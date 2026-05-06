"""Convert us-atlas states-albers-10m.json (TopoJSON) into per-state SVG path-d strings.

Reads bad_faith_rank/data/states-albers-10m.json (Albers-USA projected, 975x610 viewBox)
and writes bad_faith_rank/data/us_state_paths.json — a {postal_code: "M…Z"} dict for the
50 states + DC. Run once whenever the source TopoJSON changes; the viewer build embeds
the result so the runtime stays library-free.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "bad_faith_rank" / "data"
SRC = DATA / "states-albers-10m.json"
OUT = DATA / "us_state_paths.json"

FIPS_TO_POSTAL = {
    "01": "AL", "02": "AK", "04": "AZ", "05": "AR", "06": "CA", "08": "CO",
    "09": "CT", "10": "DE", "11": "DC", "12": "FL", "13": "GA", "15": "HI",
    "16": "ID", "17": "IL", "18": "IN", "19": "IA", "20": "KS", "21": "KY",
    "22": "LA", "23": "ME", "24": "MD", "25": "MA", "26": "MI", "27": "MN",
    "28": "MS", "29": "MO", "30": "MT", "31": "NE", "32": "NV", "33": "NH",
    "34": "NJ", "35": "NM", "36": "NY", "37": "NC", "38": "ND", "39": "OH",
    "40": "OK", "41": "OR", "42": "PA", "44": "RI", "45": "SC", "46": "SD",
    "47": "TN", "48": "TX", "49": "UT", "50": "VT", "51": "VA", "53": "WA",
    "54": "WV", "55": "WI", "56": "WY",
}


def fmt(v: float) -> str:
    """Format a coordinate to ≤1 decimal, dropping trailing zeros."""
    s = f"{v:.1f}"
    if s.endswith(".0"):
        s = s[:-2]
    return s


def decode_arc(arc, scale, translate):
    """Delta-decode a quantized topojson arc into absolute (x, y) projected points."""
    x = y = 0
    pts = []
    for dx, dy in arc:
        x += dx
        y += dy
        pts.append((x * scale[0] + translate[0], y * scale[1] + translate[1]))
    return pts


def ring_to_path(ring, arcs, scale, translate):
    """Stitch a ring's arc references into a single SVG sub-path."""
    out = []
    first_point = None
    for arc_ref in ring:
        if arc_ref >= 0:
            pts = decode_arc(arcs[arc_ref], scale, translate)
        else:
            pts = decode_arc(arcs[~arc_ref], scale, translate)[::-1]
        if first_point is None:
            first_point = pts[0]
            out.append(f"M{fmt(pts[0][0])},{fmt(pts[0][1])}")
            rest = pts[1:]
        else:
            rest = pts[1:]
        for x, y in rest:
            out.append(f"L{fmt(x)},{fmt(y)}")
    out.append("Z")
    return "".join(out)


def geometry_to_path(geom, arcs, scale, translate):
    """Build a single 'd' attribute for a Polygon or MultiPolygon geometry."""
    parts = []
    if geom["type"] == "Polygon":
        polygons = [geom["arcs"]]
    elif geom["type"] == "MultiPolygon":
        polygons = geom["arcs"]
    else:
        raise ValueError(f"unexpected geometry type: {geom['type']}")
    for polygon in polygons:
        for ring in polygon:
            parts.append(ring_to_path(ring, arcs, scale, translate))
    return "".join(parts)


def main():
    topo = json.loads(SRC.read_text())
    transform = topo["transform"]
    scale = transform["scale"]
    translate = transform["translate"]
    arcs = topo["arcs"]
    states = topo["objects"]["states"]["geometries"]

    paths = {}
    for geom in states:
        fips = geom["id"]
        postal = FIPS_TO_POSTAL.get(fips)
        if not postal:
            print(f"skip unknown FIPS {fips} ({geom.get('properties', {}).get('name')})")
            continue
        paths[postal] = geometry_to_path(geom, arcs, scale, translate)

    missing = set(FIPS_TO_POSTAL.values()) - set(paths.keys())
    if missing:
        print(f"WARNING: missing states: {sorted(missing)}")

    OUT.write_text(json.dumps(paths, separators=(",", ":")))
    total_bytes = OUT.stat().st_size
    print(f"wrote {OUT} ({total_bytes:,} bytes, {len(paths)} states)")


if __name__ == "__main__":
    main()
