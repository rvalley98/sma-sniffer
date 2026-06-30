# Fehlerbehebung

## Wechselrichter: „No reply from inverter"

Die Anfragen erreichen den Wechselrichter nicht.

- **Häufigste Ursache — falsches Subnetz/IP:** Die im Sunny Portal unter
  „Geräteeigenschaften" angezeigte `192.168.0.x`-Adresse ist meist die
  **interne WLAN-AP-Adresse** des Wechselrichters, nicht seine LAN-IP. Die echte
  IP liegt im selben Netz wie Host und Zähler. Mit `make discover` ermitteln.
- **Routing:** Der Host muss eine Route ins Netz des Wechselrichters haben
  (am besten gleiches Subnetz). `ip -4 addr` zeigt die Interfaces des Hosts;
  findet `make discover` die Geräte nicht, fehlt die L2-Verbindung.
- **Test:** `make test-inverter IP=<ip>`. Erscheinen `[DATA2] <-`-Zeilen, ist
  das Gerät erreichbar; kommt nur `[DATA2] ->` und dann der Fehler, ist es ein
  Netzwerkthema.

## Login wird abgewiesen (`status=0x0100`)

Falsches Passwort oder falsche Benutzergruppe. SMA-Standard ist `0000` mit
`INVERTER_USER_GROUP=user`. Bei abweichender Vergabe `INVERTER_PASSWORD`
anpassen; für das Installateurs-Passwort `INVERTER_USER_GROUP=installer`.

## PV-Leistung ist 0 oder unsinnig

Der ausgelesene Wert sitzt normalerweise bei Record-Offset `+8` (Byte 62). Auf
manchen Firmwares liegt er bei `+16`. Mit `DEBUG_OBIS=1` die `[DATA2] <-`-Bytes
prüfen: Steht der erwartete Wert weiter hinten im Record, in
`app/speedwire_data2.py` `_VALUE_OFFSET` von `62` auf `70` ändern.

## Vorzeichen falsch (Batterie/PV)

Die AC-Leistung wird roh übernommen. Stimmt das Vorzeichen für deinen Aufbau
nicht (z. B. Laden/Entladen vertauscht), in `app/devices/sunny_island.py` bzw.
`sunny_tripower.py` den Wert von `client.ac_power_w()` negieren.

## Batterie-SoC ist `None` beim PV-Wechselrichter

Erwartet — ein reiner PV-Wechselrichter hat keinen Akku und liefert für das
SoC-Register eine leere Antwort. Nur der Sunny Island liefert einen SoC.

## Energie-kWh um einen Faktor daneben

Die Zähler werden von Wattsekunden in kWh umgerechnet (`/3 600 000` beim Grid,
`/1000` bei den Wechselrichter-Wh-Zählern). Liegt ein Wert um einen festen
Faktor daneben, die Skalierung in `app/speedwire.py` (`ENERGY_DIVISOR`) bzw.
`app/speedwire_data2.py` (`yield_counters_kwh` / `battery_energy_kwh`) prüfen.
Größenordnung grob gegen das Sunny Portal vergleichen.

## Grid-Werte fehlen / Hausverbrauch bleibt 0

- Erscheinen gar keine `[GRID]`-Zeilen, empfängt der Host die Multicast-Pakete
  nicht — der Container muss im `network_mode: host` laufen (siehe
  `compose.yaml`) und der Host am selben Segment wie der Zähler hängen.
- Bleibt der **Hausverbrauch** im Dashboard 0, fehlt die Netz-Quelle. Im
  Energie-Dashboard „Grid Energy Import/Export" als Stromnetz hinterlegen
  (siehe [home-assistant.md](home-assistant.md)).

## Sensoren erscheinen nicht im Energie-Dashboard

Die kWh-Sensoren werden erst wählbar, **nachdem sie einmal einen Wert gemeldet
haben** (~10 s nach Start). Kurz warten und die Seite neu laden. Prüfen, dass
`device_class: energy` und `state_class: total_increasing` gesetzt sind (das ist
der Standard der `energy_sensor`-Definition).
