#!/usr/bin/env python3
"""Clip USGS 3DEP lidar points from an Entwine Point Tile (EPT) dataset for a lon/lat bbox.

Pure-Python EPT walker (no PDAL): reads ept.json, walks ept-hierarchy, downloads only
the ept-data/*.laz nodes intersecting the bbox, filters points, writes a merged LAZ.
Usage: ept_clip.py <ept_base_url> <min_lon> <min_lat> <max_lon> <max_lat> <out.laz> [max_depth]
"""
import sys, json, io, os, math, urllib.request, concurrent.futures as cf
import numpy as np, laspy
from pyproj import Transformer

def fetch(url, retries=4):
    for i in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                return r.read()
        except Exception as e:
            if i == retries - 1:
                raise
    return None

def main():
    base, min_lon, min_lat, max_lon, max_lat, out = sys.argv[1:7]
    max_depth = int(sys.argv[7]) if len(sys.argv) > 7 else 99
    min_lon, min_lat, max_lon, max_lat = map(float, (min_lon, min_lat, max_lon, max_lat))
    ept = json.loads(fetch(base + "/ept.json"))
    b = ept["bounds"]; srs = ept["srs"]
    epsg = f"EPSG:{srs['horizontal']}"
    t = Transformer.from_crs("EPSG:4326", epsg, always_xy=True)
    xs, ys = zip(*[t.transform(lon, lat) for lon, lat in
                   ((min_lon, min_lat), (max_lon, min_lat), (max_lon, max_lat), (min_lon, max_lat))])
    qx0, qx1, qy0, qy1 = min(xs), max(xs), min(ys), max(ys)
    print(f"EPT srs {epsg}; query bbox {qx0:.1f},{qy0:.1f} - {qx1:.1f},{qy1:.1f}")
    root_size = b[3] - b[0]  # cube

    def node_bounds(d, x, y, z):
        s = root_size / (2 ** d)
        return (b[0] + x * s, b[0] + (x + 1) * s, b[1] + y * s, b[1] + (y + 1) * s)

    def intersects(nb):
        return not (nb[1] < qx0 or nb[0] > qx1 or nb[3] < qy0 or nb[2] > qy1)

    # walk hierarchy: keys "d-x-y-z" -> point count (>0) or -1 meaning sub-hierarchy file
    todo = ["0-0-0-0"]; nodes = []; seen_hier = set()
    hier = json.loads(fetch(base + "/ept-hierarchy/0-0-0-0.json"))
    while todo:
        key = todo.pop()
        d, x, y, z = map(int, key.split("-"))
        if not intersects(node_bounds(d, x, y, z)):
            continue
        cnt = hier.get(key)
        if cnt is None:
            continue
        if cnt == -1:
            if key not in seen_hier:
                seen_hier.add(key)
                hier.update(json.loads(fetch(f"{base}/ept-hierarchy/{key}.json")))
                cnt = hier.get(key, 0)
        if cnt and cnt > 0:
            nodes.append((key, cnt))
        if d < max_depth:
            for dx in (0, 1):
                for dy in (0, 1):
                    for dz in (0, 1):
                        todo.append(f"{d+1}-{2*x+dx}-{2*y+dy}-{2*z+dz}")
    print(f"{len(nodes)} nodes intersect, {sum(c for _, c in nodes):,} candidate points")

    parts = []
    def get(node):
        key, cnt = node
        data = fetch(f"{base}/ept-data/{key}.laz")
        las = laspy.read(io.BytesIO(data))
        X, Y = np.asarray(las.x), np.asarray(las.y)
        m = (X >= qx0) & (X <= qx1) & (Y >= qy0) & (Y <= qy1)
        return las, m
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for las, m in ex.map(get, nodes):
            if m.any():
                parts.append(las[m])
    total = sum(len(p) for p in parts)
    print(f"{total:,} points inside bbox")
    if not parts:
        sys.exit("no points")
    hdr = laspy.LasHeader(point_format=parts[0].header.point_format, version=parts[0].header.version)
    hdr.offsets = parts[0].header.offsets; hdr.scales = parts[0].header.scales
    for vlr in parts[0].header.vlrs:
        hdr.vlrs.append(vlr)
    with laspy.open(out, mode="w", header=hdr) as w:
        for p in parts:
            w.write_points(p.points)
    print("wrote", out, os.path.getsize(out) // 1024, "KB")

if __name__ == "__main__":
    main()
