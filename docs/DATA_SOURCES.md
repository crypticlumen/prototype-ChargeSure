# ChargeSure Data Sources

## 1. OpenChargeMap

Purpose:

Charger-level location and station metadata.

Potential data:

- charger location
- station name
- operator
- address
- connector information
- charging power
- external station ID

Role in ChargeSure:

Primary charger-level data source for the MVP.

---

## 2. OpenStreetMap

Purpose:

Geographic and road-network context.

Role in ChargeSure:

- spatial context
- geographic validation
- routing infrastructure
- OSRM data foundation

---

## 3. Government / Open Government Data

Purpose:

Official infrastructure-level validation and statistics.

Role in ChargeSure:

- infrastructure statistics
- state/national validation
- supporting evidence

Important:

Aggregate government data must not be treated as live charger-level
operational telemetry unless the source explicitly provides it.

---

## 4. Simulated Operational Data

For the hackathon prototype:

- simulated OCPP status events
- synthetic charging sessions
- synthetic failures
- synthetic crowd reports
- synthetic grid-load values

These values must be clearly identified as simulated.

---

## Source Strategy

OpenChargeMap +
OpenStreetMap +
Government Data +
Simulated Operational Data +
Future CPO/UBC Feeds

            ↓

ChargeSure Canonical Data Layer
