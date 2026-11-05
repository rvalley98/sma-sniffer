import os

import ha_app

# Load a local .env for development. In the container the variables are provided
# by Docker Compose (env_file), so python-dotenv is optional there.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass

# As a Home Assistant app the values come from the Supervisor instead.
ha_app.load_into_env()


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required setting '{name}'. Provide it via a .env file "
            "(see .env.example) or, as a Home Assistant app, via its configuration."
        )
    return value


def _optional_int(name: str):
    value = os.getenv(name)
    return int(value) if value else None


def _flag(name: str, default: str = "") -> bool:
    return os.getenv(name, default).lower() in ("1", "true", "yes", "on")


# Speedwire multicast group of SMA devices
MCAST_GRP = "239.12.255.254"
MCAST_PORT = 9522

# MQTT broker. User and password stay empty for brokers without authentication.
MQTT_HOST = _require("MQTT_HOST")
MQTT_PORT = int(os.getenv("MQTT_PORT") or 1883)
MQTT_USER = os.getenv("MQTT_USER") or None
MQTT_PASS = os.getenv("MQTT_PASS") or None

BASE_TOPIC = "sma-sniffer/energy"

# Home Assistant MQTT discovery
HA_DISCOVERY = True
HA_DISCOVERY_PREFIX = "homeassistant"
DEVICE_ID = "sma_sniffer"

# Optional: map devices to roles by serial number (from .env).
# Read the [DEVICE] discovery lines in the log to find each serial.
METER_SERIAL = _optional_int("METER_SERIAL")
PV_SERIAL = _optional_int("PV_SERIAL")
BATTERY_SERIAL = _optional_int("BATTERY_SERIAL")

# Active polling of the inverters via SMA Speedwire Data2+ (query by IP).
# The inverters do not broadcast their power, so they are queried directly.
PV_IP = os.getenv("PV_IP") or None
BATTERY_IP = os.getenv("BATTERY_IP") or None
INVERTER_PASSWORD = os.getenv("INVERTER_PASSWORD", "0000")
INVERTER_USER_GROUP = os.getenv("INVERTER_USER_GROUP", "user").strip().lower()
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))

# Debug: dump all decoded OBIS channels once per device serial.
DEBUG_OBIS = _flag("DEBUG_OBIS")

# Log every published value. The meter alone produces several lines per second,
# which is why the Home Assistant app turns this off by default.
LOG_VALUES = _flag("LOG_VALUES", "1")
