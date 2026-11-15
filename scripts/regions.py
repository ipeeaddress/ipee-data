#!/usr/bin/env python3
"""List the Geofabrik extracts to build (US states + territories, Canadian provinces).

Prints one line per region: <id> <pbf_url>  and writes regions.json with their bounding boxes.
"""
import json, sys, urllib.request

PARENTS = {'us', 'canada'}  # add e.g. 'europe' countries here later

with urllib.request.urlopen('https://download.geofabrik.de/index-v1.json') as r:
    index = json.load(r)

def bbox(geom):
    xs, ys = [], []
    def walk(c):
        if isinstance(c[0], (int, float)):
            xs.append(c[0]); ys.append(c[1])
        else:
            for x in c:
                walk(x)
    walk(geom['coordinates'])
    return [round(min(xs), 3), round(min(ys), 3), round(max(xs), 3), round(max(ys), 3)]

boxes = []
for f in index['features']:
    p = f['properties']
    if p.get('parent') in PARENTS and 'pbf' in p.get('urls', {}):
        # Skip "parent" regions that are split further (e.g. California -> norcal/socal),
        # we take their children instead.
        if any(g['properties'].get('parent') == p['id'] for g in index['features']):
            continue
        print(p['id'], p['urls']['pbf'])
        boxes.append(bbox(f['geometry']))

with open(sys.argv[1] if len(sys.argv) > 1 else 'regions.json', 'w') as out:
    json.dump(boxes, out)
