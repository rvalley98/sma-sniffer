# sma-sniffer

Passiver Listener für **SMA Speedwire** Multicast-Telegramme. Liest die
Leistungsdaten des SMA Energy Meter / Sunny Home Manager (Netzanschlusspunkt)
mit, dekodiert sie über OBIS und veröffentlicht sie per **MQTT** – inklusive
**Home Assistant MQTT Discovery**.

Optional lassen sich weitere SMA-Geräte (Sunny Tripower PV-Wechselrichter,
Sunny Island Batterie-Wechselrichter) anhand ihrer Seriennummer zuordnen,
sofern sie ebenfalls Speedwire-Telegramme senden.

## Funktionsweise

- Lauscht auf der Speedwire-Multicast-Gruppe `239.12.255.254:9522`.
- Filtert auf SMA-Energy-Meter-Telegramme (Protokoll `0x6069`).
- Dekodiert die OBIS-Kanäle und berechnet die **Netto-Wirkleistung**
  (`P+ − P−`): positiv = Netzbezug, negativ = Einspeisung.
- Ordnet jedes Telegramm einem Gerät zu und veröffentlicht es per MQTT.
- Der Grid-Zähler wird automatisch über seine SUSY-ID erkannt
  (270 = SMA Energy Meter, 372 = Sunny Home Manager 2.0).

## Voraussetzungen

- Docker / Docker Compose
- Der Host muss die Speedwire-Multicast-Pakete empfangen können – deshalb läuft
  der Container im `network_mode: host` (siehe `compose.yaml`).
- Ein erreichbarer MQTT-Broker.

## Konfiguration

Die Konfiguration erfolgt über eine `.env` im Projektverzeichnis. Als Vorlage
dient `.env.example`:

```bash
cp .env.example .env
```

Anschließend die Werte eintragen:

| Variable         | Pflicht | Beschreibung                                                        |
| ---------------- | ------- | ------------------------------------------------------------------- |
| `MQTT_HOST`      | ja      | Hostname/IP des MQTT-Brokers                                         |
| `MQTT_PORT`      | ja      | Port des MQTT-Brokers (z. B. `1883`)                                 |
| `MQTT_USER`      | ja      | MQTT-Benutzername                                                    |
| `MQTT_PASS`      | ja      | MQTT-Passwort                                                        |
| `METER_SERIAL`   | nein    | Seriennummer des Energy Meters (sonst Auto-Erkennung via SUSY-ID)   |
| `PV_SERIAL`      | nein    | Seriennummer des Sunny Tripower (PV-Wechselrichter)                 |
| `BATTERY_SERIAL` | nein    | Seriennummer des Sunny Island (Batterie-Wechselrichter)             |

> Die `.env` ist über `.gitignore` ausgeschlossen und wird bei `git pull` nicht
> überschrieben.

### Geräte zuordnen (PV & Batterie)

Der Grid-Zähler funktioniert ohne weitere Konfiguration. PV und Batterie werden
erst veröffentlicht, wenn ihre Seriennummer gesetzt ist. So findest du sie:

1. Container starten und Logs beobachten (siehe unten).
2. Nach Zeilen wie dieser Ausschau halten:
   ```
   [DEVICE] unmapped susy=123 serial=1900112233 net_power=... W obis=[...]
   ```
3. Die passende `serial` in `PV_SERIAL` bzw. `BATTERY_SERIAL` (und ggf.
   `METER_SERIAL`) in der `.env` eintragen und den Container neu starten.

> Hinweis: Nicht alle SMA-Wechselrichter senden ihre Leistung per
> Speedwire-Broadcast. Erscheinen für Tripower/Island keine `[DEVICE]`-Zeilen,
> liefern sie passiv keine Daten – dann wäre aktives Polling (Speedwire Data2+
> oder Modbus TCP) nötig.

## Starten

```bash
docker compose up -d --build
```

Logs ansehen:

```bash
docker compose logs -f sma-decoder
```

Stoppen:

```bash
docker compose down
```

## MQTT-Topics

Basis-Topic: `sma-sniffer/energy`

| Topic                          | Beschreibung                              |
| ------------------------------ | ----------------------------------------- |
| `sma-sniffer/energy/grid/power_w`    | Netzleistung in W (+ Bezug / − Einspeisung) |
| `sma-sniffer/energy/pv/power_w`      | PV-Leistung in W (sofern zugeordnet)        |
| `sma-sniffer/energy/battery/power_w` | Batterieleistung in W (sofern zugeordnet)   |

### Home Assistant

Ist `HA_DISCOVERY` aktiv (Standard), werden die Sensoren automatisch per MQTT
Discovery unter dem Gerät **„SMA Sniffer Energy System"** angelegt. Es ist keine
manuelle `configuration.yaml` nötig.

## Projektstruktur

```
app/
├── main.py              # Einstiegspunkt: Socket, Dispatch-Loop, Discovery-Logging
├── config.py            # Konfiguration aus der .env
├── speedwire.py         # OBIS-Parser + Telegram-Klasse
├── mqtt_publisher.py    # MQTT-Publish + Home-Assistant-Discovery
└── devices/
    ├── base.py          # SmaDevice (Basisklasse) + Sensor-Helfer
    ├── energy_meter.py  # EnergyMeter   → grid    (Auto-Erkennung via SUSY-ID)
    ├── sunny_tripower.py# SunnyTripower → pv      (via PV_SERIAL)
    └── sunny_island.py  # SunnyIsland   → battery (via BATTERY_SERIAL)
```

Ein neuer Gerätetyp lässt sich durch eine weitere Datei in `devices/` und eine
Zeile in `build_devices()` (`main.py`) ergänzen.

## Lokale Entwicklung

```bash
pip install -r app/requirements.txt
python app/main.py
```

Es wird eine `.env` im Arbeitsverzeichnis benötigt.
