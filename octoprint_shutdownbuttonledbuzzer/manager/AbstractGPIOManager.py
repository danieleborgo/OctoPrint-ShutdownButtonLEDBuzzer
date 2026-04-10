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

from abc import ABC, abstractmethod


class AbstractGPIOManager(ABC):
    """
    Abstract base class for GPIO managers.

    Each concrete implementation wraps a specific GPIO library (e.g. periphery,
    gpiozero) and exposes a uniform interface for the three hardware components
    used by this plugin: a shutdown button, a status LED, and a buzzer.

    A manager owns the GPIO resources it opens. Components must be explicitly
    set up before use and closed when no longer needed. Calling a setup method
    on an already-configured component closes the previous one first.
    """

    @staticmethod
    @abstractmethod
    def supports_pwm() -> bool:
        """
        Return True if this implementation can drive a passive (PWM) buzzer.

        When False, the plugin forces the buzzer type to active and hides the
        passive buzzer option in the UI.
        """
        pass

    @abstractmethod
    def setup_button(self, pin: int, hold_time: float, callback) -> None:
        """
        Configure the shutdown button on the given BCM pin.

        The button is expected to be wired active-low (pressed = LOW). An
        internal pull-up resistor is applied where the underlying library and
        kernel support it; otherwise an external one is required.

        :param pin: BCM pin number.
        :param hold_time: Seconds the button must be held before firing
                          (used by implementations that support hold detection).
        :param callback: Callable invoked on each press event. Must be
                         thread-safe as it is called from a background thread.
        """
        pass

    @abstractmethod
    def close_button(self) -> None:
        """Release the button GPIO and stop any associated background thread."""
        pass

    @abstractmethod
    def setup_led(self, pin: int) -> None:
        """
        Configure the status LED on the given BCM pin and turn it on.

        The LED stays on from plugin startup until the GPIO subsystem shuts
        down, giving a visual indication that the Raspberry Pi is running.

        :param pin: BCM pin number.
        """
        pass

    @abstractmethod
    def close_led(self) -> None:
        """Release the LED GPIO. The LED state after closing is implementation-defined."""
        pass

    @abstractmethod
    def setup_buzzer(self, pin: int, is_active: bool) -> None:
        """
        Configure the buzzer on the given BCM pin.

        :param pin: BCM pin number.
        :param is_active: True for an active buzzer (driven by a simple HIGH/LOW
                          signal); False for a passive buzzer (requires PWM).
        """
        pass

    @abstractmethod
    def close_buzzer(self) -> None:
        """Release the buzzer GPIO."""
        pass

    @abstractmethod
    def emit_beep(self, n: int, beep_ms: int, note: int) -> None:
        """
        Emit n beeps synchronously, blocking until all beeps are complete.

        Each beep lasts beep_ms milliseconds, followed by a silence of the
        same duration. For passive buzzers the tone is derived from the MIDI
        note number.

        :param n: Number of beeps. No-op if <= 0 or the buzzer is not set up.
        :param beep_ms: Duration of each beep and each gap, in milliseconds.
        :param note: MIDI note number (21-108) used as the tone for passive
                     buzzers. Ignored for active buzzers.
        """
        pass

    @abstractmethod
    def close_all(self) -> None:
        """Close all components: button, LED, and buzzer."""
        pass
