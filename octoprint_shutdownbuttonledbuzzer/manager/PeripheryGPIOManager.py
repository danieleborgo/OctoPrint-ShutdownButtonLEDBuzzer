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

import time
import threading
from time import sleep

from periphery import GPIO

from .AbstractGPIOManager import AbstractGPIOManager


def _midi_to_freq(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


class PeripheryGPIOManager(AbstractGPIOManager):

    @staticmethod
    def detect_gpiochip() -> str:
        """
        Return the gpiochip device path for the current board.

        Raspberry Pi 5 exposes user GPIO via the RP1 chip on /dev/gpiochip4.
        All other boards default to /dev/gpiochip0.
        """
        try:
            with open("/proc/device-tree/model") as f:
                if "raspberry pi 5" in f.read().lower():
                    return "/dev/gpiochip4"
        except Exception:
            pass
        return "/dev/gpiochip0"

    def __init__(self, gpiochip: str = "/dev/gpiochip0"):
        self.__gpiochip = gpiochip
        self.__button_gpio = None
        self.__button_stop = None
        self.__button_thread = None
        self.__led_gpio = None
        self.__buzzer_gpio = None
        self.__is_active = True

    @staticmethod
    def supports_pwm() -> bool:
        return True

    def setup_button(self, pin: int, hold_time: float, callback) -> None:
        self.close_button()
        try:
            #  GPIO V2 chardev (kernel >= 5.10): internal pull-up supported
            self.__button_gpio = GPIO(self.__gpiochip, pin, "in", bias="pull_up", edge="falling")
        except Exception:
            #  GPIO V1 chardev (kernel < 5.10): bias not supported, external pull-up required
            self.__button_gpio = GPIO(self.__gpiochip, pin, "in", edge="falling")
        self.__button_stop = threading.Event()
        self.__button_thread = threading.Thread(
            target=self.__poll_loop,
            args=(callback,),
            daemon=True
        )
        self.__button_thread.start()

    def __poll_loop(self, callback) -> None:
        while not self.__button_stop.is_set():
            try:
                if self.__button_gpio and self.__button_gpio.poll(timeout=0.5):
                    self.__button_gpio.read_event()
                    callback()
            except Exception:
                if not self.__button_stop.is_set():
                    sleep(0.1)

    def close_button(self) -> None:
        if self.__button_stop:
            self.__button_stop.set()
        if self.__button_thread:
            self.__button_thread.join(timeout=1.5)
            self.__button_thread = None
        if self.__button_gpio:
            self.__button_gpio.close()
            self.__button_gpio = None
        self.__button_stop = None

    def setup_led(self, pin: int) -> None:
        self.close_led()
        self.__led_gpio = GPIO(self.__gpiochip, pin, "out")
        self.__led_gpio.write(True)

    def close_led(self) -> None:
        if self.__led_gpio is not None:
            self.__led_gpio.close()
            self.__led_gpio = None

    def setup_buzzer(self, pin: int, is_active: bool) -> None:
        self.close_buzzer()
        self.__is_active = is_active
        self.__buzzer_gpio = GPIO(self.__gpiochip, pin, "out")
        self.__buzzer_gpio.write(False)

    def close_buzzer(self) -> None:
        if self.__buzzer_gpio is not None:
            self.__buzzer_gpio.close()
            self.__buzzer_gpio = None

    def emit_beep(self, n: int, beep_ms: int, note: int) -> None:
        if self.__buzzer_gpio is None or n <= 0:
            return
        if self.__is_active:
            self.__emit_active(n, beep_ms)
        else:
            self.__emit_passive(n, beep_ms, note)

    def __emit_active(self, n: int, beep_ms: int) -> None:
        for _ in range(n):
            self.__buzzer_gpio.write(True)
            sleep(beep_ms / 1000.0)
            self.__buzzer_gpio.write(False)
            sleep(beep_ms / 1000.0)

    def __emit_passive(self, n: int, beep_ms: int, note: int) -> None:
        # Software PWM via sleep(): OS scheduling jitter (~1-5 ms) means the
        # actual frequency will drift from the target, especially above ~500 Hz.
        # This is acceptable for short notification beeps but not musical accuracy.
        freq = _midi_to_freq(note)
        half_period = 1.0 / (2.0 * freq)
        beep_s = beep_ms / 1000.0
        for _ in range(n):
            deadline = time.monotonic() + beep_s
            while time.monotonic() < deadline:
                self.__buzzer_gpio.write(True)
                sleep(half_period)
                self.__buzzer_gpio.write(False)
                sleep(half_period)
            sleep(beep_s)

    def close_all(self) -> None:
        self.close_button()
        self.close_led()
        self.close_buzzer()
