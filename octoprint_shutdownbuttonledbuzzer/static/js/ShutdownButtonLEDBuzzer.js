/*
 * Copyright (C) 2022 Daniele Borgo
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
    function ShutdownButtonLEDBuzzerViewModel(parameters) {
        let self = this;

        self.settingsViewModel = parameters[0];

        self.i2c_status = ko.observable("_");
        self.spi_status = ko.observable("-");
        self.updated_hour = ko.observable("-");

        self.set_hour = function (){
            let date = new Date($.now());
            self.updated_hour(date.toLocaleDateString() + " " + date.toLocaleTimeString());
        }

        self.refresh = function (){
            self.updated_hour("Updating...");
            self.i2c_status("Loading...");
            self.spi_status("Loading...");

            $.ajax({
                url: API_BASEURL + "plugin/shutdownbuttonledbuzzer",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "services_status"
                })
            }).done(function (data) {
                self.i2c_status(data.i2c_status);
                self.spi_status(data.spi_status);
            }).fail(function () {
                self.i2c_status("Error in retrieving");
                self.spi_status("Error in retrieving");
            }).always(function () {
                self.set_hour();
            });
        }

        self.onStartupComplete = function () {
            self.refresh();
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ShutdownButtonLEDBuzzerViewModel,
        dependencies: [ "settingsViewModel" ],
        elements: [ "#settings_plugin_shutdownbuttonledbuzzer" ]
    });
});
