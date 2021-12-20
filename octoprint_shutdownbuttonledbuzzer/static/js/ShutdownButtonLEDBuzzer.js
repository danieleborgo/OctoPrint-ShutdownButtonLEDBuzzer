/*
 * View model for OctoPrint-ShutdownButtonLEDBuzzer
 *
 * Author: Daniele Borgo
 * License: GPLv3
 */

$(function() {
    function ShutdownbuttonledbuzzerViewModel(parameters) {
        let self = this;

        self.settingsViewModel = parameters[0];

        self.i2c_status = ko.observable("_")
        self.spi_status = ko.observable("-")
        self.updated_hour = ko.observable("-")

        self.set_hour = function (){
            let date = new Date($.now())
            self.updated_hour(date.toLocaleDateString() + " " + date.toLocaleTimeString())
        }

        self.refresh = function (){
            self.updated_hour("Updating...")
            self.i2c_status("Loading...")
            self.spi_status("Loading...")

            $.ajax({
                url: API_BASEURL + "plugin/shutdownbuttonledbuzzer",
                type: "POST",
                dataType: "json",
                contentType: "application/json; charset=UTF-8",
                data: JSON.stringify({
                    command: "services_status"
                })
            }).done(function (data) {
                self.i2c_status(data.i2c_status)
                self.spi_status(data.spi_status)
            }).fail(function () {
                self.i2c_status("Error in retrieving")
                self.spi_status("Error in retrieving")
            }).always(function () {
                self.set_hour()
            });
        }

        self.onStartupComplete = function () {
            self.refresh()
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: ShutdownbuttonledbuzzerViewModel,
        dependencies: [ "settingsViewModel" ],
        elements: [ "#settings_plugin_shutdownbuttonledbuzzer" ]
    });
});
