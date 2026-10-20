"""Install an ESPHome firmware on a stock Sonoff S60 through its own updater.

Usage: python send_firmware.py firmware.ota.bin [--plug-ip IP] [--email EMAIL]

`firmware.ota.bin` is the ESPHome build in OTA format (an ESP32-C3 app image).
The script wraps it in the Sonoff update format, checks it, and sends the
plug an eWeLink `upgrade` command that points to this computer. The stock
updater writes it into the spare app slot and boots it. The partition table,
bootloader and NVS stay as they are.

Needs the Sonoff-OTA checkout next to this file (./Sonoff-OTA), the plug in an
eWeLink account with LAN Control on, and internet access for the plug.
"""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "Sonoff-OTA"
sys.path.insert(0, str(ROOT))

from tools.analyze_vendor_ota import analyze  # noqa: E402
from tools.autoflash import hostsys  # noqa: E402
from tools.autoflash.prompts import ask_secret, ask_text  # noqa: E402
from tools.build_vendor_ota import build_wrapper, wrapper_version  # noqa: E402
from tools.s60_autoflash import DELIVERY_PORTS  # noqa: E402
from tools.s60_readout import Stop, account_email, choose_plug, deliver, query_plug  # noqa: E402

CONFIRM_WORD = "ESPHOME"


def wrap(firmware: Path, out: Path) -> str:
    """Wrap the ESPHome image for the stock updater, validate it and return its version."""
    payload = firmware.read_bytes()
    version = wrapper_version(payload, None)
    wrapped = build_wrapper(payload, version=version)
    report = analyze(wrapped)
    wrapper, esp = report["wrapper"], report["esp_image"]
    checks = (wrapper["magic_valid"], wrapper["header_crc32_valid"], wrapper["payload_crc32_valid"],
              wrapper["record_crc32_valid"], esp["chip_is_esp32_c3"], esp["checksum_valid"],
              esp["sha256_valid"] is not False, esp["trailing_bytes"] == 0)
    if not all(checks):
        raise Stop(f"the wrapped image failed validation: {report}")
    out.write_bytes(wrapped)
    print(f"Wrapped {firmware.name}: version {version}, {len(wrapped):,} bytes, "
          f"SHA-256 {hashlib.sha256(wrapped).hexdigest()[:16]}...")
    return version


def run(args: argparse.Namespace) -> int:
    if not (ROOT / "RECOVERY_LOCK").exists():
        raise Stop("RECOVERY_LOCK is not in place in Sonoff-OTA; refusing to start")

    work = ROOT / "captures" / "esphome-install" / f"run-{time.strftime('%Y%m%d-%H%M%S')}"
    work.mkdir(parents=True, exist_ok=True)
    wrapped = work / "esphome.ota"
    wrap(args.firmware, wrapped)

    plug_ip = choose_plug(args.plug_ip)
    listen_ip = args.listen_ip or hostsys.local_ip_towards(plug_ip)
    port = hostsys.first_free_port(listen_ip, DELIVERY_PORTS)
    if port is None:
        raise Stop("no free port for serving the firmware")

    email = account_email(args.email)
    env = {**os.environ, "EWELINK_PASSWORD": ask_secret(f"eWeLink password for {email}: ")}
    version = query_plug(plug_ip, email, env, work)
    print(f"\nSonoff S60 at {plug_ip}, running Sonoff {version}.")
    print("The stock firmware has no automatic rollback: if ESPHome does not start,")
    print("the plug needs opening and a serial adapter to recover.")
    print("Keep the plug powered until ESPHome has started.")
    if ask_text(f"Type {CONFIRM_WORD} to install ESPHome on this plug").strip() != CONFIRM_WORD:
        print("Stopped. Nothing was sent to the plug.")
        return 1

    rule = None
    try:
        if hostsys.active_firewall():
            print("Adding a temporary firewall rule so the plug can fetch the firmware.")
            try:
                rule = hostsys.open_firewall(plug_ip, [port])
            except OSError as exc:
                print(f"Could not add it ({exc}); carrying on.")
        code = deliver(plug_ip, listen_ip, port, email, version, work, env, wrapped, args.verbose)
    finally:
        env.pop("EWELINK_PASSWORD", None)
        if rule is not None and not hostsys.close_firewall(rule):
            print("Remove the temporary firewall rule yourself:")
            for line in hostsys.undo_commands(rule):
                print("  " + line)

    if code == 2:
        raise Stop("the sender refused before contacting the plug; nothing was sent")
    print(f"\nSender finished with code {code}; its log is {work / 'sender.log'}.")
    print("ESPHome should come up within a minute and appear in Home Assistant.")
    return code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("firmware", type=Path, help="ESPHome build in OTA format (firmware.ota.bin)")
    parser.add_argument("--plug-ip", help="the plug's address, instead of looking for it")
    parser.add_argument("--email", help="the eWeLink account the plug is in")
    parser.add_argument("--listen-ip", help="this computer's address as the plug sees it")
    parser.add_argument("-v", "--verbose", action="store_true", help="show the sender's full output")
    args = parser.parse_args()
    try:
        return run(args)
    except Stop as exc:
        print(f"\nStopped: {exc}.", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nStopped.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
