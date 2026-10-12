"""Exporte les tables de rapport dbt en un seul fichier JSON lu par le dashboard."""
from __future__ import annotations

import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "warehouse.duckdb"
OUT = ROOT / "site" / "data" / "dashboard.json"

TABLES = {
    "kpis": "select * from rpt_kpis",
    "daily": "select * from rpt_daily",
    "hour_weekday": "select * from rpt_hour_weekday",
    "category": "select * from rpt_category",
    "stations": "select * from rpt_station order by n_measured desc",
    "lines": "select * from rpt_line order by n_measured desc limit 60",
    "delay_distribution": "select * from rpt_delay_distribution",
    "propagation": "select * from rpt_propagation",
}


def clean(v):
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, float):
        return None if math.isnan(v) else round(v, 4)
    return v


def main() -> None:
    con = duckdb.connect(str(DB), read_only=True)
    out = {}
    for key, sql in TABLES.items():
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description]
        out[key] = [{c: clean(v) for c, v in zip(cols, row)} for row in cur.fetchall()]
    out["kpis"] = out["kpis"][0]
    out["meta"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "source": "sample" if (ROOT / "data" / "raw" / "SAMPLE").exists() else "opentransportdata.swiss",
        "punctual_threshold_s": 180,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{OUT.relative_to(ROOT)} : {OUT.stat().st_size / 1024:.0f} Ko")


if __name__ == "__main__":
    main()
