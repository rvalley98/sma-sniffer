# sma-sniffer

Passiver Listener für **SMA Speedwire** Multicast-Telegramme. Liest die
Leistungsdaten des SMA Energy Meter / Sunny Home Manager (Netzanschlusspunkt)
mit, dekodiert sie über OBIS und veröffentlicht sie per **MQTT** – inklusive
**Home Assistant MQTT Discovery**.

Zusätzlich werden die Wechselrichter (Sunny Tripower PV-Wechselrichter, Sunny
Island Batterie-Wechselrichter) **aktiv abgefragt**: Sie senden ihre Leistung
nicht per Broadcast, sondern werden über das SMA-Speedwire-**Data2+**-Protokoll
direkt per IP angefragt (Login + Register-Abfrage, wie SBFspot).

## Funktionsweise

**Grid-Zähler (passiv):**

- Lauscht auf der Speedwire-Multicast-Gruppe `239.12.255.254:9522`.
- Filtert auf SMA-Energy-Meter-Telegramme (Protokoll `0x6069`).
- Dekodiert die OBIS-Kanäle und berechnet die **Netto-Wirkleistung**
  (`P+ − P−`): positiv = Netzbezug, negativ = Einspeisung.
- Der Grid-Zähler wird automatisch über seine SUSY-ID erkannt
  (270 = SMA Energy Meter, 372 = Sunny Home Manager 2.0).

**Wechselrichter (aktiv gepollt):**

- Verbindet sich per Unicast UDP `9522` mit der Speedwire-IP des Geräts.
- Meldet sich mit dem Geräte-Passwort an (Speedwire Data2+ Login) und fragt
  alle `POLL_INTERVAL` Sekunden die Spot-Werte ab: AC-Leistung (`0x00263F00`)
  und – beim Sunny Island – den Ladezustand (`0x00295A00`).
- Veröffentlicht die Werte per MQTT (eigener Thread parallel zum Listener).

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
| `PV_SERIAL`      | nein    | Seriennummer des Sunny Tripower (nur zur Plausibilitätsprüfung)     |
| `BATTERY_SERIAL` | nein    | Seriennummer des Sunny Island (nur zur Plausibilitätsprüfung)       |
| `PV_IP`          | nein    | Speedwire-IP des Sunny Tripower – leer = PV-Polling aus             |
| `BATTERY_IP`     | nein    | Speedwire-IP des Sunny Island – leer = Batterie-Polling aus         |
| `INVERTER_PASSWORD` | nein | Login-Passwort der Wechselrichter (SMA-Standard `0000`)            |
| `INVERTER_USER_GROUP` | nein | Login-Benutzergruppe: `user` oder `installer`                    |
| `POLL_INTERVAL`  | nein    | Abfrageintervall der Wechselrichter in Sekunden (Standard `10`)     |

> Die `.env` ist über `.gitignore` ausgeschlossen und wird bei `git pull` nicht
> überschrieben.

### Wechselrichter abfragen (PV & Batterie)

Der Grid-Zähler funktioniert ohne weitere Konfiguration. PV und Batterie werden
**aktiv per IP gepollt** und erst veröffentlicht, wenn ihre `*_IP` gesetzt ist:

1. Die Speedwire-IP der Geräte im Router bzw. in der SMA-App ermitteln und als
   `PV_IP` / `BATTERY_IP` eintragen.
2. Das Login-Passwort setzen (`INVERTER_PASSWORD`, Standard `0000` für die
   Benutzergruppe `user`).
3. Verbindung vorab testen (ohne MQTT/Container):
   ```bash
   python app/speedwire_data2.py 192.168.0.172 0000 user
   ```
   Das gibt SusyID/Serial, AC-Leistung und – beim Island – den SoC aus. Mit
   `debug=True` (im CLI-Modus aktiv) werden die rohen Sende-/Empfangs-Bytes
   geloggt, falls etwas nicht passt.

> Hinweis: `PV_SERIAL` / `BATTERY_SERIAL` sind fürs Polling nicht nötig (das
> läuft über die IP). Sind sie gesetzt, warnt der Poller, wenn die per Login
> ermittelte Seriennummer nicht passt – nützlich, um eine falsche IP zu
> erkennen.

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
| `sma-sniffer/energy/grid/power_w`          | Netzleistung in W (+ Bezug / − Einspeisung)   |
| `sma-sniffer/energy/grid/energy_import_kwh` | Netzbezug-Zähler in kWh (für Energie-Dashboard) |
| `sma-sniffer/energy/grid/energy_export_kwh` | Einspeisung-Zähler in kWh                      |
| `sma-sniffer/energy/pv/power_w`           | PV-Leistung in W (sofern `PV_IP` gesetzt)     |
| `sma-sniffer/energy/pv/energy_total_kwh`  | PV-Gesamtertrag in kWh (für Energie-Dashboard) |
| `sma-sniffer/energy/pv/energy_today_kwh`  | PV-Tagesertrag in kWh                          |
| `sma-sniffer/energy/battery/power_w`      | Batterieleistung in W (sofern `BATTERY_IP`)   |
| `sma-sniffer/energy/battery/soc_pct`      | Batterie-Ladezustand in % (Sunny Island)      |
| `sma-sniffer/energy/battery/energy_in_kwh`  | In den Speicher geladene Energie in kWh     |
| `sma-sniffer/energy/battery/energy_out_kwh` | Aus dem Speicher entladene Energie in kWh   |

Die `*_kwh`-Topics sind kumulative Zähler (`device_class: energy`,
`state_class: total_increasing`) und damit direkt im **Home Assistant
Energie-Dashboard** verwendbar (Solarproduktion bzw. Batteriespeicher).

### Home Assistant

Ist `HA_DISCOVERY` aktiv (Standard), werden die Sensoren automatisch per MQTT
Discovery unter dem Gerät **„SMA Sniffer Energy System"** angelegt. Es ist keine
manuelle `configuration.yaml` nötig.

## Projektstruktur

```
app/
├── main.py              # Einstiegspunkt: Multicast-Loop (Zähler) + Poller-Thread (Wechselrichter)
├── config.py            # Konfiguration aus der .env
├── speedwire.py         # OBIS-Parser + Telegram-Klasse (Energy-Meter-Protokoll 0x6069)
├── speedwire_data2.py   # Data2+-Client: Login + Register-Abfrage der Wechselrichter (0x6065)
├── mqtt_publisher.py    # MQTT-Publish + Home-Assistant-Discovery
└── devices/
    ├── base.py          # SmaDevice (Multicast) + PolledInverter (Data2+) + Sensor-Helfer
    ├── energy_meter.py  # EnergyMeter   → grid    (Auto-Erkennung via SUSY-ID)
    ├── sunny_tripower.py# SunnyTripower → pv      (gepollt via PV_IP)
    └── sunny_island.py  # SunnyIsland   → battery (gepollt via BATTERY_IP)
```

- Ein neues **Multicast-Gerät** ergänzt man über eine Datei in `devices/`
  (Subklasse von `SmaDevice`) und `build_devices()` in `main.py`.
- Einen neuen **gepollten Wechselrichter** über eine Subklasse von
  `PolledInverter` (mit `read(client)`) und `build_inverters()` in `main.py`.

## Lokale Entwicklung

```bash
pip install -r app/requirements.txt
python app/main.py
```

Es wird eine `.env` im Arbeitsverzeichnis benötigt.
