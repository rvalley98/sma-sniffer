# Home Assistant

## MQTT-Topics

Basis-Topic: `sma-sniffer/energy`

| Topic                                       | Einheit | Beschreibung                              |
| ------------------------------------------- | ------- | ----------------------------------------- |
| `sma-sniffer/energy/grid/power_w`           | W       | Netzleistung (+ Bezug / − Einspeisung)    |
| `sma-sniffer/energy/grid/energy_import_kwh` | kWh     | Netzbezug-Zähler                          |
| `sma-sniffer/energy/grid/energy_export_kwh` | kWh     | Einspeisung-Zähler                        |
| `sma-sniffer/energy/pv/power_w`             | W       | PV-Leistung                               |
| `sma-sniffer/energy/pv/energy_total_kwh`    | kWh     | PV-Gesamtertrag                           |
| `sma-sniffer/energy/pv/energy_today_kwh`    | kWh     | PV-Tagesertrag                            |
| `sma-sniffer/energy/battery/power_w`        | W       | Batterieleistung                          |
| `sma-sniffer/energy/battery/soc_pct`        | %       | Batterie-Ladezustand                      |
| `sma-sniffer/energy/battery/energy_in_kwh`  | kWh     | In den Speicher geladene Energie          |
| `sma-sniffer/energy/battery/energy_out_kwh` | kWh     | Aus dem Speicher entladene Energie        |

Alle Werte werden mit `retain=True` veröffentlicht. PV- und Batterie-Topics
erscheinen nur, wenn die jeweilige `*_IP` gesetzt ist.

## MQTT Discovery

Ist `HA_DISCOVERY` aktiv (Standard), legt der Sniffer alle Sensoren automatisch
per MQTT Discovery an (Prefix `homeassistant`), gebündelt unter dem Gerät
**„SMA Sniffer Energy System"**. Eine manuelle `configuration.yaml` ist nicht
nötig.

Sensor-Klassen:

| Topic-Suffix            | `device_class` | `state_class`      |
| ----------------------- | -------------- | ------------------ |
| `*/power_w`             | `power`        | `measurement`      |
| `battery/soc_pct`       | `battery`      | `measurement`      |
| `*/energy_*_kwh`        | `energy`       | `total_increasing` |

## Energie-Dashboard

Das HA-Energie-Dashboard verlangt **kumulative kWh-Zähler** (`energy` /
`total_increasing`) — keine Leistungs- oder Prozentwerte. Genau dafür sind die
`*_kwh`-Topics gedacht.

Einrichtung unter **Einstellungen → Dashboards → Energie**:

| Abschnitt           | Sensor(en)                                    |
| ------------------- | --------------------------------------------- |
| Stromnetz → Bezug   | **Grid Energy Import**                        |
| Stromnetz → Einsp.  | **Grid Energy Export**                        |
| Solarpanele         | **PV Energy Total**                           |
| Batteriespeicher    | **Battery Energy In** + **Battery Energy Out** |

Der **Hausverbrauch** ist ein Rechenwert von Home Assistant und erscheint
automatisch, sobald die Netz-Quelle hinterlegt ist:

```
Hausverbrauch = Netzbezug − Einspeisung + PV − Batterieladung + Batterieentladung
```

> Die kWh-Sensoren tauchen in den Dropdowns erst auf, **nachdem sie einmal einen
> Wert gemeldet haben** (~10 s nach Start). Ggf. kurz warten und die Seite neu
> laden.

### Hinweis zur aktuellen Leistung

Das Energie-Dashboard kennt **nur Energie (kWh)** – für Solar und Batterie gibt
es dort **kein Feld für die Momentanleistung (W)**. Die im Fluss angezeigte
aktuelle Leistung wird intern aus den kWh-Zählern abgeleitet (und ist daher
etwas träge). Möchtest du die **aktuelle PV-Leistung** und **Lade-/Entlade-
leistung** präzise und live sehen, nutze dafür eine eigene Lovelace-Karte mit den
W-Sensoren (siehe unten).

