# s60-ota-bridge-flash-readout-4.4.2.ota

Read-only helper firmware for backing up the flash of a stock Sonoff S60. It
is installed through the Sonoff updater by `tools/s60_readout.py` from
Sonoff-OTA, serves the whole flash over Wi-Fi, and returns the plug to its
Sonoff firmware on the next power cycle.

This file is licensed under the **GNU General Public License v3.0**, not under
this repository's MIT license.

Source: [adamsthws/Sonoff-OTA](https://github.com/adamsthws/Sonoff-OTA),
commit `9a20bf0e85258d3cb7ef91ead106732e44ef354e`, directory
`archive/bridge`, PlatformIO environment `s60-ota-bridge-flash-readout`.

Built with:

```sh
cp -r Sonoff-OTA/archive/bridge build-readout
pio run -d build-readout -e s60-ota-bridge-flash-readout
python Sonoff-OTA/tools/build_vendor_ota.py \
  build-readout/.pio/build/s60-ota-bridge-flash-readout/firmware.bin \
  s60-ota-bridge-flash-readout-4.4.2.ota
```

SHA-256: `91f73ce9b59a110e37d3770b6d2d1e90866cb25c7478834466df6ebf9e3d9a3e`
