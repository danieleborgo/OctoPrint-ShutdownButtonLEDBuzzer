/*
 * Copyright (C) 2026 Daniele Borgo
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

$(function() {
    const RESERVED_PINS = {
        2:  { label: "I2C SDA",  service: "i2c" },
        3:  { label: "I2C SCL",  service: "i2c" },
        7:  { label: "SPI CE1",  service: "spi" },
        8:  { label: "SPI CE0",  service: "spi" },
        9:  { label: "SPI MISO", service: "spi" },
        10: { label: "SPI MOSI", service: "spi" },
        11: { label: "SPI SCLK", service: "spi" },
        14: { label: "UART TX",  service: null  },
        15: { label: "UART RX",  service: null  },
    };

    function ShutdownButtonLEDBuzzerViewModel(parameters) {
        let self = this;

        self.settingsViewModel = parameters[0];
        self.shutdownButtonLEDBuzzer = undefined;

        self.onBeforeBinding = function () {
            self.shutdownButtonLEDBuzzer = self.settingsViewModel.settings.plugins.shutdownbuttonledbuzzer;
        };

        self.i2c_status = ko.observable("-");
        self.spi_status = ko.observable("-");
        self.updated_hour = ko.observable("-");
        self.os_name = ko.observable("");
        self.board_model = ko.observable("");
        self.is_raspberry_pi = ko.observable(null);

        self.library_available = ko.observable(true);
        self.library_supports_pwm = ko.observable(true);
        self.checking = ko.observable(false);
        self.check_message = ko.observable("");
        self.check_success = ko.observable(null);

        self.on_check_click = function () {
            self.checking(true);
            self.check_message("");
            self.check_success(null);

            $.ajax({
                url: API_BASEURL + "plugin/shutdownbuttonledbuzzer",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "check_library",
                    library: self.shutdownButtonLEDBuzzer.gpio_library()
                })
            }).done(function (data) {
                self.library_available(data.available);
                self.library_supports_pwm(data.supports_pwm);
                if (!data.supports_pwm) {
                    self.shutdownButtonLEDBuzzer.is_buzzer_active(true);
                }
                self.check_success(data.available);

                let msg;
                const selected = self.shutdownButtonLEDBuzzer.gpio_library();
                const os = data.os_name || "your OS";
                if (!data.available) {
                    msg = "Library does not work on this system.";
                    if (data.recommended && data.recommended !== selected) {
                        msg += " For " + os + ", " + data.recommended + " is recommended instead.";
                    }
                } else if (data.recommended && data.recommended !== selected) {
                    msg = "Library works, but for " + os + ", " + data.recommended + " is recommended instead.";
                } else {
                    msg = "Library works correctly on this system.";
                }
                self.check_message(msg);
            }).fail(function () {
                self.library_available(false);
                self.library_supports_pwm(false);
                self.check_success(false);
                self.check_message("Failed to check library status.");
            }).always(function () {
                self.checking(false);
            });
        }

        self.set_hour = function () {
            let date = new Date($.now());
            self.updated_hour(date.toLocaleDateString() + " " + date.toLocaleTimeString());
        }

        self.refresh = function () {
            self.updated_hour("Updating...");
            self.i2c_status("Loading...");
            self.spi_status("Loading...");

            $.ajax({
                url: API_BASEURL + "plugin/shutdownbuttonledbuzzer",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({command: "services_status"})
            }).done(function (data) {
                self.i2c_status(data.i2c_status);
                self.spi_status(data.spi_status);
                if (data.os_name) self.os_name(data.os_name);
                if (data.board_model !== undefined) self.board_model(data.board_model);
                if (data.is_raspberry_pi !== undefined) self.is_raspberry_pi(data.is_raspberry_pi);
            }).fail(function () {
                self.i2c_status("Error in retrieving");
                self.spi_status("Error in retrieving");
            }).always(function () {
                self.set_hour();
            });
        }

        self.check_library = function (library) {
            $.ajax({
                url: API_BASEURL + "plugin/shutdownbuttonledbuzzer",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({command: "check_library", library: library})
            }).done(function (data) {
                self.library_available(data.available);
                self.library_supports_pwm(data.supports_pwm);
                if (!data.supports_pwm) {
                    self.shutdownButtonLEDBuzzer.is_buzzer_active(true);
                }
            }).fail(function () {
                self.library_available(false);
                self.library_supports_pwm(false);
            });
        }

        self.pin_options = ko.computed(function() {
            const i2c = self.i2c_status();
            const spi = self.spi_status();
            const options = [];
            for (let pin = 2; pin <= 27; pin++) {
                const reserved = RESERVED_PINS[pin];
                let text = "BCM " + pin;
                let disabled = false;
                if (reserved) {
                    text += " \u2013 " + reserved.label;
                    if (reserved.service === "i2c" && i2c === "enabled") disabled = true;
                    if (reserved.service === "spi" && spi === "enabled") disabled = true;
                }
                options.push({ value: pin, text: text, disabled: disabled });
            }
            return options;
        });

        self.pin_after_render = function(option, item) {
            if (item && item.disabled) option.disabled = true;
        };

        self.has_pin_conflict = ko.computed(function() {
            const s = self.shutdownButtonLEDBuzzer;
            if (!s) return false;
            const pins = [];
            if (s.is_button_en()) pins.push(parseInt(s.button_pin()));
            if (s.is_led_en())    pins.push(parseInt(s.led_pin()));
            if (s.is_buzzer_en()) pins.push(parseInt(s.buzzer_pin()));
            return new Set(pins).size !== pins.length;
        }, null, { deferEvaluation: true });

        self.advanced_expanded = ko.observable(false);

        self.buzzer_type = ko.observable();

        self.onStartupComplete = function () {
            self.buzzer_type(self.shutdownButtonLEDBuzzer.is_buzzer_active() ? "Active" : "Passive");
            self.buzzer_type.subscribe(function (new_value) {
                self.shutdownButtonLEDBuzzer.is_buzzer_active(new_value === "Active");
            });

            self.on_check_click();
            self.shutdownButtonLEDBuzzer.gpio_library.subscribe(function () {
                self.check_message("");
                self.check_success(null);
            });

            self.refresh();
        }

        self._conflict_on_save = false;

        self.onSettingsBeforeSave = function() {
            if (self.has_pin_conflict()) {
                self._conflict_on_save = true;
                new PNotify({
                    title: gettext("ShutdownButtonLEDBuzzer"),
                    text: gettext("Two or more enabled components share the same pin. Settings were not saved."),
                    type: "error",
                    hide: false
                });
            }
        };

        self.onSettingsHidden = function() {
            if (self._conflict_on_save) {
                self._conflict_on_save = false;
                setTimeout(function() {
                    self.settingsViewModel.show("#settings_plugin_shutdownbuttonledbuzzer");
                }, 100);
            }
        };
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ShutdownButtonLEDBuzzerViewModel,
        dependencies: ["settingsViewModel"],
        elements: ["#settings_plugin_shutdownbuttonledbuzzer"]
    });
});
