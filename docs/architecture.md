# Architektur

`sma-sniffer` liest die Energiedaten einer SMA-Anlage auf zwei Wegen ein und
veröffentlicht sie per MQTT (inkl. Home-Assistant-Discovery).

## Überblick

```
                 ┌──────────────────────────────────────────────┐
   Speedwire     │                 sma-decoder                  │
   239.12.255.254│                                              │
   :9522 (MC) ───┼─▶ main.py (Multicast-Loop)                   │
                 │     └─ speedwire.py  (OBIS 0x6069)            │
                 │         └─ EnergyMeter ─▶ grid/*              │
                 │                                              │
   Wechselrichter│   main.py (Poller-Thread, alle POLL_INTERVAL)│      ┌──────────┐
   192.168.x.y   │     └─ speedwire_data2.py (Data2+ 0x6065)    ├─MQTT▶│  Broker  │
   :9522 (UC) ◀──┼────── SunnyTripower ─▶ pv/*                  │      └────┬─────┘
                 │        SunnyIsland  ─▶ battery/*             │           │
                 └──────────────────────────────────────────────┘           ▼
                                                                      Home Assistant
                                                                      (MQTT Discovery)
```

Es gibt zwei grundlegend verschiedene Datenquellen:

| Quelle            | Protokoll | Transport            | Geräte                          |
| ----------------- | --------- | -------------------- | ------------------------------- |
| **Energy Meter**  | `0x6069`  | Multicast (passiv)   | SMA Energy Meter / Home Manager |
| **Wechselrichter**| `0x6065`  | Unicast (aktiv/Poll) | Sunny Tripower, Sunny Island    |

Der Energy Meter **broadcastet** seine Werte jede Sekunde; die Wechselrichter
tun das **nicht** und müssen aktiv per IP abgefragt werden (Login + Register).

## Komponenten

| Datei                       | Aufgabe                                                           |
| --------------------------- | ---------------------------------------------------------------- |
| `app/main.py`               | Einstiegspunkt: Multicast-Socket-Loop + Poller-Thread + Dispatch |
| `app/config.py`             | Konfiguration aus der `.env` bzw. den App-Optionen               |
| `app/ha_app.py`             | Home Assistant App: Optionen + MQTT-Daten vom Supervisor         |
| `app/speedwire.py`          | Parser für Energy-Meter-Telegramme (OBIS, Protokoll `0x6069`)    |
| `app/speedwire_data2.py`    | Client für das Wechselrichter-Protokoll (Data2+, `0x6065`)       |
| `app/discover_speedwire.py` | Standalone-Scanner: findet alle SMA-Geräte im Netz               |
| `app/mqtt_publisher.py`     | MQTT-Publish + Home-Assistant-Discovery                          |
| `app/devices/base.py`       | Basisklassen `SmaDevice` / `PolledInverter` + Sensor-Helfer      |
| `app/devices/energy_meter.py`| `EnergyMeter` → `grid/*`                                         |
| `app/devices/sunny_tripower.py`| `SunnyTripower` → `pv/*`                                      |
| `app/devices/sunny_island.py`| `SunnyIsland` → `battery/*`                                      |

## Datenfluss

**Grid (passiv):** `main.py` lauscht auf der Multicast-Gruppe, `speedwire.parse()`
dekodiert das Telegramm in ein `Telegram`-Objekt (SUSY-ID, Serial, OBIS-Kanäle).
Das passende Gerät wird per `matches()` gefunden, `handle()` liefert die zu
veröffentlichenden `(topic, wert)`-Tupel.

**Wechselrichter (aktiv):** Ein Daemon-Thread (`poll_inverters`) fragt alle
`POLL_INTERVAL` Sekunden jeden konfigurierten Wechselrichter ab. Pro Abfrage
wird ein `Data2Client` als Kontextmanager geöffnet (Discovery → Login →
Abfragen → Logoff), `device.read(client)` liefert die `(topic, wert)`-Tupel.

Beide Pfade veröffentlichen über denselben `MqttPublisher`. Der MQTT-Client von
`paho` ist threadsicher, daher teilen sich Listener und Poller eine Instanz.

## Erweiterbarkeit

- **Neues Multicast-Gerät:** Unterklasse von `SmaDevice` in `devices/` +
  Zeile in `build_devices()`.
- **Neuer gepollter Wechselrichter:** Unterklasse von `PolledInverter`
  (mit `read(client)`) + Zeile in `build_inverters()`.

Details siehe [development.md](development.md).
