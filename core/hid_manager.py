import logging

import rivalcfg
from rivalcfg import handlers
from rivalcfg.handlers import rgbcolor, choice as choice_handler, range as range_handler

logger = logging.getLogger(__name__)

ZONE_MAP = {"z1": "z1_color", "z2": "z2_color", "z3": "z3_color"}


class HidManager:
    def __init__(self):
        self._mouse = None

    def connect(self) -> bool:
        try:
            self._mouse = rivalcfg.get_first_mouse()
            return self._mouse is not None
        except Exception:
            logger.exception("Failed to connect to mouse")
            return False

    def disconnect(self) -> None:
        if self._mouse is not None:
            try:
                self._mouse.close()
            except Exception:
                logger.exception("Error disconnecting mouse")
            self._mouse = None

    def reconnect(self) -> bool:
        self.disconnect()
        return self.connect()

    def is_connected(self) -> bool:
        return self._mouse is not None

    def set_colors(self, z1: str, z2: str, z3: str) -> bool:
        return (
            self._send(ZONE_MAP["z1"], z1)
            and self._send(ZONE_MAP["z2"], z2)
            and self._send(ZONE_MAP["z3"], z3)
        )

    def set_brightness(self, val: int) -> bool:
        return self._send("led_brightness", val)

    def set_rainbow(self) -> bool:
        return self._send("rainbow_effect", "all")

    def reset(self) -> bool:
        if self._mouse is None:
            logger.warning("Mouse not connected")
            return False
        try:
            self._mouse.reset_settings()
            return True
        except Exception:
            logger.exception("Failed to reset mouse settings")
            return False

    def _send(self, setting_name: str, value) -> bool:
        if self._mouse is None:
            logger.warning("Mouse not connected")
            return False
        try:
            setting_info = self._mouse.mouse_profile["settings"][setting_name]

            handler_name = setting_info.get("value_type")
            data = []
            if handler_name and handler_name != "none":
                handler = getattr(handlers, handler_name)
                data = handler.process_value(setting_info, value)

            self._mouse._hid_write(
                report_type=setting_info["report_type"],
                report_id=0,
                data=setting_info["command"] + data,
            )
            return True
        except KeyError:
            logger.exception("Unknown setting: %s", setting_name)
            return False
        except Exception:
            logger.exception("Error sending setting '%s'", setting_name)
            return False


hid = HidManager()
