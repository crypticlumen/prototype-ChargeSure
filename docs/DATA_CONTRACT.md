# ChargeSure Data Contract

## Purpose

This document defines the canonical data structure used by ChargeSure.

External data sources such as OpenChargeMap, OpenStreetMap and future
CPO feeds must be converted into the ChargeSure canonical schema before
being used by the rest of the application.

This prevents the frontend and backend from becoming dependent on the
schema of any particular external data provider.

---

## Charger

### Required Fields

- charger_id
- source
- source_id
- name
- latitude
- longitude
- location
- status

### Optional Fields

- operator
- address
- city
- state
- country
- power_kw
- last_verified_at

---

## Charger Status

Allowed values:

- available
- occupied
- faulted
- offline
- unknown

---

## Geographic Coordinates

Coordinate System:

WGS84 / EPSG:4326

Latitude:

-90 to +90

Longitude:

-180 to +180

PostGIS representation:

GEOGRAPHY(POINT, 4326)

---

## Source Tracking

Every charger must preserve:

- source
- source_id

Example:

source = "openchargemap"

source_id = "123456"

This allows ChargeSure to combine multiple external data sources later.

---

## Design Rule

External provider schemas must never directly become application schemas.

The pipeline is:

External Source
↓
Raw Data
↓
Cleaning / Normalization
↓
Canonical ChargeSure Schema
↓
PostgreSQL / PostGIS
↓
Backend
↓
Frontend
