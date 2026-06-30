# CLI-Werkzeuge

Beide Tools sind reine Python-Skripte ohne externe Abhängigkeiten und lassen
sich direkt auf dem Host ausführen — unabhängig vom Container.

---

## `discover_speedwire.py` — Geräte finden

Sendet die SMA-Multicast-Discovery und listet alle antwortenden Geräte mit ihrer
**echten LAN-IP** auf (aus der Absenderadresse der Antwort).

```bash
python3 app/discover_speedwire.py      # oder: make discover
```

Beispielausgabe:

```
Sending Speedwire discovery to 239.12.255.254:9522 ...

Found 3 SMA device(s):
  192.168.178.37
  192.168.178.79
  192.168.178.82   susy=270 serial=1900255994
```

Der Energy Meter liefert SUSY/Serial direkt mit; Wechselrichter erscheinen ohne
(ihre Identität holt man per `speedwire_data2.py`, siehe unten).

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
