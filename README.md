# ShutdownButtonLEDBuzzer

This OctoPrint plugin implements a shutdown physical button
for the Rasperry Pi. It offers also a status LED to know when
OctoPrint is ready and a buzzer to signal the startup and
the shutdown. Remember that these signals may vary of few
seconds.

## Setup

Install via the bundled [Plugin Manager](https://docs.octoprint.org/en/master/bundledplugins/pluginmanager.html)
or manually using this URL:

    https://github.com/danieleborgo/OctoPrint-ShutdownButtonLEDBuzzer/archive/master.zip


## Circuit

The circuit hereafter exposed is just the one set by default,
since the plugin allows to edit each of these pin:

- Button: by default directly on pin GPIO26
- LED: by default on pin GPIO6
- Buzzer: by default on pin GPIO12

In case one of these features is not needed, it can be
deactivated by the apposite settings section.

![circuit](docs/circuit.png)

## Configuration

This plugin offers several configuration parameters,
accessible in the apposite OctoPrint section in setting:

![settings1](docs/settings1.png)
![settings2](docs/settings2.png)
![settings3](docs/settings3.png)

## License

This software is distributed on GPLv3.0, more information
available in [LICENSE.md](LICENSE.md).
