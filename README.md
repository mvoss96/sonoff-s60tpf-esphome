# Sonoff S60TPF → ESPHome, over the air

Install ESPHome on a stock Sonoff iPlug S60TPF (EU, Type E/F, ESP32-C3)
without opening it, and keep its factory energy-meter calibration.

The plug's own Sonoff updater installs the ESPHome firmware. The bootloader,
partition table and settings memory (NVS) stay as they are, and ESPHome reads
the per-plug calibration that Sonoff stored there at the factory. No Tasmota
step is needed.

This repository contains:

| File | Purpose |
|---|---|
| `sonoff-s60tpf.yaml` | ESPHome package for the plug (relay, button, LED, power meter, calibration) |
| `example.yaml` | Example device configuration using the package |
| `send_firmware.py` | Sends an ESPHome build to a stock plug through its Sonoff updater |

Tested on two S60TPF plugs running Sonoff firmware 1.2.0, with ESPHome
2026.9.1. The UK model S60TPG has the same chip and updater but has not been
tried.

## Read this first

**This is a mains-voltage device, and the first install cannot be undone over
the air.** The stock firmware has no automatic rollback: if the ESPHome image
does not start, the plug has to be opened (the case is welded) and flashed
over a USB-serial adapter. Keep the plug powered until ESPHome has come up.

Only do this with a plug you can afford to lose. It ends Sonoff support and
eWeLink control.

## How it works

The S60 accepts an eWeLink `upgrade` command that tells it where to download
a new firmware. `send_firmware.py` wraps the ESPHome image in the Sonoff
update format, serves it from your computer and sends the plug that command,
pointing to your computer. The stock updater writes ESPHome into its spare
app slot and boots it. From then on it is a normal ESPHome device with normal
OTA updates.

The eWeLink and update-format parts come from
[adamsthws/Sonoff-OTA](https://github.com/adamsthws/Sonoff-OTA), which converts
the S60 to Tasmota. `send_firmware.py` reuses its code to send ESPHome directly
instead.

## What you need

- The plug, added to an eWeLink account, with **LAN Control** turned on in its
  settings in the eWeLink app.
- Sonoff firmware 1.2.0 on the plug (1.1.1 is likely fine as well; Sonoff-OTA
  supports both). Do not update it further through eWeLink, newer versions are
  untested.
- Internet access for the plug during the install: the command reaches it
  through the eWeLink cloud.
- A computer on the same network with Python 3.10 or newer and git. If its
  firewall is on, the script adds a temporary rule so the plug can download
  the firmware, which needs administrator rights.
- ESPHome (the Home Assistant ESPHome Device Builder or the `esphome` command).

## Steps

### 1. Get this repository and Sonoff-OTA

```sh
git clone https://github.com/mvoss96/sonoff-s60tpf-esphome.git
cd sonoff-s60tpf-esphome
git clone https://github.com/adamsthws/Sonoff-OTA.git
git -C Sonoff-OTA checkout 9a20bf0
```

`send_firmware.py` expects the Sonoff-OTA checkout in the folder next to it.
It imports internal functions of Sonoff-OTA, which may change in later
versions; `9a20bf0` is the commit it was last checked against.

### 2. Optional: back up the stock firmware

The install keeps NVS but overwrites the spare app slot, and the first ESPHome
OTA update afterwards overwrites the slot holding the Sonoff firmware. Without
a backup there is no way back to stock.

Sonoff-OTA can read the whole flash over Wi-Fi (`tools/s60_readout.py`); the
read-only firmware it needs has to be built first, see
`Sonoff-OTA/archive/bridge/README.md`. The dump contains your Wi-Fi password
and the plug's eWeLink keys in plain text, so keep it private.

### 3. Build the ESPHome firmware

Create a device configuration like `example.yaml`, with your own `name` and
`friendly_name`, and a `secrets.yaml` with `wifi_ssid` and `wifi_password`.
You can add your own settings below the package, for example an `api:`
encryption key.

Build it and get the image in **OTA format**:

- ESPHome Device Builder: *Install* → *Manual download* → *OTA format*
  (`<name>-firmware.ota.bin`).
- Command line: `esphome compile smartplug-kitchen.yaml`, then use
  `.esphome/build/<name>/build/firmware.ota.bin`.

Do not use the factory image: the Sonoff updater only accepts an app image.

### 4. Install it on the plug

```sh
python send_firmware.py path/to/firmware.ota.bin
```

The script:

1. wraps and checks the image,
2. looks for Sonoff plugs on the network and lets you pick one
   (or use `--plug-ip`),
3. asks for the eWeLink email and password and confirms the plug is an S60,
4. asks you to type `ESPHOME`, then sends the update.

The plug downloads the image (about 900 KB), restarts and should show up as
an ESPHome device within a minute. A log of each run is kept in
`Sonoff-OTA/captures/esphome-install/`.

### 5. Add it to Home Assistant

Home Assistant discovers the new device; add it with the ESPHome integration.
The old eWeLink/SonoffLAN device can be removed. Later updates are normal
ESPHome OTA updates from the Device Builder.

## The package

Entities: `Relay` (switch), `current`, `voltage`, `power`, `energy` (kWh, kept
across restarts) and a diagnostic `Calibration` text sensor.

- **Button** (GPIO9) toggles the relay. The relay turns on after a power cut.
- **Overload cut-off:** the relay turns off above `max_power` (default
  3680 W, 16 A at 230 V) and a notification is created in Home Assistant.
  Override it with a `max_power` substitution in the device file.
- **Energy** is counted from the meter chip's energy pulses rather than by
  integrating the power reading, so small loads are counted correctly.
- **Logging** goes to UART0; the USB pins are used as a board-ID input.
- **App version:** the image's ESP-IDF version field is set to `2.0.0`,
  because the Sonoff updater accepts at most 7 characters there.

### Factory calibration

Each plug is calibrated at the factory. The stock firmware stores the result
in NVS (namespace `user_unusual`, key `content`, field `calib_coefficient0`)
as two sets of coefficients: one used below 300 W and one from 300 W on, each
holding `a, b, c` for current, voltage and power. The stock firmware applies
`value = a·x²/1e7 + b·x/1e6 + c/1e6` with `x` in mA, mV or mW. It also scales
voltage and power by 1.02 unless GPIO6, GPIO10 and GPIO19 all read high at
boot (a hardware-variant marker).

The package does the same at every boot. It keeps a copy of the coefficients
in its own saved state, so they remain if NVS is ever erased. The
`Calibration` sensor shows where they came from (`stock NVS`, `saved copy` or
`missing`) and which factor applies.

On both plugs examined, the set below 300 W was the identity, so readings
under 300 W are uncalibrated, as on stock.

### Small loads

Below a few watts the meter chip reports a new power value only every few
seconds. ESPHome up to 2026.10 reports 0 W between those values, so a 2 W load
alternates between its value and 0 W. This is fixed in the `cse7766` driver
from ESPHome 2026.11
([esphome/esphome#20631](https://github.com/esphome/esphome/pull/20631)); the
package picks it up when you update ESPHome, nothing needs changing.

## Pins

| GPIO | Function |
|---|---|
| 4 | Relay |
| 5 | Status LED (inverted) |
| 7 | CSE7766 meter, UART RX (4800 baud, even parity) |
| 9 | Button (inverted, pull-up) |
| 6, 10, 19 | Board-variant input, read once at boot |

## Credits

- [adamsthws/Sonoff-OTA](https://github.com/adamsthws/Sonoff-OTA) for the
  eWeLink update mechanism and the Sonoff update format.
