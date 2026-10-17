"""Rival 110 single-LED animation engine.  No Qt or HID dependency.

Effect math is deliberately one-zone instead of collapsing three-zone frame
outputs, which used to erase two-thirds of Lightning/Comet/Starry Night hits.
"""
from __future__ import annotations
import colorsys
import math
import random
import time
from dataclasses import dataclass

# (label, key, minimum, maximum, initial, suffix) -- per-effect editing hints.
PARAMETERS = {
    'Static': [('Pulse-free brightness', 'level', 0, 100, 100, '%')],
    'Two-color': [('Color blend sharpness', 'sharpness', 1, 5, 2, ''), ('Pause at each color', 'dwell', 0, 80, 10, '%')],
    'Off': [],
    'Rainbow': [('Hue range', 'range', 30, 360, 360, 'deg'), ('Reverse direction', 'reverse', 0, 1, 0, '')],
    'Breathing': [('Minimum glow', 'minimum', 0, 75, 3, '%'), ('Pulse softness', 'curve', 1, 5, 2, '')],
    'Two-color Pulse': [('Minimum glow', 'minimum', 0, 75, 5, '%'), ('Color transition width', 'blend', 1, 100, 50, '%')],
    'Custom Gradient': [('Intermediate hue shift', 'shift', 0, 180, 0, 'deg'), ('Pause at colors', 'dwell', 0, 75, 0, '%')],
    'Sunrise': [('Sunrise duration', 'duration', 2, 60, 15, 's'), ('Daylight pause', 'hold', 0, 20, 3, 's')],
    'Comet': [('Flash length', 'flash_ms', 40, 500, 160, 'ms'), ('Trail decay', 'trail', 1, 100, 70, '%'), ('Secondary streaks', 'secondary', 0, 100, 30, '%')],
    'Lightning': [('Strikes per minute', 'frequency', 1, 180, 28, '/min'), ('Flash length', 'flash_ms', 30, 450, 95, 'ms'), ('Double-strike chance', 'double_chance', 0, 100, 55, '%'), ('Background glow', 'background', 0, 30, 4, '%')],
    'Color Wave': [('Hue spread', 'spread', 20, 360, 210, 'deg'), ('Wave smoothness', 'softness', 1, 5, 3, '')],
    'Fire': [('Flicker intensity', 'flicker', 0, 100, 70, '%'), ('Warmth', 'warmth', 0, 100, 80, '%'), ('Ember frequency', 'ember', 0, 100, 20, '%')],
    'Ocean': [('Wave depth', 'depth', 0, 100, 55, '%'), ('Current shift', 'shift', 0, 70, 30, 'deg')],
    'Starry Night': [('Stars per minute', 'frequency', 1, 120, 25, '/min'), ('Twinkle decay', 'decay', 100, 2500, 650, 'ms'), ('Ambient starlight', 'ambient', 0, 30, 3, '%')],
    'CPU Monitor': [('Low-load hue', 'low_hue', 0, 360, 120, 'deg'), ('High-load hue', 'high_hue', 0, 360, 0, 'deg'), ('Minimum output', 'minimum', 0, 60, 20, '%')],
    'Custom Sequence': [('Loop sequence', 'loop', 0, 1, 1, ''), ('Transition softness', 'softness', 0, 100, 70, '%')],
    'Hardware Breath': [],
    'Hardware Effect 2': [],
    'Hardware Effect 4': [],
}
EFFECT_NAMES = list(PARAMETERS)
HARDWARE_EFFECTS = {'Hardware Breath', 'Hardware Effect 2', 'Hardware Effect 4'}


def clamp(x, lo=0.0, hi=1.0):
    return min(hi, max(lo, x))


def fromhex(color):
    return tuple(int(color[i:i+2], 16) for i in (1, 3, 5))


def tohex(rgb):
    return '#%02X%02X%02X' % tuple(int(round(clamp(c / 255.0) * 255)) for c in rgb)


def mix(a, b, alpha):
    alpha = clamp(alpha)
    a, b = fromhex(a), fromhex(b)
    return tohex([x * (1 - alpha) + y * alpha for x, y in zip(a, b)])


def hsv(h, s=1, v=1):
    return tohex([component * 255 for component in colorsys.hsv_to_rgb((h % 360) / 360, clamp(s), clamp(v))])


def modulate(color, brightness=1, saturation=1):
    r, g, b = [x / 255 for x in fromhex(color)]
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return hsv(h * 360, s * clamp(saturation), v * clamp(brightness))


def ease(t, sharpness=2):
    t = clamp(t)
    x = 0.5 - 0.5 * math.cos(math.pi * t)
    return x ** (1 / max(.5, float(sharpness) / 2))


