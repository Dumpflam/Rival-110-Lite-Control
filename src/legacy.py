"""Convert exported Rival Lite Control .rivalprofile single-zone values.

Legacy releases saved three-zone Polish-named modes. Only the first LED
physically maps to a Rival 110, so z1 is the original actual LED color.
"""
import copy
from state import DEFAULT_LIGHTING, validate_light

MODES = dict(zip(
    ('Statyczny', 'Dwukolorowy', 'Wygaszony', 'Tęcza', 'Oddychanie',
     'Puls Dwukolorowy', 'Własny Gradient', 'Wschód Słońca', 'Kometa',
     'Błyskawica', 'Fala Kolorów', 'Ogień', 'Ocean', 'Gwiezdna Noc',
     'Monitor CPU', 'Własny Sekwencyjny'),
    ('Static', 'Two-color', 'Off', 'Rainbow', 'Breathing',
     'Two-color Pulse', 'Custom Gradient', 'Sunrise', 'Comet',
     'Lightning', 'Color Wave', 'Fire', 'Ocean', 'Starry Night',
     'CPU Monitor', 'Custom Sequence')
))


def convert_old_lighting(old):
    new = copy.deepcopy(DEFAULT_LIGHTING)
    new['effect'] = MODES.get(old.get('effect'), old.get('effect', 'Static'))
    colors = old.get('colors', {})
    new['primary'] = colors.get('z1', new['primary'])
    new['secondary'] = old.get('color_b', colors.get('z2', new['secondary']))
    new['brightness'] = max(0, min(100, int(old.get('brightness', new['brightness']))))
    old_speed = int(old.get('speed', 5))
    new['speed'] = max(1, min(100, old_speed * 10 if old_speed <= 10 else old_speed))
    return validate_light(new)
