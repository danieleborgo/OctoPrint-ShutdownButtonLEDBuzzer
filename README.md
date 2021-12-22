# ShutdownButtonLEDBuzzer

This plugin implements a shutdown physical button for
the Rasperry. It offers also a status LED to know when
OctoPrint is ready and a buzzer to signal the startup and
the shutdown.

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/danieleborgo/OctoPrint-ShutdownButtonLEDBuzzer/archive/master.zip


## Circuit

- Button: by default directly on pin 26 since pull-up is enabled
via software.
- LED: by default on pin 6
- Buzzer: by default on pin 12

They can be changed in the settings page.

![circuit](docs/circuit.png)

## Configuration

This plugin offers several configuration parameters,
accessible in the apposite OctoPrint section in setting:

![settings1](docs/settings1.png)
![settings2](docs/settings2.png)
![settings3](docs/settings3.png)

The offered three features can be disabled independently.

## License

This software is distributed on GPLv3.0, more information
available in [LICENSE.md](LICENSE.md).
