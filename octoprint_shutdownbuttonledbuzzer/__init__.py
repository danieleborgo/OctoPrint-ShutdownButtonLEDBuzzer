# coding=utf-8

"""
Copyright (C) 2022 Daniele Borgo

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
from time import sleep
from gpiozero import Button, Buzzer, LED, TonalBuzzer, tones
from gpiozero.tones import Tone
from flask import jsonify
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

__plugin_pythoncompat__ = ">=3,<4"  # only python 3


class ShutdownButtonLEDBuzzerPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.ShutdownPlugin,
    octoprint.plugin.SimpleApiPlugin
):
    DEFAULT_BUTTON_PIN = 26
    DEFAULT_LED_PIN = 6
    DEFAULT_BUZZER_PIN = 13
    DEFAULT_BEEP_MS = 50
    DEFAULT_IS_BUZZER_ACTIVE = True
    DEFAULT_BEEPS_ON_STARTUP = 2
    DEFAULT_BEEPS_ON_SHUTDOWN = 3
    DEFAULT_BEEPS_ON_PRESSED = 2
    DEFAULT_ACTIVE_NOTE = 77
    DEFAULT_EN = True
    BOUNCING_TIME_MS = 500
    HOLD_TIME_S = 1
    MID_TONE = "B4"  # Client input max and min values depend on this
    OCTAVES = 3  # Client input max and min values depend on this
    PI_SHUTDOWN_COMMAND = "shutdown -h now"
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
        self.__is_buzzer_active = None
        self.__beeps_on_startup = None
        self.__beeps_on_shutdown = None
        self.__beeps_on_pressed = None
        self.__active_note = None
        self.__is_button_en = None
        self.__is_led_en = None
        self.__is_buzzer_en = None

        #  Plugin data
        self.__button = None
        self.__led = None
        self.__buzzer = None
        self.__beep_thread_pool = ThreadPoolExecutor(max_workers=1)
        self.__shutdown_lock = Lock()

    def on_after_startup(self):
        self.__load_settings()
        self.__setup()
        self._logger.info('Plugin ready')

    def __load_settings(self):
        self.__button_pin = self._settings.get_int(["button_pin"])
        self.__led_pin = self._settings.get_int(["led_pin"])
        self.__buzzer_pin = self._settings.get_int(["buzzer_pin"])
        self.__beep_ms = self._settings.get_int(["beep_ms"])
        self.__is_buzzer_active = self._settings.get_boolean(["is_buzzer_active"])
        self.__beeps_on_startup = self._settings.get_int(["beeps_on_startup"])
        self.__beeps_on_shutdown = self._settings.get_int(["beeps_on_shutdown"])
        self.__beeps_on_pressed = self._settings.get_int(["beeps_on_pressed"])
        self.__active_note = self._settings.get_int(["active_note"])
        self.__is_button_en = self._settings.get_boolean(["is_button_en"])
        self.__is_led_en = self._settings.get_boolean(["is_led_en"])
        self.__is_buzzer_en = self._settings.get_boolean(["is_buzzer_en"])

    def __setup(self):
        #  Set the button with a pull-up resistor, so it's measurable through a tester
        self.__close_component(self.__button)
        if self.__is_button_en:
            self.__button = Button(self.__button_pin, hold_time=ShutdownButtonLEDBuzzerPlugin.HOLD_TIME_S)
            self.__button.when_pressed = lambda: self.__shutdown_for_button()
        else:
            self.__button = None

        #  Set the status LED
        self.__close_component(self.__led)
        if self.__is_led_en:
            self.__led = LED(self.__led_pin)
            self.__led.on()
        else:
            self.__led = None

        #  Set the buzzer
        self.__close_component(self.__buzzer)
        if self.__is_buzzer_en:
            if self.__is_buzzer_active:
                self.__buzzer = Buzzer(self.__buzzer_pin)
            else:
                self.__buzzer = TonalBuzzer(
                    self.__buzzer_pin,
                    mid_tone=Tone(ShutdownButtonLEDBuzzerPlugin.MID_TONE),
                    octaves=ShutdownButtonLEDBuzzerPlugin.OCTAVES
                )
            self.__emit_beep(self.__beeps_on_startup)
        else:
            self.__buzzer = None

    def __shutdown_for_button(self):
        if not self.__shutdown_lock.acquire(blocking=False):
            return

        self._logger.info("Shutdown command received")
        sleep(ShutdownButtonLEDBuzzerPlugin.BOUNCING_TIME_MS / 1000)
        self.__emit_beep(self.__beeps_on_pressed)
        os.system(ShutdownButtonLEDBuzzerPlugin.PI_SHUTDOWN_COMMAND)
        #  No lock release needed

    def __emit_beep(self, n: int):
        if self.__is_buzzer_en:
            self.__beep_thread_pool.submit(
                self.__emit_active_beep_for_pool if self.__is_buzzer_active else
                self.__emit_passive_beep_for_pool,
                n
            )

    def __emit_passive_beep_for_pool(self, n: int):
        tone = Tone.from_midi(self.__active_note)
        for i in range(n):
            self.__buzzer.play(tone)
            sleep(self.__beep_ms / 1000.0)
            self.__buzzer.stop()
            sleep(self.__beep_ms / 1000.0)

    def __emit_active_beep_for_pool(self, n: int):
        for i in range(n):
            self.__buzzer.on()
            sleep(self.__beep_ms / 1000.0)
            self.__buzzer.off()
            sleep(self.__beep_ms / 1000.0)

    @staticmethod
    def __close_component(component):
        if component is not None:
            component.close()

    def on_shutdown(self):
        self.__beep_thread_pool.shutdown(wait=False)
        self.__close_component(self.__button)
        # LED is not turned off since it has to indicate the Raspberry GPIO shutdown
        if self.__is_buzzer_active:
            self.__emit_active_beep_for_pool(self.__beeps_on_shutdown)
        else:
            self.__emit_passive_beep_for_pool(self.__beeps_on_shutdown)
        self.__close_component(self.__buzzer)
        self._logger.info("Plugin closed")

    def get_settings_defaults(self):
        return dict(
            button_pin=ShutdownButtonLEDBuzzerPlugin.DEFAULT_BUTTON_PIN,
            buzzer_pin=ShutdownButtonLEDBuzzerPlugin.DEFAULT_BUZZER_PIN,
            is_buzzer_active=ShutdownButtonLEDBuzzerPlugin.DEFAULT_IS_BUZZER_ACTIVE,
            led_pin=ShutdownButtonLEDBuzzerPlugin.DEFAULT_LED_PIN,
            beep_ms=ShutdownButtonLEDBuzzerPlugin.DEFAULT_BEEP_MS,
            beeps_on_startup=ShutdownButtonLEDBuzzerPlugin.DEFAULT_BEEPS_ON_STARTUP,
            beeps_on_shutdown=ShutdownButtonLEDBuzzerPlugin.DEFAULT_BEEPS_ON_SHUTDOWN,
            beeps_on_pressed=ShutdownButtonLEDBuzzerPlugin.DEFAULT_BEEPS_ON_PRESSED,
            active_note=ShutdownButtonLEDBuzzerPlugin.DEFAULT_ACTIVE_NOTE,
            is_button_en=ShutdownButtonLEDBuzzerPlugin.DEFAULT_EN,
            is_led_en=ShutdownButtonLEDBuzzerPlugin.DEFAULT_EN,
            is_buzzer_en=ShutdownButtonLEDBuzzerPlugin.DEFAULT_EN
        )

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self.__load_settings()
        self.__setup()

    def get_api_commands(self):
        return dict(
            services_status=[]
        )

    def on_api_command(self, command, data):
        self._logger.info("Refresh request received")
        if command == "services_status":
            return jsonify({
                'i2c_status': ShutdownButtonLEDBuzzerPlugin.__get_i2c_status(),
                'spi_status': ShutdownButtonLEDBuzzerPlugin.__get_spi_status()
            })
        return None

    @staticmethod
    def __get_i2c_status():
        return ShutdownButtonLEDBuzzerPlugin.__get_service_status(ShutdownButtonLEDBuzzerPlugin.I2C_STATUS_COMMAND)

    @staticmethod
    def __get_spi_status():
        return ShutdownButtonLEDBuzzerPlugin.__get_service_status(ShutdownButtonLEDBuzzerPlugin.SPI_STATUS_COMMAND)

    @staticmethod
    def __get_service_status(command: str):
        try:
            out = subprocess.run(command.split(), capture_output=True).stdout.decode("utf-8").strip()
            return "enabled" if (out == ShutdownButtonLEDBuzzerPlugin.SERVICE_ENABLED_OUTPUT) else "disabled"
        except FileNotFoundError:
            return "undefined"

    def get_template_configs(self):
        return [
            #  dict(type="settings", custom_bindings=False)
        ]

    def get_assets(self):
        # Define your plugin's asset files to automatically include in the
        # core UI here.
        return {
            "js": ["js/ShutdownButtonLEDBuzzer.js"],
            # "less": ["less/ShutdownButtonLEDBuzzer.less"],
            "css": ["css/ShutdownButtonLEDBuzzer.css"]
        }

    def get_update_information(self):
        # Define the configuration for your plugin to use with the Software Update
        # Plugin here. See https://docs.octoprint.org/en/master/bundledplugins/softwareupdate.html
        # for details.
        return {
            "shutdownbuttonledbuzzer": {
                "displayName": "Shutdownbuttonledbuzzer Plugin",
                "displayVersion": self._plugin_version,

                # version check: github repository
                "type": "github_release",
                "user": "danieleborgo",
                "repo": "OctoPrint-ShutdownButtonLEDBuzzer",
                "current": self._plugin_version,

                # update method: pip
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
