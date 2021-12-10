/*
 * View model for OctoPrint-ShutdownButtonLEDBuzzer
 *
 * Author: Daniele Borgo
 * License: AGPLv3
 */
$(function() {
    function ShutdownbuttonledbuzzerViewModel(parameters) {
        let self = this;

        // assign the injected parameters, e.g.:
        // self.loginStateViewModel = parameters[0];
        self.settingsViewModel = parameters[0];

        // TODO: Implement your plugin's view model here.

        self.onBeforeBinding = function() {

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
        elements: [ /* "#settings_plugin_shutdownbuttonledbuzzer" */  ]
    });
});
