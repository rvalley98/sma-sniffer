# Protokolle

Zwei SMA-Speedwire-Protokolle sind im Einsatz. Beide laufen über UDP-Port
`9522`.

---

## 1. Energy Meter (`0x6069`, Multicast)

Der SMA Energy Meter / Sunny Home Manager sendet jede Sekunde ein Telegramm an
die Multicast-Gruppe `239.12.255.254:9522`. Geparst von `app/speedwire.py`.

### Aufbau (relevante Offsets)

| Offset | Größe | Feld                                  |
| ------ | ----- | ------------------------------------- |
| 0      | 4     | `"SMA\0"`                             |
| 16     | 2     | Protokoll-ID (`0x6069`), big-endian   |
| 18     | 2     | SUSY-ID, big-endian                   |
| 20     | 4     | Seriennummer, big-endian              |
| 28…    | –     | OBIS-Kanäle (siehe unten)             |

### OBIS-Kanäle

Ab Offset 28 folgen Kanäle. Jeder beginnt mit einem 4-Byte-Identifier; das
zweite Byte kodiert den Messwerttyp: `0x04` = Momentanwert (4 Byte), `0x08` =
Zähler (8 Byte). Alle Werte big-endian.

| Identifier   | Bedeutung                      | Rohwert → Einheit       |
| ------------ | ------------------------------ | ----------------------- |
| `0x00010400` | P+ Wirkleistung Bezug          | `/10` → W               |
| `0x00020400` | P− Wirkleistung Einspeisung    | `/10` → W               |
| `0x00010800` | Zähler Bezug (1.8.0)           | `/3 600 000` → kWh (Ws) |
| `0x00020800` | Zähler Einspeisung (2.8.0)     | `/3 600 000` → kWh (Ws) |

Die **Netto-Wirkleistung** ist `(P+ − P−)/10`: positiv = Netzbezug, negativ =
Einspeisung. Energiezähler sind in **Wattsekunden** kodiert (`1 kWh =
3 600 000 Ws`).

> Weitere Kanäle (Blindleistung, Scheinleistung, pro Phase) werden vom Parser
> ebenfalls dekodiert und mit `DEBUG_OBIS=1` ausgegeben, aber nicht
> veröffentlicht.

---

## 2. Wechselrichter (Data2+ / `0x6065`, Unicast)

Aktive Abfrage per Unicast an die IP des Wechselrichters. Implementiert in
`app/speedwire_data2.py`. Nachgebaut anhand von SBFspot und dem FHEM-Modul
`76_SMAInverter`, gegen echte Geräte verifiziert.

**Wichtig:** Die beiden Längenfelder im äußeren Header sind **big-endian**,
**alles im inneren Frame ist little-endian**.

### Paketaufbau

```
Offset
0    "SMA\0"                              ┐ äußerer Header
4    00 04 02 A0   tag0 (len 4 / id 02A0) │
8    00 00 00 01   group = 1              │
12   <datalength>  (2 Byte, BIG-endian)   │ = Länge des Frames ab Offset 20
14   00 10         SMA-Net-2-Tag          │
16   60 65         Protokoll 0x6065       │
18   <longwords> <ctrl=0xA0>              ┘
20   dst SusyID(2) + dst Serial(4)        ┐ innerer Frame (little-endian)
26   ctrl2 (2)                            │
28   src SusyID(2) + src Serial(4)        │
34   ctrl2 (2)                            │
36   status(2) + fragment(2)              │
40   packet id(2)  (| 0x8000)             │
42   command(4) + first(4) + last(4) …    ┘
```

- `datalength` (Offset 12, big-endian) = Anzahl Bytes ab Offset 20 =
  `Gesamtlänge − 20`. Login `0x3A`, Query `0x26`, Logoff `0x22`.
- `longwords` (Offset 18): Login `0x0E`, Query `0x09`, Logoff `0x08`. `ctrl` = `0xA0`.
- `ctrl2` (Offset 26 + 34): Login `0x0100`, Query `0x0000`, Logoff `0x0300`
  (Wert little-endian, d. h. auf dem Draht `00 01` / `00 00` / `00 03`).
- Quelle (Client): SusyID `0x007D` (125), Serial beliebig — der Wechselrichter
  spiegelt sie nur zurück.
- `packet id`: vor jeder Anfrage hochzählen, auf dem Draht mit `| 0x8000`,
  Antwort per `& 0x7FFF` zuordnen.

### Ablauf

1. **Discovery** — `command=0x00000200`, `first=last=0`, an Broadcast
   (`dst=0xFFFF/0xFFFFFFFF`). Die Antwort enthält an Offset 28/30 die echte
   SusyID/Serial des Wechselrichters; sie wird fortan als Ziel verwendet.
2. **Login** — `command=0xFFFD040C`, Benutzergruppe (`0x07` user / `0x0A`
   installer), Timeout `0x00000384` (900 s), Unix-Timestamp, dann 12-Byte-
   Passwort. Passwort-Encoding: je Zeichen `(0x88 + ord) & 0xFF` für `user`
   bzw. `0xBB` für `installer`, auf 12 Byte mit dem Encoding-Byte aufgefüllt.
   Status an Offset 36 (`0x0000` = OK, `0x0100` = falsches Passwort).
3. **Abfrage** — `command`, `first`, `last` als drei Little-Endian-Longs.
4. **Logoff** — `command=0xFFFD010E` + `0xFFFFFFFF`.

### Antwort-Parsing

Datensätze beginnen bei **Offset 54**: 4 Byte LRI-Code, 4 Byte Timestamp, dann
der Wert ab **Offset 62** (`record + 8`).

- **Momentanwerte** (Leistung, SoC): 32-bit, Record-Schrittweite **28 Byte**.
- **Zähler** (Energie): 64-bit, Record-Schrittweite **16 Byte**.
- „Nicht verfügbar"-Marker → `None`: 32-bit `0x80000000`/`0xFFFFFFFF`,
  64-bit `0x8000000000000000`/`0xFFFFFFFFFFFFFFFF`.
- Fragt man ein Register ab, das ein Gerät nicht hat, kommt eine leere
  Echo-Antwort (datalength bleibt `0x26`) → `None`.

### Verwendete Register

| Wert                     | command      | first        | last         | Skalierung    |
| ------------------------ | ------------ | ------------ | ------------ | ------------- |
| AC-Leistung (Pac)        | `0x51000200` | `0x00263F00` | `0x00263FFF` | signed, W     |
| Batterie-SoC             | `0x51000200` | `0x00295A00` | `0x00295AFF` | unsigned, %   |
| Ertrag gesamt/heute      | `0x54000200` | `0x00260100` | `0x002622FF` | `/1000` → kWh |
| Batterie laden/entladen  | `0x54000200` | `0x00496700` | `0x004968FF` | `/1000` → kWh |

Innerhalb der Energie-Antworten per LRI unterschieden:

- `0x00260100` = Gesamtertrag, `0x00262200` = Tagesertrag (Wh).
- `0x00496700` = geladene Energie, `0x00496800` = entladene Energie (Wh).
  Plausibilität: geladen ≥ entladen (Round-Trip-Verluste).

> Weitere bekannte Register (Batterietemperatur, Strang-Spannungen,
> Netzfrequenz …) lassen sich per Dump-Modus erkunden, siehe
> [cli-tools.md](cli-tools.md).
