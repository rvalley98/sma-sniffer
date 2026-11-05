import socket
import struct
import threading
import time

import config
import discover_speedwire
import speedwire
from mqtt_publisher import MqttPublisher
from speedwire_data2 import Data2Client, Data2Error
from devices.energy_meter import EnergyMeter
from devices.sunny_tripower import SunnyTripower
from devices.sunny_island import SunnyIsland


def build_devices():
    """Devices read passively from the Speedwire multicast stream.

    Only the grid meter broadcasts its power (auto-detected by SUSY id, or
    pinned via METER_SERIAL). The inverters are polled separately, see
    build_inverters().
    """
    return [EnergyMeter(config.METER_SERIAL)]


def build_inverters():
    """Inverters that are actively polled by IP via Speedwire Data2+.

    Each is only added once its Speedwire IP is set in the .env.
    """
    inverters = []

    if config.PV_IP is not None:
        inverters.append(SunnyTripower(
            config.PV_IP, config.PV_SERIAL,
            config.INVERTER_PASSWORD, config.INVERTER_USER_GROUP,
        ))

    if config.BATTERY_IP is not None:
        inverters.append(SunnyIsland(
            config.BATTERY_IP, config.BATTERY_SERIAL,
            config.INVERTER_PASSWORD, config.INVERTER_USER_GROUP,
        ))

    return inverters


def poll_inverters(inverters, mqtt):
    """Background loop: query each inverter every POLL_INTERVAL seconds."""
    while True:
        for inv in inverters:
            try:
                with Data2Client(
                    inv.ip, inv.password, inv.user_group,
                    debug=config.DEBUG_OBIS,
                ) as client:
                    results = inv.read(client)
                    discovered = client.serial
            except (Data2Error, OSError) as exc:
                print(f"[{inv.role.upper()}] poll failed ({inv.ip}): {exc}")
                continue

            if inv.serial is not None and discovered != inv.serial:
                print(
                    f"[{inv.role.upper()}] warning: {inv.ip} reports serial "
                    f"{discovered}, expected {inv.serial} (wrong IP?)"
                )

            for topic_suffix, value in results:
                mqtt.publish(topic_suffix, value)
                if config.LOG_VALUES:
                    print(f"[{inv.role.upper()}] {inv.ip} {topic_suffix} = {value}")

        time.sleep(config.POLL_INTERVAL)


def open_socket():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("", config.MCAST_PORT))

    mreq = struct.pack(
        "4s4s",
        socket.inet_aton(config.MCAST_GRP),
        socket.inet_aton("0.0.0.0"),
    )
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
    return sock


def main():
    # Runs before the listener socket exists: the device replies are unicast to
    # port 9522 and would otherwise end up at that socket instead of the scan.
    if config.PV_IP is None or config.BATTERY_IP is None:
        discover_speedwire.report(config.INVERTER_PASSWORD, config.INVERTER_USER_GROUP)

    devices = build_devices()
    inverters = build_inverters()

    mqtt = MqttPublisher(
        config.MQTT_HOST, config.MQTT_PORT, config.MQTT_USER, config.MQTT_PASS,
        config.BASE_TOPIC, config.HA_DISCOVERY_PREFIX, config.DEVICE_ID,
    )

    if config.HA_DISCOVERY:
        time.sleep(2)
        mqtt.publish_ha_discovery(devices + inverters)

    if inverters:
        names = ", ".join(f"{inv.role}@{inv.ip}" for inv in inverters)
        print(f"Polling inverters every {config.POLL_INTERVAL}s: {names}")
        threading.Thread(
            target=poll_inverters, args=(inverters, mqtt), daemon=True
        ).start()

    sock = open_socket()
    print("Listening SMA Speedwire...")

    seen_unmapped = set()
    dumped_serials = set()

    while True:
        data, _ = sock.recvfrom(4096)

        telegram = speedwire.parse(data)
        if telegram is None:
            continue

        if config.DEBUG_OBIS and telegram.serial not in dumped_serials:
            dumped_serials.add(telegram.serial)
            print(
                f"[OBIS] susy={telegram.susy_id} serial={telegram.serial} "
                f"channels:"
            )
            for line in telegram.describe():
                print(line)

        device = next((d for d in devices if d.matches(telegram)), None)

        if device is None:
            # Unknown device: log once so you can map its serial in the .env
            # (e.g. your Sunny Tripower or Sunny Island).
            if telegram.serial not in seen_unmapped:
                seen_unmapped.add(telegram.serial)
                print(
                    f"[DEVICE] unmapped susy={telegram.susy_id} "
                    f"serial={telegram.serial} "
                    f"net_power={telegram.net_active_power_w()} W "
                    f"obis={[hex(k) for k in telegram.obis]}"
                )
            continue

        for topic_suffix, value in device.handle(telegram):
            mqtt.publish(topic_suffix, value)
            if config.LOG_VALUES:
                print(
                    f"[{device.role.upper()}] serial={telegram.serial} "
                    f"{topic_suffix} = {value}"
                )


if __name__ == "__main__":
    main()
