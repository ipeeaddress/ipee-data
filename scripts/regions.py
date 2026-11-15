#!/usr/bin/env python3
"""List the Geofabrik extracts to build (US states + territories, Canadian provinces).

Prints one line per region: <id> <pbf_url>  and writes regions.json with their bounding boxes.
Diagnostics go to stderr so they show up in the GitHub Actions log.
"""
import json, sys
from collections import Counter

# A region is included if its ISO 3166-2 code starts with one of these,
# or if its parent is one of PARENTS. (Belt and braces: Geofabrik's ids changed over time.)
ISO_PREFIXES = ('US-', 'CA-')
PARENTS = {'us', 'canada', 'north-america/us', 'north-america/canada'}

with open('index-v1.json') as f:
    index = json.load(f)
feats = index['features']
parents_with_children = {f['properties'].get('parent') for f in feats}

def iso2(p):
    v = p.get('iso3166-2') or []
    return v if isinstance(v, list) else [v]

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

picked, boxes = [], []
for f in feats:
    p = f['properties']
    if 'pbf' not in p.get('urls', {}):
        continue
    hit = p.get('parent') in PARENTS or any(c.startswith(ISO_PREFIXES) for c in iso2(p))
    if not hit:
        continue
    if p['id'] in parents_with_children:
        continue  # split further (e.g. California -> norcal/socal): take the children
    picked.append(p)
    print(p['id'], p['urls']['pbf'])
    boxes.append(bbox(f['geometry']))

# Diagnostics
print(f'picked {len(picked)} regions', file=sys.stderr)
print('parents:', Counter(p.get('parent') for p in picked), file=sys.stderr)
us_like = [f['properties']['id'] for f in feats if 'alabama' in f['properties']['id'] or 'columbia' in f['properties']['id'] or f['properties']['id'] in ('us', 'canada')]
for fid in us_like:
    pp = next(f['properties'] for f in feats if f['properties']['id'] == fid)
    print('  sample:', fid, 'parent=', pp.get('parent'), 'iso2=', pp.get('iso3166-2'), file=sys.stderr)
if len(picked) < 50:
    sys.exit(f'Only {len(picked)} regions found - expected 60+ (50 US states + DC + territories + 13 Canadian). Stopping.')

with open(sys.argv[1] if len(sys.argv) > 1 else 'regions.json', 'w') as out:
    json.dump(boxes, out)
