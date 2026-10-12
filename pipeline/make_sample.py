"""Génère un petit jeu de données fictif au format Ist-Daten.

Sert aux tests automatiques et au développement hors ligne. Les vraies données
sont téléchargées par pipeline/fetch.py ; le dashboard affiche un bandeau
« données de démonstration » tant qu'il tourne sur cet échantillon.
"""
from __future__ import annotations

import random
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"

# (ligne, catégorie, opérateur, gares desservies, minutes entre gares)
ROUTES = [
    ("IC1", "IC", "SBB", ["Genève-Aéroport", "Genève", "Nyon", "Morges", "Lausanne", "Fribourg/Freiburg", "Bern", "Zürich HB", "St. Gallen"], 14),
    ("IC5", "IC", "SBB", ["Genève", "Lausanne", "Yverdon-les-Bains", "Neuchâtel", "Biel/Bienne", "Solothurn", "Olten", "Zürich HB"], 16),
    ("IR15", "IR", "SBB", ["Genève-Aéroport", "Genève", "Lausanne", "Vevey", "Montreux", "Fribourg/Freiburg", "Bern", "Luzern"], 13),
    ("RE33", "RE", "SBB", ["Annemasse", "Genève", "Coppet", "Nyon", "Gland", "Rolle", "Allaman", "Morges", "Lausanne", "Vevey", "St-Maurice"], 7),
    ("IR90", "IR", "SBB", ["Genève-Aéroport", "Genève", "Lausanne", "Montreux", "Aigle", "Martigny", "Sion", "Sierre", "Visp", "Brig"], 15),
    ("L1", "S", "SBB", ["Coppet", "Genève", "Genève-Champel", "Genève-Eaux-Vives", "Chêne-Bourg", "Annemasse", "Bonneville", "Cluses"], 5),
    ("S1", "S", "SBB", ["Grandson", "Yverdon-les-Bains", "Cossonay", "Renens VD", "Lausanne", "Pully", "Lutry", "Cully", "Vevey"], 5),
    ("IC8", "IC", "SBB", ["Brig", "Visp", "Bern", "Olten", "Zürich HB", "Zürich Flughafen", "Winterthur", "Frauenfeld", "Romanshorn"], 18),
    ("S3", "S", "SBB", ["Bern", "Ostermundigen", "Gümligen", "Worb SBB", "Konolfingen", "Thun"], 6),
    ("IR36", "IR", "SBB", ["Basel SBB", "Liestal", "Olten", "Aarau", "Brugg AG", "Baden", "Zürich HB"], 11),
]


def uic(name: str) -> str:
    return "85" + str(zlib.crc32(name.encode()) % 100000).zfill(5)


def main(days: int = 14) -> None:
    random.seed(42)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    start = date(2026, 9, 28)
    for d in range(days):
        day = start + timedelta(days=d)
        weekday = day.weekday()
        for line, cat, op, stops, gap in ROUTES:
            freq = 30 if cat in ("S", "RE") else 60
            first = 5 * 60 + random.randint(0, 20)
            for k, dep_min in enumerate(range(first, 23 * 60, freq)):
                for direction in (1, -1):
                    seq = stops if direction == 1 else list(reversed(stops))
                    train = f"85:11:{line}{k:03d}{'A' if direction == 1 else 'B'}:{day:%Y%m%d}"
                    hour = dep_min // 60
                    rush = 1.8 if hour in (7, 8, 17, 18) and weekday < 5 else 1.0
                    cancelled_trip = random.random() < 0.004
                    delay = max(-30, random.gauss(20, 40))
                    t0 = datetime(day.year, day.month, day.day) + timedelta(minutes=dep_min)
                    for i, st in enumerate(seq):
                        planned = t0 + timedelta(minutes=i * gap)
                        delay += max(-20, random.gauss(9, 35)) * rush
                        if random.random() < 0.01 * rush:
                            delay += random.randint(180, 900)
                        delay = max(-60, delay)
                        status = "REAL" if random.random() > 0.03 else "PROGNOSE"
                        arr_p = None if i == 0 else planned
                        dep_p = None if i == len(seq) - 1 else planned + timedelta(minutes=1)
                        f = lambda t: t.strftime("%d.%m.%Y %H:%M") if t else ""
                        g = lambda t: (t + timedelta(seconds=delay)).strftime("%d.%m.%Y %H:%M:%S") if t else ""
                        rows.append((
                            day.strftime("%d.%m.%Y"), train, "11", op, "Schweizerische Bundesbahnen SBB", "Zug",
                            line, line, cat, "false", "true" if cancelled_trip else "false", uic(st), st,
                            f(arr_p), g(arr_p), status if arr_p else "", f(dep_p), g(dep_p), status if dep_p else "", "false",
                        ))
    con = duckdb.connect()
    cols = ("BETRIEBSTAG,FAHRT_BEZEICHNER,BETREIBER_ID,BETREIBER_ABK,BETREIBER_NAME,PRODUKT_ID,LINIEN_ID,"
            "LINIEN_TEXT,VERKEHRSMITTEL_TEXT,ZUSATZFAHRT_TF,FAELLT_AUS_TF,BPUIC,HALTESTELLEN_NAME,ANKUNFTSZEIT,"
            "AN_PROGNOSE,AN_PROGNOSE_STATUS,ABFAHRTSZEIT,AB_PROGNOSE,AB_PROGNOSE_STATUS,DURCHFAHRT_TF").split(",")
    con.execute("CREATE TABLE s (" + ", ".join(f"{c} VARCHAR" for c in cols) + ")")
    con.executemany(f"INSERT INTO s VALUES ({','.join('?' * len(cols))})", rows)
    for (d,) in con.execute("SELECT DISTINCT BETRIEBSTAG FROM s").fetchall():
        iso = datetime.strptime(d, "%d.%m.%Y").date().isoformat()
        con.execute(f"COPY (SELECT * FROM s WHERE BETRIEBSTAG = '{d}') TO '{RAW_DIR}/istdaten_{iso}.parquet' (FORMAT parquet)")
    (RAW_DIR / "SAMPLE").write_text("données fictives générées par make_sample.py\n")
    print(f"{len(rows):,} lignes fictives sur {days} jours".replace(",", "'"))


if __name__ == "__main__":
    main()
