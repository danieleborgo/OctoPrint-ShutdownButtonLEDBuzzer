/*
 * View model for OctoPrint-ShutdownButtonLEDBuzzer
 *
 * Author: Daniele Borgo
 * License: GPLv3
 */

$(function() {
    function ShutdownbuttonledbuzzerViewModel(parameters) {
        let self = this;

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        self.settingsViewModel = parameters[0];

        // TODO: Implement your plugin's view model here.

        self.i2c_status = ko.observable("loading...")
        self.spi_status = ko.observable("loading...")

        self.refresh = function (){
            $.get(
                API_BASEURL + "plugin/shutdownbuttonledbuzzer",
                function (data) {
                    let parsed = JSON.parse(data)
                    self.i2c_status(parsed.i2c_status)
                    self.spi_status(parsed.spi_status)
                }
            )
        }

        self.onStartupComplete = function () {
            self.refresh()
        }
    }

    /* view model class, parameters for constructor, container to bind to
     * Please see http://docs.octoprint.org/en/master/plugins/viewmodels.html#registering-custom-viewmodels for more details
     * and a full list of the available options.
     */
    OCTOPRINT_VIEWMODELS.push({
        construct: ShutdownbuttonledbuzzerViewModel,
        // ViewModels your plugin depends on, e.g. loginStateViewModel, settingsViewModel, ...
        dependencies: [ /* "loginStateViewModel", "settingsViewModel" */ "settingsViewModel"],
        // Elements to bind to, e.g. #settings_plugin_ShutdownButtonLEDBuzzer, #tab_plugin_ShutdownButtonLEDBuzzer, ...
        elements: [ "#settings_plugin_shutdownbuttonledbuzzer"  ]
    });
});
