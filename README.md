# Sonoff S60TPF → ESPHome, over the air

Install ESPHome on a stock Sonoff iPlug S60TPF without opening it. The plug's
own Sonoff updater installs the image; bootloader, partitions and NVS stay
unchanged, and ESPHome uses the per-plug factory calibration stored in NVS.

Tested on two S60TPF with Sonoff firmware 1.2.0 and ESPHome 2026.9.1.

> **Warning:** mains voltage. If the first ESPHome image does not start, the
> plug has to be opened and flashed over serial. Keep it powered until ESPHome
> is up.

## Requirements

- Plug in an eWeLink account, **LAN Control** on, Sonoff firmware 1.2.0,
  internet access during the install.
- Computer on the same network with Python 3.10+ and git.

## Steps

1. Clone this repo and [Sonoff-OTA](https://github.com/adamsthws/Sonoff-OTA)
   into it (`send_firmware.py` uses its eWeLink and update-format code):

   ```sh
   git clone https://github.com/mvoss96/sonoff-s60tpf-esphome.git
   cd sonoff-s60tpf-esphome
   git clone https://github.com/adamsthws/Sonoff-OTA.git
   git -C Sonoff-OTA checkout 9a20bf0
   ```

2. Create a device config like `example.yaml` and build it. Use the image in
   **OTA format** (Device Builder: *Install → Manual download → OTA format*;
   CLI: `.esphome/build/<name>/build/firmware.ota.bin`).

3. Install it:

   ```sh
   python send_firmware.py path/to/firmware.ota.bin
   ```

   Pick the plug, enter the eWeLink login, type `ESPHOME` to confirm. The plug
   restarts into ESPHome within a minute.

4. Add it in Home Assistant. Later updates are normal ESPHome OTA updates.

## Notes

- **Calibration:** the package reads `calib_coefficient0` from NVS at boot and
  applies it like the stock firmware, including the 1.02 board-variant factor.
  The `Calibration` diagnostic sensor shows the source.
- **Small loads:** before ESPHome 2026.11, loads of a few watts alternate
  between their value and 0 W. Fixed by
  [esphome/esphome#20631](https://github.com/esphome/esphome/pull/20631).
- **Back to stock:** bootloader, partitions and NVS are untouched, so the
  Sonoff app image (the same on every plug) flashed with ESPHome OTA should
  boot stock with its eWeLink pairing. Not tested yet.
