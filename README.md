# iPee Address – restroom map data

Weekly snapshot of restroom-related places from OpenStreetMap (public restrooms,
businesses that list a restroom, restroom-friendly chains, libraries, department
stores), cut into 0.05° map squares for the iPee Address app.

- `meta.json` – build date, covered regions
- `t/<floor(lat*20)>/<floor(lon*20)>.json` – `[[id, lat, lon, {tags}], ...]`

Rebuilt every Monday by GitHub Actions (`.github/workflows/build.yml`) from
[Geofabrik](https://download.geofabrik.de/) extracts.

Data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the
Open Database License (ODbL).
