"""Home Assistant app support: turn the Supervisor's config into env variables.

Outside Home Assistant neither the options file nor the Supervisor exists, so
this does nothing and the .env / Docker Compose setup works unchanged.
"""

import json
import os
import time
import urllib.request

OPTIONS_FILE = "/data/options.json"
SUPERVISOR_URL = "http://supervisor"
MQTT_SERVICE_ATTEMPTS = 12
MQTT_SERVICE_RETRY_SECONDS = 10


def _set_default(name, value):
    if value is not None and value != "":
        os.environ.setdefault(name, str(value))


def _fetch_mqtt_service(token):
    """Return the broker the Supervisor knows about (the Mosquitto app)."""
    request = urllib.request.Request(
        f"{SUPERVISOR_URL}/services/mqtt",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)["data"]


def _use_supervisor_mqtt():
    token = os.getenv("SUPERVISOR_TOKEN")
    if not token or os.getenv("MQTT_HOST"):
        return

    # During boot Mosquitto may register its service a little after we start,
    # and a stopped app is not restarted automatically, so give it some time.
    for attempt in range(1, MQTT_SERVICE_ATTEMPTS + 1):
        try:
            service = _fetch_mqtt_service(token)
            break
        except (OSError, ValueError, KeyError) as exc:
            # urllib.error.HTTPError is an OSError: the Supervisor answers with
            # an error status when no MQTT broker app is available.
            print(
                f"No MQTT broker available from Home Assistant yet ({exc}), "
                f"attempt {attempt}/{MQTT_SERVICE_ATTEMPTS}. "
                "Install the Mosquitto app or set mqtt_host in the configuration."
            )
            if attempt < MQTT_SERVICE_ATTEMPTS:
                time.sleep(MQTT_SERVICE_RETRY_SECONDS)
    else:
        return

    _set_default("MQTT_HOST", service.get("host"))
    _set_default("MQTT_PORT", service.get("port"))
    _set_default("MQTT_USER", service.get("username"))
    _set_default("MQTT_PASS", service.get("password"))
    print(f"Using MQTT broker from Home Assistant: {service.get('host')}")


def load_into_env():
    """Expose the app options as the env variables config.py already reads."""
    if not os.path.exists(OPTIONS_FILE):
        return

    with open(OPTIONS_FILE, encoding="utf-8") as options_file:
        for name, value in json.load(options_file).items():
            _set_default(name.upper(), value)

    _use_supervisor_mqtt()
