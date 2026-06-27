import json
import paho.mqtt.client as mqtt


class MqttPublisher:
    """Wraps the MQTT client and Home Assistant discovery."""

    def __init__(self, host, port, user, password,
                 base_topic, ha_prefix, device_id):
        self.base_topic = base_topic
        self.ha_prefix = ha_prefix
        self.device_id = device_id

        self.client = mqtt.Client()
        self.client.username_pw_set(user, password)
        self.client.connect(host, port, 60)
        self.client.loop_start()

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
