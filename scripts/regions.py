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

by_id = {f['properties']['id']: f for f in feats}
children = {}
for f in feats:
    children.setdefault(f['properties'].get('parent'), []).append(f['properties']['id'])

def leaves(fid):
    """A region that is split further (California -> norcal/socal) is replaced by its pieces."""
    kids = [k for k in children.get(fid, []) if 'pbf' in by_id[k]['properties'].get('urls', {})]
    if not kids:
        return [fid]
    out = []
    for k in kids:
        out += leaves(k)
    return out

wanted_ids = []
for f in feats:
    p = f['properties']
    if 'pbf' not in p.get('urls', {}):
        continue
    # Skip Geofabrik's multi-state bundles (us-midwest, us-south, ...): the states inside them are already picked.
    if p['id'].startswith('us-') or p['id'] in ('us', 'canada', 'north-america'):
        continue
    if p.get('parent') in PARENTS or any(c.startswith(ISO_PREFIXES) for c in iso2(p)):
        wanted_ids.append(p['id'])

picked, boxes, seen = [], [], set()
for fid in wanted_ids:
    for leaf in leaves(fid):
        if leaf in seen:
            continue
        seen.add(leaf)
        p = by_id[leaf]['properties']
        picked.append(p)
        print(p['id'], p['urls']['pbf'])
        boxes.append(bbox(by_id[leaf]['geometry']))

# Diagnostics
print(f'picked {len(picked)} regions', file=sys.stderr)
print('parents:', Counter(p.get('parent') for p in picked), file=sys.stderr)
us_like = [f['properties']['id'] for f in feats if any(w in f['properties']['id'] for w in ('california', 'columbia', 'nunavut', 'norcal', 'socal'))]
for fid in us_like:
    pp = next(f['properties'] for f in feats if f['properties']['id'] == fid)
    print('  sample:', fid, 'parent=', pp.get('parent'), 'iso2=', pp.get('iso3166-2'), file=sys.stderr)
if len(picked) < 60 or not any('cal' in p['id'] for p in picked):
    sys.exit(f'Region list looks wrong ({len(picked)} regions, California present: {any("cal" in p["id"] for p in picked)}). Stopping.')

with open(sys.argv[1] if len(sys.argv) > 1 else 'regions.json', 'w') as out:
    json.dump(boxes, out)
