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

from time import sleep

from gpiozero import Button, Buzzer, LED, TonalBuzzer
from gpiozero.tones import Tone

from .AbstractGPIOManager import AbstractGPIOManager


class GpiozeroGPIOManager(AbstractGPIOManager):

    def __init__(self):
        self.__button = None
        self.__led = None
        self.__buzzer = None
        self.__is_active = True

    @staticmethod
    def supports_pwm() -> bool:
        return True

    def setup_button(self, pin: int, hold_time: float, callback) -> None:
        self.close_button()
        self.__button = Button(pin, hold_time=hold_time)
        self.__button.when_pressed = callback

    def close_button(self) -> None:
        if self.__button is not None:
            self.__button.close()
            self.__button = None

    def setup_led(self, pin: int) -> None:
        self.close_led()
        self.__led = LED(pin)
        self.__led.on()

    def close_led(self) -> None:
        if self.__led is not None:
            self.__led.close()
            self.__led = None

    def setup_buzzer(self, pin: int, is_active: bool) -> None:
        self.close_buzzer()
        self.__is_active = is_active
        if is_active:
            self.__buzzer = Buzzer(pin)
        else:
            self.__buzzer = TonalBuzzer(pin, mid_tone=Tone("B4"), octaves=3)

    def close_buzzer(self) -> None:
        if self.__buzzer is not None:
            self.__buzzer.close()
            self.__buzzer = None

    def emit_beep(self, n: int, beep_ms: int, note: int) -> None:
        if self.__buzzer is None or n <= 0:
            return
        if self.__is_active:
            self.__emit_active(n, beep_ms)
        else:
            self.__emit_passive(n, beep_ms, note)

    def __emit_active(self, n: int, beep_ms: int) -> None:
        for _ in range(n):
            self.__buzzer.on()
            sleep(beep_ms / 1000.0)
            self.__buzzer.off()
            sleep(beep_ms / 1000.0)

    def __emit_passive(self, n: int, beep_ms: int, note: int) -> None:
        tone = Tone.from_midi(note)
        for _ in range(n):
            self.__buzzer.play(tone)
            sleep(beep_ms / 1000.0)
            self.__buzzer.stop()
            sleep(beep_ms / 1000.0)

    def close_all(self) -> None:
        self.close_button()
        self.close_led()
        self.close_buzzer()
