# coding=utf-8

"""
Copyright (C) 2026 Daniele Borgo

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from __future__ import absolute_import
import octoprint.plugin
import os
import subprocess
from octoprint.events import Events
from time import sleep
from flask import jsonify
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

__plugin_pythoncompat__ = ">=3,<4"  # only python 3

LIBRARY_GPIOZERO = "gpiozero"
LIBRARY_PERIPHERY = "periphery"


class ShutdownButtonLEDBuzzerPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.EventHandlerPlugin
):
    BOUNCING_TIME_MS = 500
    HOLD_TIME_S = 1
    I2C_STATUS_COMMAND = "raspi-config nonint get_i2c"
    SPI_STATUS_COMMAND = "raspi-config nonint get_spi"
    SERVICE_ENABLED_OUTPUT = "0"

    def __init__(self):
        super().__init__()

        #  User editable data
        self.__button_pin = None
        self.__led_pin = None
        self.__buzzer_pin = None
        self.__beep_ms = None
        self.__is_disabled_in_print = None
        self.__is_buzzer_active = None
        self.__beeps_on_startup = None
        self.__beeps_on_shutdown = None
        self.__beeps_on_pressed = None
        self.__active_note = None
        self.__is_button_en = None
        self.__is_led_en = None
        self.__is_buzzer_en = None
        self.__gpio_library = None

        #  Plugin data
        self.__manager = None
        self.__beep_thread_pool = ThreadPoolExecutor(max_workers=1)
        self.__shutdown_lock = Lock()
        self.__is_printing = False

    def on_after_startup(self):
        self.__load_settings()
        self.__initialize_manager()
        self.__setup()
        self._logger.info('Plugin ready')

    def on_event(self, event, payload):
        if event == Events.PRINT_STARTED:
            self.__is_printing = True
            return

        if event in (Events.PRINT_DONE, Events.PRINT_CANCELLED, Events.PRINT_FAILED):
            self.__is_printing = False
            return

    def __load_settings(self):
        self.__button_pin = self._settings.get_int(["button_pin"])
        self.__led_pin = self._settings.get_int(["led_pin"])
        self.__buzzer_pin = self._settings.get_int(["buzzer_pin"])
        self.__beep_ms = self._settings.get_int(["beep_ms"])
        self.__is_disabled_in_print = self._settings.get_boolean(["is_disabled_in_print"])
        self.__is_buzzer_active = self._settings.get_boolean(["is_buzzer_active"])
        self.__beeps_on_startup = self._settings.get_int(["beeps_on_startup"])
        self.__beeps_on_shutdown = self._settings.get_int(["beeps_on_shutdown"])
        self.__beeps_on_pressed = self._settings.get_int(["beeps_on_pressed"])
        self.__active_note = self._settings.get_int(["active_note"])
        self.__is_button_en = self._settings.get_boolean(["is_button_en"])
        self.__is_led_en = self._settings.get_boolean(["is_led_en"])
        self.__is_buzzer_en = self._settings.get_boolean(["is_buzzer_en"])
        self.__gpio_library = self._settings.get(["gpio_library"])

    def __detect_library(self) -> str:
        debian_version = self.__get_debian_version()
        if debian_version >= 12:
            self._logger.info(f"Debian {debian_version} detected, selecting periphery")
            return LIBRARY_PERIPHERY
        if debian_version > 0:
            self._logger.info(f"Debian {debian_version} detected, selecting gpiozero")
            return LIBRARY_GPIOZERO
        # Non-Debian OS: fall back to functionality test
        self._logger.info("OS version unknown, falling back to library functionality test")
        for library in (LIBRARY_PERIPHERY, LIBRARY_GPIOZERO):
            if self.__test_library(library):
                self._logger.info(f"Auto-detected GPIO library: {library}")
                return library
        self._logger.warning("No working GPIO library detected, defaulting to periphery")
        return LIBRARY_PERIPHERY

    @staticmethod
    def __get_debian_version() -> int:
        try:
            with open("/etc/os-release") as f:
                fields = {}
                for line in f:
                    k, _, v = line.strip().partition("=")
                    fields[k] = v.strip('"')
            return int(fields.get("VERSION_ID", 0))
        except Exception:
            return 0

    @staticmethod
    def __get_os_codename() -> str:
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    k, _, v = line.strip().partition("=")
                    if k == "VERSION_CODENAME":
                        return v.strip('"').capitalize()
        except Exception:
            pass
        return "Unknown"

    @staticmethod
    def __is_raspberry_pi() -> bool:
        try:
            with open("/proc/device-tree/model") as f:
                return "raspberry pi" in f.read().lower()
        except Exception:
            return False

    @staticmethod
    def __get_board_model() -> str:
        try:
            with open("/proc/device-tree/model") as f:
                return f.read().rstrip("\x00").strip()
        except Exception:
            return ""

    def __initialize_manager(self):
        resolved = self.__gpio_library
        if resolved == "auto":
            resolved = self.__detect_library()
            self._logger.info(f"Auto-detected GPIO library: {resolved}")

        if self.__manager is not None:
            self.__manager.close_all()
            self.__manager = None

        try:
            if resolved == LIBRARY_PERIPHERY:
                from .manager.PeripheryGPIOManager import PeripheryGPIOManager
                self.__manager = PeripheryGPIOManager(PeripheryGPIOManager.detect_gpiochip())
            else:
                from .manager.GpiozeroGPIOManager import GpiozeroGPIOManager
                self.__manager = GpiozeroGPIOManager()
            self._logger.info(f"GPIO manager initialized: {resolved}")
        except Exception as e:
            self._logger.error(f"Failed to initialize GPIO manager ({resolved}): {e}")
            self.__manager = None

    def __setup(self):
        if self.__manager is None:
            return

        try:
            if self.__is_button_en:
                self.__manager.setup_button(
                    self.__button_pin,
                    ShutdownButtonLEDBuzzerPlugin.HOLD_TIME_S,
                    self.__shutdown_for_button
                )
            else:
                self.__manager.close_button()

            if self.__is_led_en:
                self.__manager.setup_led(self.__led_pin)
            else:
                self.__manager.close_led()

            if self.__is_buzzer_en:
                self.__manager.setup_buzzer(self.__buzzer_pin, self.__is_buzzer_active)
                self.__emit_beep(self.__beeps_on_startup)
            else:
                self.__manager.close_buzzer()
        except Exception as e:
            self._logger.error(f"GPIO setup failed: {e}")

    def __shutdown_for_button(self):
        self.__beep_thread_pool.submit(self.__shutdown_for_pool)

    def __shutdown_for_pool(self):
        if not self.__shutdown_lock.acquire(blocking=False):
            return

        if self.__is_disabled_in_print and self.__is_printing:
            self._logger.info("Shutdown command stopped due to printing")
            self.__shutdown_lock.release()
            return

        self._logger.info("Shutdown command received")
        sleep(ShutdownButtonLEDBuzzerPlugin.BOUNCING_TIME_MS / 1000)
        self.__emit_beep(self.__beeps_on_pressed)
        os.system(self.__get_shutdown_command())
        # No lock release needed

    def __get_shutdown_command(self):
        return self._settings.global_get(["server", "commands", "systemShutdownCommand"])

    def __emit_beep(self, n: int):
        if self.__is_buzzer_en and n > 0 and self.__manager is not None:
            self.__beep_thread_pool.submit(
                self.__manager.emit_beep,
                n, self.__beep_ms, self.__active_note
            )

    def on_shutdown(self):
        self.__beep_thread_pool.shutdown(wait=False)
        if self.__manager is not None:
            self.__manager.close_button()
            # LED is not closed: it stays on to indicate GPIO is still live during OS shutdown
            if self.__is_buzzer_en:
                self.__manager.emit_beep(
                    self.__beeps_on_shutdown, self.__beep_ms, self.__active_note
                )
            self.__manager.close_buzzer()
        self._logger.info("Plugin closed")

    def get_settings_defaults(self):
        return dict(
            button_pin=26,
            led_pin=6,
            buzzer_pin=13,
            beep_ms=50,
            is_disabled_in_print=False,
            is_buzzer_active=True,
            beeps_on_startup=2,
            beeps_on_shutdown=3,
            beeps_on_pressed=2,
            active_note=77,
            is_button_en=True,
            is_led_en=True,
            is_buzzer_en=True,
            gpio_library="auto",
            unlock_pin_range=not ShutdownButtonLEDBuzzerPlugin.__is_raspberry_pi()
        )

    def on_settings_save(self, data):
        incoming_button_en  = data.get("is_button_en", self.__is_button_en)
        incoming_led_en     = data.get("is_led_en",    self.__is_led_en)
        incoming_buzzer_en  = data.get("is_buzzer_en", self.__is_buzzer_en)
        incoming_button_pin = int(data.get("button_pin", self.__button_pin))
        incoming_led_pin    = int(data.get("led_pin",    self.__led_pin))
        incoming_buzzer_pin = int(data.get("buzzer_pin", self.__buzzer_pin))

        seen = {}
        for name, enabled, pin in (
            ("button", incoming_button_en, incoming_button_pin),
            ("led",    incoming_led_en,    incoming_led_pin),
            ("buzzer", incoming_buzzer_en, incoming_buzzer_pin),
        ):
            if not enabled:
                continue
            if pin in seen:
                self._logger.error(
                    f"Pin conflict: {name} and {seen[pin]} both assigned to BCM {pin}. "
                    "Settings not saved — resolve the conflict and save again."
                )
                return
            seen[pin] = name

        old_library = self.__gpio_library
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.__load_settings()
        if self.__gpio_library != old_library:
            self.__initialize_manager()
        self.__setup()

    def is_api_protected(self):
        return True

    def get_api_commands(self):
        return dict(
            services_status=[],
            check_library=["library"]
        )

    def on_api_command(self, command, data):
        self._logger.info(f"API request received: {command}")
        if command == "services_status":
            return jsonify({
                'i2c_status': ShutdownButtonLEDBuzzerPlugin.__get_i2c_status(),
                'spi_status': ShutdownButtonLEDBuzzerPlugin.__get_spi_status(),
                'os_name': ShutdownButtonLEDBuzzerPlugin.__get_os_codename(),
                'board_model': ShutdownButtonLEDBuzzerPlugin.__get_board_model(),
                'is_raspberry_pi': ShutdownButtonLEDBuzzerPlugin.__is_raspberry_pi()
            })
        if command == "check_library":
            library = data.get("library", LIBRARY_PERIPHERY)
            available = self.__test_library(library)
            supports_pwm = ShutdownButtonLEDBuzzerPlugin.__library_supports_pwm(library)
            debian_version = ShutdownButtonLEDBuzzerPlugin.__get_debian_version()
            if debian_version >= 12:
                recommended = LIBRARY_PERIPHERY
            elif debian_version > 0:
                recommended = LIBRARY_GPIOZERO
            else:
                recommended = None
            return jsonify({
                'available': available,
                'supports_pwm': supports_pwm,
                'recommended': recommended,
                'os_name': ShutdownButtonLEDBuzzerPlugin.__get_os_codename()
            })
        return None

    def __test_library(self, library: str) -> bool:
        try:
            if library == LIBRARY_PERIPHERY:
                from periphery import GPIO
                gpio = GPIO("/dev/gpiochip0", 0, "in")
                gpio.close()
            else:
                import os
                import gpiozero
                return (
                    any(os.path.exists(f"/dev/gpiochip{i}") for i in range(8)) or
                    os.path.isdir("/sys/class/gpio")
                )
            return True
        except Exception as e:
            self._logger.warning(f"Library test failed for '{library}': {e}")
            return False

    @staticmethod
    def __library_supports_pwm(library: str) -> bool:
        return library in (LIBRARY_PERIPHERY, LIBRARY_GPIOZERO)

    @staticmethod
    def __get_i2c_status():
        return ShutdownButtonLEDBuzzerPlugin.__get_service_status(
            ShutdownButtonLEDBuzzerPlugin.I2C_STATUS_COMMAND
        )

    @staticmethod
    def __get_spi_status():
        return ShutdownButtonLEDBuzzerPlugin.__get_service_status(
            ShutdownButtonLEDBuzzerPlugin.SPI_STATUS_COMMAND
        )

    @staticmethod
    def __get_service_status(command: str):
        try:
            out = subprocess.run(command.split(), capture_output=True).stdout.decode("utf-8").strip()
            return "enabled" if (out == ShutdownButtonLEDBuzzerPlugin.SERVICE_ENABLED_OUTPUT) else "disabled"
        except FileNotFoundError:
            return "undefined"

    def get_template_configs(self):
        return []

    def get_assets(self):
        return {
            "js": ["js/ShutdownButtonLEDBuzzer.js"],
            "css": ["css/ShutdownButtonLEDBuzzer.css"]
        }

    def get_update_information(self):
        return {
            "shutdownbuttonledbuzzer": {
                "displayName": "Shutdownbuttonledbuzzer Plugin",
                "displayVersion": self._plugin_version,
                "type": "github_release",
                "user": "danieleborgo",
                "repo": "OctoPrint-ShutdownButtonLEDBuzzer",
                "current": self._plugin_version,
                "pip": "https://github.com/danieleborgo/OctoPrint-ShutdownButtonLEDBuzzer/archive/{target_version}.zip",
            }
        }


def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = ShutdownButtonLEDBuzzerPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
    }
