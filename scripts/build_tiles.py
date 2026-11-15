#!/usr/bin/env python3
"""
Turn OpenStreetMap extracts (.osm.pbf) into small JSON map squares for the iPee Address app.

Usage:
  build_tiles.py add  <region.osm.pbf> <work_dir>     # run once per downloaded region
  build_tiles.py finish <work_dir> <out_dir> <regions.json>

Each square ("tile") covers 0.05° x 0.05° (about 5 km) and is saved as
  out_dir/t/<lat_index>/<lon_index>.json  ->  [[id, lat, lon, {tags}], ...]
where lat_index = floor(lat * 20), lon_index = floor(lon * 20).
"""
import json, math, os, sys
import osmium

TILE = 20  # tiles per degree (0.05°)

# Must match RESTROOM_FRIENDLY_CHAINS in the app (src/lib/places.ts).
CHAINS = {
    'Starbucks', "McDonald's", 'Burger King', "Wendy's", "Dunkin'", 'Panera Bread', 'Pret A Manger',
    'Shake Shack', 'Chick-fil-A', 'Chipotle', 'Taco Bell', 'Barnes & Noble', 'Target', 'Walmart',
    'Whole Foods Market', "Macy's", 'Nordstrom', 'IKEA', 'The Home Depot', "Lowe's", 'Wegmans',
}
KEEP_TAGS = (
    'name', 'brand', 'amenity', 'shop', 'operator', 'description',
    'access', 'toilets', 'toilets:access', 'wheelchair', 'toilets:wheelchair',
    'fee', 'toilets:fee', 'opening_hours', 'toilets:opening_hours',
    'addr:housenumber', 'addr:street', 'changing_table', 'unisex',
)


def wanted(tags) -> bool:
    a = tags.get('amenity')
    if a == 'toilets' or a == 'library':
        return True
    if a and tags.get('toilets') == 'yes':
        return True
    if tags.get('brand') in CHAINS:
        return True
    if tags.get('shop') in ('department_store', 'mall'):
        return True
    return False


def slim(tags):
    return {k: tags[k] for k in KEEP_TAGS if k in tags}


class Collector(osmium.SimpleHandler):
    def __init__(self, work):
        super().__init__()
        self.work = work
        self.buffers = {}
        self.count = 0

    def emit(self, oid, lat, lon, tags):
        key = (math.floor(lat * TILE), math.floor(lon * TILE))
        self.buffers.setdefault(key, []).append([oid, round(lat, 6), round(lon, 6), slim(tags)])
        self.count += 1
        if self.count % 50000 == 0:
            self.flush()

    def flush(self):
        for (la, lo), rows in self.buffers.items():
            d = os.path.join(self.work, str(la))
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f'{lo}.jsonl'), 'a') as f:
                for r in rows:
                    f.write(json.dumps(r, separators=(',', ':'), ensure_ascii=False) + '\n')
        self.buffers = {}

    def node(self, n):
        if n.tags and wanted(n.tags):
            self.emit(f'n{n.id}', n.location.lat, n.location.lon, n.tags)

    def way(self, w):
        if not (w.tags and wanted(w.tags)):
            return
        pts = [(nd.location.lat, nd.location.lon) for nd in w.nodes if nd.location.valid()]
        if not pts:
            return
        lat = sum(p[0] for p in pts) / len(pts)
        lon = sum(p[1] for p in pts) / len(pts)
        self.emit(f'w{w.id}', lat, lon, w.tags)


def add(pbf, work):
    os.makedirs(work, exist_ok=True)
    h = Collector(work)
    # Node locations are needed to find the middle of buildings (ways).
    h.apply_file(pbf, locations=True, idx='flex_mem')
    h.flush()
    print(f'{os.path.basename(pbf)}: {h.count} places', flush=True)


def finish(work, out, regions_file):
    tiles = places = 0
    for la in os.listdir(work):
        for fn in os.listdir(os.path.join(work, la)):
            lo = fn[:-6]
            seen, rows = set(), []
            with open(os.path.join(work, la, fn)) as f:
                for line in f:
                    r = json.loads(line)
                    if r[0] in seen:  # same place appears in two neighbouring regions
                        continue
                    seen.add(r[0])
                    rows.append(r)
            d = os.path.join(out, 't', la)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, f'{lo}.json'), 'w') as f:
                json.dump(rows, f, separators=(',', ':'), ensure_ascii=False)
            tiles += 1
            places += len(rows)
    with open(regions_file) as f:
        regions = json.load(f)
    import datetime
    meta = {
        'built': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%MZ'),
        'tilesPerDegree': TILE,
        'tiles': tiles,
        'places': places,
        # Bounding boxes [minLon, minLat, maxLon, maxLat] of every region included.
        # Inside these, a missing tile just means "nothing here".
        'coverage': regions,
        'attribution': '© OpenStreetMap contributors, ODbL',
    }
    with open(os.path.join(out, 'meta.json'), 'w') as f:
        json.dump(meta, f, indent=1)
    print(f'wrote {tiles} tiles, {places} places', flush=True)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'add':
        add(sys.argv[2], sys.argv[3])
    elif cmd == 'finish':
        finish(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
