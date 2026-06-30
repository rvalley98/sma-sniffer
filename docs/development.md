# Entwicklung & Erweiterung

## Lokal ausführen

```bash
pip install -r app/requirements.txt
python app/main.py        # benötigt eine .env im Arbeitsverzeichnis
```

Die CLI-Tools (`discover_speedwire.py`, `speedwire_data2.py`) brauchen keine
Abhängigkeiten und laufen mit reinem `python3`.

## Sensor-Helfer

In `app/devices/base.py`:

| Helfer            | Einheit | `device_class` | `state_class`      |
| ----------------- | ------- | -------------- | ------------------ |
| `power_sensor`    | W       | `power`        | `measurement`      |
| `battery_sensor`  | %       | `battery`      | `measurement`      |
| `energy_sensor`   | kWh     | `energy`       | `total_increasing` |
| `sensor`          | frei    | frei           | frei (Standard `measurement`) |

## Neues Multicast-Gerät (Energy-Meter-artig)

1. Neue Datei in `app/devices/`, Unterklasse von `SmaDevice`.
2. `matches(telegram)` (Standard: Vergleich per Seriennummer), `handle(telegram)`
   → Liste von `(topic_suffix, wert)`, `ha_sensors()` → Sensor-Definitionen.
3. In `app/main.py` in `build_devices()` registrieren.

```python
from devices.base import SmaDevice, power_sensor

class MyMeter(SmaDevice):
    role = "submeter"
    name = "Sub Meter"

    def handle(self, telegram):
        return [("submeter/power_w", telegram.net_active_power_w())]

    def ha_sensors(self):
        return [power_sensor("sma_submeter_w", "Sub Meter", "submeter/power_w")]
```

## Neuer gepollter Wechselrichter

1. Neue Datei in `app/devices/`, Unterklasse von `PolledInverter`.
2. `read(client)` → Liste von `(topic_suffix, wert)`, `ha_sensors()`.
3. In `app/main.py` in `build_inverters()` registrieren (mit eigener `*_IP`).

```python
from devices.base import PolledInverter, power_sensor

class MyInverter(PolledInverter):
    role = "extra"
    name = "Extra Inverter"

    def read(self, client):
        return [("extra/power_w", client.ac_power_w())]

    def ha_sensors(self):
        return [power_sensor("sma_extra_w", "Extra Power", "extra/power_w")]
```

## Neues Register hinzufügen

1. Mit dem Dump-Modus die LRI + Skalierung ermitteln (siehe
   [cli-tools.md](cli-tools.md)).
2. In `app/speedwire_data2.py` Register-Konstanten + eine Client-Methode
   ergänzen:
   - Momentanwert (32-bit): Muster wie `ac_power_w` über `_read_value`.
   - Zähler (64-bit): LRI ins Set `_COUNTER_LRIS` aufnehmen und über
     `read_wh_counters` auswerten.
3. Die Methode in der passenden `read()`-Methode des Geräts aufrufen und einen
   `energy_sensor`/`sensor` in `ha_sensors()` ergänzen.

## Tests

Die Byte-Konstruktion und das Antwort-Parsing lassen sich ohne Hardware gegen
aufgezeichnete Rohbytes prüfen (Hex aus den `[DATA2] <-`-Logzeilen). Beispiel:

```python
import speedwire_data2 as d
resp = bytes.fromhex("…")            # echte Antwort
for lri, cls, ts, v32, v64 in d.dump_records(resp):
    print(hex(lri), v32, v64)
```

So wurden Werte-Offset (Byte 62), Energie-Register und Skalierungen gegen die
echten Geräte verifiziert.
