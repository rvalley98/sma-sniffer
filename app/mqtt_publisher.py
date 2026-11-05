import json
import time

import paho.mqtt.client as mqtt

CONNECT_RETRY_SECONDS = 10


def _log_connect_result(client, userdata, flags, reason_code, properties):
    if reason_code.is_failure:
        print(f"MQTT connection refused by broker: {reason_code}")
    else:
        print("MQTT connected")


class MqttPublisher:
    """Wraps the MQTT client and Home Assistant discovery."""

    def __init__(self, host, port, user, password,
                 base_topic, ha_prefix, device_id):
        self.base_topic = base_topic
        self.ha_prefix = ha_prefix
        self.device_id = device_id

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = _log_connect_result
        self.client.username_pw_set(user, password)
        self._connect(host, port)
        self.client.loop_start()

    def _connect(self, host, port):
        # A stopped app is not restarted automatically, so wait for the broker
        # instead of crashing when it isn't up yet.
        while True:
            try:
                self.client.connect(host, port, 60)
                return
            except OSError as exc:
                print(
                    f"MQTT broker {host}:{port} not reachable ({exc}), "
                    f"retrying in {CONNECT_RETRY_SECONDS}s"
                )
                time.sleep(CONNECT_RETRY_SECONDS)

    def publish(self, topic_suffix, value):
        if value is None:
            return
        self.client.publish(
            f"{self.base_topic}/{topic_suffix}", value, retain=True
        )

    def publish_ha_discovery(self, devices):
        device_info = {
            "identifiers": [self.device_id],
            "name": "SMA Sniffer Energy System",
            "manufacturer": "SMA",
        }

        for device in devices:
            for sensor in device.ha_sensors():
                config_topic = (
                    f"{self.ha_prefix}/sensor/{self.device_id}/"
                    f"{sensor['unique_id']}/config"
                )
                payload = {
                    "name": sensor["name"],
                    "state_topic": f"{self.base_topic}/{sensor['state_topic_suffix']}",
                    "unique_id": sensor["unique_id"],
                    "unit_of_measurement": sensor["unit_of_measurement"],
                    "device_class": sensor["device_class"],
                    "state_class": sensor["state_class"],
                    "device": device_info,
                }
                self.client.publish(
                    config_topic, json.dumps(payload), retain=True
                )

        print("Home Assistant discovery published")
