# SMA Sniffer

Liest den SMA Energy Meter / Sunny Home Manager sowie die Wechselrichter
Sunny Tripower und Sunny Island aus und stellt alle Werte per MQTT bereit. Die
Sensoren erscheinen automatisch unter dem Gerät **SMA Sniffer Energy System**.

## Einrichtung

1. Die **Mosquitto**-App und die **MQTT**-Integration in Home Assistant
   einrichten. Die Zugangsdaten holt sich der SMA Sniffer dann selbst.
   Einen externen Broker trägst du stattdessen unter `mqtt_host` ein.
2. Die App starten und im **Log** nachsehen. Solange eine Wechselrichter-IP fehlt,
   sucht die App beim Start nach SMA-Geräten und listet sie auf:

   ```text
   Found 3 SMA device(s):
     192.168.178.37  PV inverter  serial=305075972  -> pv_ip / PV_IP
     192.168.178.79  battery inverter  serial=1261042460  -> battery_ip / BATTERY_IP
     192.168.178.82  energy meter  serial=1900255994  (no IP setting needed)
   ```

3. Die IPs unter **Konfiguration** eintragen (`pv_ip`, `battery_ip`) und die App
   neu starten. Der Grid-Zähler funktioniert ohne Konfiguration. Nach etwa
   10 Sekunden sind die Sensoren verfügbar.

Reserviere die IPs am besten im Router, damit sie sich nicht ändern.

Für die Typ-Erkennung meldet sich die App einmal mit dem konfigurierten Passwort an
den Wechselrichtern an. Wird das abgelehnt, steht dort `type unknown`. Dann das
richtige `inverter_password` setzen und die App neu starten.

> **Wichtig:** Die im Sunny Portal unter „Geräteeigenschaften“ angezeigte
> `192.168.0.x`-Adresse ist meist die interne WLAN-Adresse der Geräte und im LAN
> nicht erreichbar. Nimm die IP aus dem Log.

## Optionen

| Option                | Standard | Beschreibung                                                    |
| --------------------- | -------- | --------------------------------------------------------------- |
| `pv_ip`               | –        | LAN-IP des Sunny Tripower. Leer = keine PV-Abfrage              |
| `battery_ip`          | –        | LAN-IP des Sunny Island. Leer = keine Batterie-Abfrage          |
| `inverter_password`   | `0000`   | Login-Passwort der Wechselrichter                               |
| `inverter_user_group` | `user`   | Benutzergruppe: `user` oder `installer`                         |
| `poll_interval`       | `10`     | Abfrageintervall der Wechselrichter in Sekunden                 |
| `mqtt_host`           | –        | Externer Broker. Leer = Mosquitto-App                           |
| `mqtt_port`           | `1883`   | Port des externen Brokers                                       |
| `mqtt_user`           | –        | Benutzer des externen Brokers                                   |
| `mqtt_pass`           | –        | Passwort des externen Brokers                                   |
| `meter_serial`        | –        | Nur nötig, wenn mehrere Zähler im Netz sind                     |
| `pv_serial`           | –        | Warnt im Log, wenn unter `pv_ip` ein anderes Gerät antwortet    |
| `battery_serial`      | –        | Warnt im Log, wenn unter `battery_ip` ein anderes Gerät antwortet |
| `log_values`          | `false`  | Jeden Messwert loggen (mehrere Zeilen pro Sekunde)              |
| `debug_obis`          | `false`  | Alle OBIS-Kanäle und Data2+-Rohbytes loggen                     |

Änderungen werden erst nach einem Neustart der App wirksam.

## Fehlersuche

- **Keine Grid-Werte:** Für einen Test `log_values` einschalten. Erscheinen keine
  `[GRID]`-Zeilen, kommen die Multicast-Pakete nicht an, etwa weil der Host in
  einem anderen Netz oder VLAN als der Zähler hängt.
- **`No SMA devices answered`:** Der Host erreicht die Geräte nicht per Multicast,
  etwa weil er in einem anderen Netz oder VLAN hängt.
- **`[PV] poll failed` oder `[BATTERY] poll failed`:** IP und Passwort prüfen. Hat
  sich die IP geändert, die Option leeren und die App neu starten, dann steht die
  neue IP im Log.
- **`MQTT connection refused by broker`:** Zugangsdaten des Brokers prüfen.
- **`No MQTT broker available`:** Mosquitto-App installieren oder `mqtt_host`
  setzen.
- **Sensoren doppelt oder Werte springen:** Läuft der SMA Sniffer zusätzlich als
  Docker-Container, diesen stoppen (`make down`).

Mehr dazu in der [Dokumentation](https://github.com/rvalley98/sma-sniffer/blob/main/docs/README.md).

## Unterstützen

Wenn dir der SMA Sniffer hilft, freue ich mich über einen Kaffee:

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-unterst%C3%BCtzen-FFDD00?logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/rvalley98)
