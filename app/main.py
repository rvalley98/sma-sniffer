import socket
import struct
import time

import config
import speedwire
from mqtt_publisher import MqttPublisher
from devices.energy_meter import EnergyMeter
from devices.sunny_tripower import SunnyTripower
from devices.sunny_island import SunnyIsland


def build_devices():
    """Build the list of active devices based on the configuration.

    The grid meter is always active (auto-detected by SUSY id). The PV and
    battery devices are only added once their serial is set in the .env.
    """
    devices = [EnergyMeter(config.METER_SERIAL)]

    if config.PV_SERIAL is not None:
        devices.append(SunnyTripower(config.PV_SERIAL))

    if config.BATTERY_SERIAL is not None:
        devices.append(SunnyIsland(config.BATTERY_SERIAL))

    return devices


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
    devices = build_devices()

    mqtt = MqttPublisher(
        config.MQTT_HOST, config.MQTT_PORT, config.MQTT_USER, config.MQTT_PASS,
        config.BASE_TOPIC, config.HA_DISCOVERY_PREFIX, config.DEVICE_ID,
    )

    if config.HA_DISCOVERY:
        time.sleep(2)
        mqtt.publish_ha_discovery(devices)

    sock = open_socket()
    print("Listening SMA Speedwire...")

    seen_unmapped = set()

    while True:
        data, _ = sock.recvfrom(4096)

        telegram = speedwire.parse(data)
        if telegram is None:
            continue

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
            print(
                f"[{device.role.upper()}] serial={telegram.serial} "
                f"{topic_suffix} = {value}"
            )


if __name__ == "__main__":
    main()