@dataclass
class EffectResult:
    color: str
    hardware: str | int = 'steady'


class Animator:
    def __init__(self, rng=None):
        self.random = rng or random.Random()
        self.profile = {}
        self.start = time.monotonic()
        self.previous = self.start
        self.color = '#000000'
        self.next_event = None
        self.event_end = 0.0
        self.followup_at = None
        self.followup_ms = 0
        self.intensity = 0.0
        self.cpu_load = 0.0
        self.last_cpu = 0.0

    def configure(self, profile, now=None):
        self.profile = dict(profile)
        self.start = time.monotonic() if now is None else float(now)
        self.previous = self.start
        self.next_event = None
        self.followup_at = None
        self.event_end = 0
        self.intensity = 0
        self.color = '#000000'

    def setting(self, key):
        effect = self.profile.get('effect', 'Static')
        for _, k, _, _, default, _ in PARAMETERS.get(effect, []):
            if k == key:
                return self.profile.get('parameters', {}).get(key, default)
        return 0

    def _event(self, now, rate):
        """Returns True at a Poisson-distributed arrival (rate per minute)."""
        if self.next_event is None:
            self.next_event = now + self.random.expovariate(max(.0001, rate / 60.0))
        if now >= self.next_event:
            self.next_event = now + self.random.expovariate(max(.0001, rate / 60.0))
            return True
        return False

    def sample(self, now=None, cpu_load=None):
        now = time.monotonic() if now is None else float(now)
        elapsed = max(0, now - self.start)
        dt = max(0, min(.5, now - self.previous))
        self.previous = now
        p = self.profile
        effect = p.get('effect', 'Static')
        a = p.get('primary', '#357CC8')
        b = p.get('secondary', '#F6F8FF')
        speed = max(.05, p.get('speed', 45) / 45.0)
        t = elapsed * speed
        phase = t % 1
        color = a
        hardware = 'steady'

        if effect == 'Off':
            color = '#000000'
        elif effect == 'Static':
            color = modulate(a, self.setting('level') / 100)
        elif effect == 'Hardware Breath':
            color = a
            hardware = 'breath'
        elif effect == 'Hardware Effect 2':
            color = a
            hardware = 2
        elif effect == 'Hardware Effect 4':
            color = a
            hardware = 4
        elif effect == 'Rainbow':
            direction = -1 if self.setting('reverse') else 1
            color = hsv(phase * direction * self.setting('range'), 1, 1)
        elif effect == 'Two-color':
            dwell = self.setting('dwell') / 100 * .4
            local = phase * 2 if phase < .5 else (phase-.5)*2
            ramp = clamp((local - dwell) / max(.01, 1 - 2*dwell))
            alpha = ramp if phase < .5 else 1 - ramp
            color = mix(a, b, ease(alpha, self.setting('sharpness')))
        elif effect == 'Breathing':
            magnitude = (0.5 - 0.5 * math.cos(2 * math.pi * phase)) ** (self.setting('curve') / 2)
            power = self.setting('minimum') / 100 + (1 - self.setting('minimum') / 100) * magnitude
            color = modulate(a, power)
        elif effect == 'Two-color Pulse':
            alpha = ease(0.5 - 0.5 * math.cos(2 * math.pi * phase))
            blend = self.setting('blend') / 100
            color = mix(a, b, clamp((alpha - .5) / max(.01, blend) + .5))
            floor = self.setting('minimum') / 100
            color = modulate(color, floor + (1 - floor) * (.55 + .45 * alpha))
        elif effect == 'Custom Gradient':
            shift = self.setting('shift')
            mid_rgb = [x / 255 for x in fromhex(mix(a, b, .5))]
            mid_hue, mid_sat, mid_val = colorsys.rgb_to_hsv(*mid_rgb)
            midpoint = hsv(mid_hue * 360 + shift, mid_sat, mid_val)
            anchors = (a, midpoint, b, a)
            seg = min(2, int(phase * 3))
            local = (phase * 3) % 1
            dwell = self.setting('dwell') / 100 * .45
            local = clamp((local - dwell) / max(.01, 1 - 2*dwell))
            color = mix(anchors[seg], anchors[seg+1], ease(local))
        elif effect == 'Sunrise':
            duration = self.setting('duration')
            hold = self.setting('hold')
            cycle = (t % (duration + hold))
            if cycle > duration:
                color = '#FFF9E6'
            else:
                u = cycle / duration
                stages = ('#000000', '#5D1422', '#DE4D18', '#FFB452', '#FFF9E6')
                i = min(len(stages)-2, int(u * (len(stages)-1)))
                color = mix(stages[i], stages[i+1], ease((u * (len(stages)-1)) % 1))
        elif effect == 'Comet':
            period = max(.25, 1.5 / speed)
            eventphase = (elapsed % period)
            length = self.setting('flash_ms') / 1000
            trail = self.setting('trail') / 100
            if eventphase < length:
                color = mix(a, b, 0.5 + 0.5 * math.cos(math.pi * eventphase / max(.04, length)))
            else:
                glow = math.exp(-(eventphase - length) * (3 + 14 * (1-trail)))
                color = modulate(a, glow)
            if self.setting('secondary') > 0 and eventphase > period * .48 and eventphase < period*.48 + .065:
                color = mix(color, b, self.setting('secondary') / 100)
        elif effect == 'Lightning':
            background = self.setting('background') / 100
            if self._event(now, self.setting('frequency') * speed):
                self.event_end = now + self.setting('flash_ms') / 1000
                if self.random.random() < self.setting('double_chance') / 100:
                    self.followup_at = self.event_end + .07
                    self.followup_ms = self.setting('flash_ms') * .45 / 1000
            if self.followup_at is not None and now >= self.followup_at:
                self.event_end = self.followup_at + self.followup_ms
                self.followup_at = None
            # Bright white/primary-tinted flashes on the actual single LED.
            color = mix('#000000', b, background)
            if now < self.event_end:
                color = mix(a, '#FFFFFF', .75)
        elif effect == 'Color Wave':
            spread = self.setting('spread')
            softness = self.setting('softness')
            motion = 0.5 - 0.5 * math.cos(2 * math.pi * phase)
            motion = motion ** (softness / 3)
            rgb = [x / 255 for x in fromhex(a)]
            base_hue = colorsys.rgb_to_hsv(*rgb)[0] * 360
            color = hsv(base_hue + motion * spread, .9, 1)
        elif effect == 'Fire':
            flicker = self.setting('flicker') / 100
            warmth = self.setting('warmth') / 100
            # Smoothed randomness avoids harsh flicker while retaining embers.
            self.intensity = self.intensity * (1 - .15 * speed) + (self.random.random()-.5) * .35 * flicker * speed
            flame = .68 + self.intensity
            base = hsv(5 + (1-warmth)*45 + self.random.random()*18, 1, 1)
            if self.random.random() < self.setting('ember') / 2000:
                flame = 1
                base = '#FFD9A6'
            color = modulate(base, clamp(flame))
        elif effect == 'Ocean':
            depth = self.setting('depth') / 100
            wave = .5 + .5 * math.sin(2 * math.pi * t)
            color = hsv(190 + self.setting('shift') * (wave-.5), .75 + .15 * depth, .4 + .6 * wave * depth + (1-depth)*.4)
        elif effect == 'Starry Night':
            ambient = self.setting('ambient') / 100
            self.intensity *= math.exp(-dt * speed / max(.1, self.setting('decay') / 1000))
            if self._event(now, self.setting('frequency') * speed):
                self.intensity = 1
            color = mix(modulate('#1E3B8F', ambient), b, self.intensity)
        elif effect == 'CPU Monitor':
            value = clamp(float(cpu_load if cpu_load is not None else self.cpu_load) / 100)
            self.cpu_load = value * 100
            hue = self.setting('low_hue') * (1-value) + self.setting('high_hue') * value
            intensity = self.setting('minimum') / 100 + (1 - self.setting('minimum')/100) * value
            color = hsv(hue, 1, intensity)
        elif effect == 'Custom Sequence':
            steps = p.get('sequence') or [{'color': a, 'duration': 1000, 'transition': 'smooth'}]
            total = sum(max(50, item['duration']) for item in steps)
            if total:
                position = elapsed * 1000 * speed
                if self.setting('loop'):
                    position %= total
                else:
                    position = min(position, total)
                offset = 0
                for i, step in enumerate(steps):
                    end = offset + step['duration']
                    if position <= end or i == len(steps) - 1:
                        nxt = steps[(i+1) % len(steps)]['color'] if self.setting('loop') or i < len(steps)-1 else step['color']
                        alpha = (position-offset)/max(1, step['duration'])
                        softness = self.setting('softness')/100
                        color = mix(step['color'], nxt, ease(alpha) * softness) if step['transition'] == 'smooth' else step['color']
                        break
                    offset = end
        # Global intensity and saturation, applied once for every effect.
        color = modulate(color, p.get('brightness', 80) / 100,
                         p.get('saturation', 90) / 100)
        self.color = color
        return EffectResult(color, hardware)
