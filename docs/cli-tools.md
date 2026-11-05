# CLI-Werkzeuge

Beide Tools sind reine Python-Skripte ohne externe Abhängigkeiten und lassen
sich direkt auf dem Host ausführen — unabhängig vom Container.

---

## `discover_speedwire.py` — Geräte finden

Sendet die SMA-Multicast-Discovery und listet alle antwortenden Geräte mit ihrer
**echten LAN-IP** und ihrem Typ auf (die IP stammt aus der Absenderadresse der
Antwort).

```bash
python3 app/discover_speedwire.py [passwort] [user|installer]
# oder: make discover [PW=0000] [GROUP=user]
```

Beispielausgabe:

```
Searching for SMA devices on the network ...
Found 3 SMA device(s):
  192.168.178.37  PV inverter  serial=305075972  -> pv_ip / PV_IP
  192.168.178.79  battery inverter  serial=1261042460  -> battery_ip / BATTERY_IP
  192.168.178.82  energy meter  serial=1900255994  (no IP setting needed)
```

Der Energy Meter liefert seine Seriennummer direkt mit. An den Wechselrichtern
meldet sich das Tool einmal an und liest den SoC: Liefert ein Gerät einen Wert, gilt
es als Batterie-Wechselrichter, sonst als PV-Wechselrichter. Schlägt die Anmeldung
fehl, erscheint `type unknown` mit dem Grund.

Dieselbe Suche läuft beim Start des Sniffers automatisch, solange `PV_IP` oder
`BATTERY_IP` fehlt, also auch in der Home Assistant App. Das Ergebnis steht dann im
Log, die Konfiguration bleibt unverändert.

Findet das Tool nur den Zähler, aber keine Wechselrichter, hängen diese nicht im
selben Netzsegment wie der Host — siehe [troubleshooting.md](troubleshooting.md).

---

## `speedwire_data2.py` — Wechselrichter abfragen

### Testmodus

```bash
python3 app/speedwire_data2.py <ip> [passwort] [user|installer]
# z. B.:  make test-inverter IP=192.168.178.79
```

Führt Discovery + Login durch und gibt SusyID/Serial, AC-Leistung und (beim
Sunny Island) den SoC aus. Die rohen Sende-/Empfangs-Bytes werden mitgeloggt
(`[DATA2] -> / <-`).

```
Connected: SusyID=332 serial=1261042460
AC power : -20 W
Battery SoC: 100 %
```

### Dump-Modus

Fragt einen beliebigen Registerbereich ab und zeigt die enthaltenen Datensätze
(LRI, 32-bit- und 64-bit-Wert) — nützlich, um neue Werte zu identifizieren.

```bash
# Benannte Presets:
python3 app/speedwire_data2.py <ip> <pw> <group> dump energy    # Ertragszähler
python3 app/speedwire_data2.py <ip> <pw> <group> dump batload   # Batterie-Lade-Zähler
python3 app/speedwire_data2.py <ip> <pw> <group> dump batdiag   # Batterie V/A/Temp/Durchsatz

# Beliebiger Bereich (command first last, hex):
python3 app/speedwire_data2.py <ip> <pw> <group> dump 0x54000200 0x00496000 0x00497fff
```

Beispielausgabe:

```
--- records for ['0x54000200', '0x496700', '0x4968ff'] ---
  lri=0x00496700 cls=0x07 val32=13331500 val64=13331500
  lri=0x00496800 cls=0x07 val32=10128800 val64=10128800
```

So lassen sich weitere Register erschließen (Skalierung siehe
[protocol.md](protocol.md), Einbau siehe [development.md](development.md)).
