# ChargeSure Data Dictionary

| Field            | Type      | Description                                  |
| ---------------- | --------- | -------------------------------------------- |
| charger_id       | string    | Internal ChargeSure charger identifier       |
| source           | string    | External data source                         |
| source_id        | string    | Original identifier from the external source |
| name             | string    | Charger/station name                         |
| operator         | string    | Charging station operator                    |
| address          | string    | Physical address                             |
| city             | string    | City                                         |
| state            | string    | State or Union Territory                     |
| country          | string    | Country                                      |
| latitude         | float     | WGS84 latitude                               |
| longitude        | float     | WGS84 longitude                              |
| location         | geography | PostGIS geographic point                     |
| power_kw         | float     | Charging power                               |
| status           | enum      | Current normalized charger status            |
| last_verified_at | datetime  | Timestamp of latest trusted verification     |