## Live-Leistung anzeigen (Lovelace)

Die Momentanwerte stehen als W-Sensoren bereit (`PV Power`, `Battery Power`,
`Grid Power`, `Battery SoC`). Entity-IDs sind je nach HA-Setup z. B.
`sensor.pv_power`, `sensor.battery_power`, `sensor.grid_power`,
`sensor.battery_soc` (im Zweifel über die Entity-Auswahl in der Karte wählen).

**Vorzeichen** (SMA-Rohkonvention):

| Sensor          | positiv      | negativ        |
| --------------- | ------------ | -------------- |
| `Grid Power`    | Netzbezug    | Einspeisung    |
| `Battery Power` | Entladen     | Laden          |
| `PV Power`      | Erzeugung    | –              |

### Variante A — eingebaute Karte (ohne HACS)

```yaml
type: entities
title: SMA Live
entities:
  - entity: sensor.pv_power
    name: PV-Leistung
  - entity: sensor.battery_power
    name: Batterie (+ entladen / − laden)
  - entity: sensor.battery_soc
    name: Ladezustand
  - entity: sensor.grid_power
    name: Netz (+ Bezug / − Einspeisung)
```

### Variante B — Lade-/Entladeleistung getrennt

`Battery Power` ist ein vorzeichenbehafteter Wert. Wer Laden und Entladen als
zwei getrennte, immer positive Werte möchte, legt zwei Template-Sensoren an
(`configuration.yaml`, danach HA neu starten):

```yaml
template:
  - sensor:
      - name: Batterie Ladeleistung
        unit_of_measurement: W
        device_class: power
        state: "{{ [0, (states('sensor.battery_power') | float(0)) * -1] | max }}"
      - name: Batterie Entladeleistung
        unit_of_measurement: W
        device_class: power
        state: "{{ [0, states('sensor.battery_power') | float(0)] | max }}"
```

### Aktueller Hausverbrauch (Template-Sensor)

Den momentanen Hausverbrauch in Watt gibt es nicht als Roh-Sensor – er folgt aus
der Leistungsbilanz und wird am besten als Template-Sensor berechnet
(`configuration.yaml`, danach HA neu starten):

```yaml
template:
  - sensor:
      - name: Hausverbrauch
        unique_id: sma_house_power
        unit_of_measurement: W
        device_class: power
        state_class: measurement
        availability: >
          {{ states('sensor.pv_power') not in ['unknown','unavailable']
             and states('sensor.grid_power') not in ['unknown','unavailable']
             and states('sensor.battery_power') not in ['unknown','unavailable'] }}
        state: >
          {{ (states('sensor.pv_power')      | float(0)
            + states('sensor.grid_power')    | float(0)
            + states('sensor.battery_power') | float(0)) | round(0) }}
```

Formel: `Verbrauch = PV-Leistung + Netzleistung + Batterieleistung`. Das geht
auf, weil die Vorzeichen passen (Netz + = Bezug, Batterie + = Entladen). Beispiel:
PV 3000 W, Batterie lädt mit 2000 W (−2000), Netz 0 → Verbrauch = 1000 W.

### Variante C — Energiefluss-Diagramm (HACS)

Für eine grafische Fluss-Darstellung (PV → Haus, Batterie laden/entladen, Netz)
eignet sich die HACS-Karte **Power Flow Card Plus**:

```yaml
type: custom:power-flow-card-plus
entities:
  grid:
    entity: sensor.grid_power
  solar:
    entity: sensor.pv_power
  battery:
    entity: sensor.battery_power
    state_of_charge: sensor.battery_soc
```

> Stimmt in der Karte die Lade-/Entladerichtung nicht, lässt sich das Vorzeichen
> pro Eintrag invertieren (Karten-Option `invert_state` bzw. die `battery`-
> Konfiguration der Karte) — passend zur Tabelle oben.
