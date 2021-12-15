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
            $.get(
                API_BASEURL + "plugin/shutdownbuttonledbuzzer",
                function (data) {
                    let parsed = JSON.parse(data)
                    self.i2c_status(parsed.i2c_status)
                    self.spi_status(parsed.spi_status)
                    self.set_hour()
                }
            )
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
