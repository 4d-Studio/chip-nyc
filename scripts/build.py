#!/usr/bin/env python3
"""Build the public Chip NYC plant list from ~/.chip/nyc-census.json.

Only DOHMH identity: name, street, zip, pin. No phone, site, status, menu.
"""
from __future__ import annotations

import gzip
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HOME_CENSUS = Path.home() / ".chip" / "nyc-census.json"
ROOT = Path(__file__).resolve().parent.parent
SOURCE = "https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j"
NOTE = "Hidden plant list. Not a live Chip menu. Not DoorDash."


def digits_zip(raw: object) -> str:
    return "".join(ch for ch in str(raw or "") if ch.isdigit())[:5]


def coord(v: object) -> float | None:
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return n if n == n else None


def slim(p: dict) -> dict | None:
    zipcode = digits_zip(p.get("zip"))
    name = str(p.get("name") or "").strip()
    pid = str(p.get("id") or "").strip()
    if not pid or not name or len(zipcode) != 5:
        return None
    return {
        "id": pid,
        "name": name,
        "street": str(p.get("street") or "").strip(),
        "zip": zipcode,
        "boro": str(p.get("boro") or "").strip(),
        "cuisine": str(p.get("cuisine") or "").strip(),
        "bag": p.get("bag") or "unknown",
        "lat": coord(p.get("lat")),
        "lng": coord(p.get("lng")),
    }


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else HOME_CENSUS
    if not src.is_file():
        print(f"missing {src}. run: chip census --nyc", file=sys.stderr)
        return 1
    raw = json.loads(src.read_text())
    places = [row for p in raw.get("places") or [] if (row := slim(p))]
    places.sort(key=lambda p: (p["zip"], p["name"], p["id"]))

    city = {
        "source": SOURCE,
        "note": NOTE,
        "at": raw.get("at"),
        "n": len(places),
        "places": places,
    }
    payload = json.dumps(city, separators=(",", ":"), ensure_ascii=False)
    (ROOT / "nyc.json").write_text(payload)
    (ROOT / "nyc.json.gz").write_bytes(gzip.compress(payload.encode(), mtime=0))

    by: dict[str, list] = defaultdict(list)
    for p in places:
        by[p["zip"]].append(p)

    zips_dir = ROOT / "zips"
    zips_dir.mkdir(exist_ok=True)
    for old in zips_dir.glob("*.json"):
        old.unlink()

    index = []
    for zipcode, rows in sorted(by.items()):
        lats = [r["lat"] for r in rows if r["lat"] is not None]
        lngs = [r["lng"] for r in rows if r["lng"] is not None]
        boro = Counter(r["boro"] for r in rows if r["boro"]).most_common(1)
        rec = {
            "zip": zipcode,
            "boro": boro[0][0] if boro else "",
            "n": len(rows),
            "bag": dict(Counter(r["bag"] for r in rows)),
            "lat": round(sum(lats) / len(lats), 5) if lats else None,
            "lng": round(sum(lngs) / len(lngs), 5) if lngs else None,
        }
        index.append(rec)
        shard = {
            "source": SOURCE,
            "note": NOTE,
            "zip": zipcode,
            "boro": rec["boro"],
            "n": len(rows),
            "places": rows,
        }
        (zips_dir / f"{zipcode}.json").write_text(
            json.dumps(shard, separators=(",", ":"), ensure_ascii=False),
        )

    (ROOT / "index.json").write_text(
        json.dumps(
            {
                "source": SOURCE,
                "note": NOTE,
                "at": city["at"],
                "n": city["n"],
                "zips": index,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
    )
    print(f"places {len(places)} zips {len(index)}")
    print(f"wrote {ROOT / 'nyc.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
