import os

# Load a local .env for development. In the container the variables are provided
# by Docker Compose (env_file), so python-dotenv is optional there.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable '{name}'. "
            "Please provide it via a .env file (see .env.example)."
        )
    return value


def _optional_int(name: str):
    value = os.getenv(name)
    return int(value) if value else None


# Speedwire multicast group of SMA devices
MCAST_GRP = "239.12.255.254"
MCAST_PORT = 9522

# MQTT broker (required, from .env)
MQTT_HOST = _require("MQTT_HOST")
MQTT_PORT = int(_require("MQTT_PORT"))
MQTT_USER = _require("MQTT_USER")
MQTT_PASS = _require("MQTT_PASS")

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
