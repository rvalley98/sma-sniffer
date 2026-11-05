# Konfiguration

> Als Home Assistant App wird der SMA Sniffer stattdessen im Konfigurations-Tab der
> App eingerichtet, siehe [DOCS.md](../DOCS.md). Die Optionen heißen wie die
> Variablen unten, nur kleingeschrieben.

Im Docker-Betrieb erfolgt die gesamte Konfiguration über eine `.env` im
Projektverzeichnis. Vorlage ist `.env.example`:

```bash
cp .env.example .env     # oder: make env
```

Die `.env` ist über `.gitignore` ausgeschlossen und wird bei `git pull` nicht
überschrieben.

## Variablen

| Variable               | Pflicht | Standard | Beschreibung                                                            |
| ---------------------- | ------- | -------- | ---------------------------------------------------------------------- |
| `MQTT_HOST`            | ja      | –        | Hostname/IP des MQTT-Brokers                                            |
| `MQTT_PORT`            | nein    | `1883`   | Port des MQTT-Brokers                                                   |
| `MQTT_USER`            | nein    | leer     | MQTT-Benutzername; leer = ohne Anmeldung                                |
| `MQTT_PASS`            | nein    | leer     | MQTT-Passwort                                                           |
| `METER_SERIAL`         | nein    | leer     | Seriennummer des Energy Meters; leer = Auto-Erkennung via SUSY-ID      |
| `PV_SERIAL`            | nein    | leer     | Seriennummer Sunny Tripower (nur Plausibilitätsprüfung)                |
| `BATTERY_SERIAL`       | nein    | leer     | Seriennummer Sunny Island (nur Plausibilitätsprüfung)                  |
| `PV_IP`                | nein    | leer     | Speedwire-IP des Sunny Tripower; leer = PV-Polling aus                  |
| `BATTERY_IP`           | nein    | leer     | Speedwire-IP des Sunny Island; leer = Batterie-Polling aus             |
| `INVERTER_PASSWORD`    | nein    | `0000`   | Login-Passwort der Wechselrichter                                      |
| `INVERTER_USER_GROUP`  | nein    | `user`   | Login-Benutzergruppe: `user` oder `installer`                          |
| `POLL_INTERVAL`        | nein    | `10`     | Abfrageintervall der Wechselrichter in Sekunden                        |
| `LOG_VALUES`           | nein    | `1`      | Jeden Messwert loggen; `0` = aus (in der HA-App standardmäßig aus)     |
| `DEBUG_OBIS`           | nein    | leer     | `1` = alle OBIS-Kanäle dumpen **und** Data2+-Rohbytes loggen           |

## Grid-Zähler

Der Energy Meter funktioniert ohne Konfiguration: Er wird automatisch über seine
SUSY-ID erkannt (`270` = SMA Energy Meter, `372` = Sunny Home Manager 2.0).
`METER_SERIAL` ist nur nötig, wenn mehrere Zähler im Netz sind und ein
bestimmter gewählt werden soll.

## Wechselrichter

PV und Batterie werden **aktiv per IP abgefragt** und erst veröffentlicht, wenn
ihre `*_IP` gesetzt ist.

1. Echte LAN-IP der Geräte ermitteln — am einfachsten mit `make discover`
   (siehe [cli-tools.md](cli-tools.md)). **Wichtig:** die im Sunny Portal unter
   „Geräteeigenschaften" angezeigte `192.168.0.x`-Adresse ist meist die interne
   WLAN-AP-Adresse, **nicht** die LAN-IP (siehe [troubleshooting.md](troubleshooting.md)).
2. Login-Passwort setzen (`INVERTER_PASSWORD`, SMA-Standard `0000` für `user`).
3. Verbindung vorab testen: `make test-inverter IP=<ip>`.

`PV_SERIAL` / `BATTERY_SERIAL` sind fürs Polling nicht erforderlich. Sind sie
gesetzt, warnt der Poller, wenn die per Login ermittelte Seriennummer abweicht —
nützlich, um eine falsche IP zu erkennen.

## Debugging

`DEBUG_OBIS=1` aktiviert zwei Dinge:

- Einen einmaligen Dump **aller** dekodierten OBIS-Kanäle pro Gerät (Grid).
- Das Roh-Byte-Logging des Data2+-Clients (`[DATA2] -> / <-`) im Poller.

Nach dem Setzen den Container neu starten (`make restart`).
