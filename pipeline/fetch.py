"""Télécharge les fichiers « Ist-Daten » (données réelles du trafic suisse)
depuis opentransportdata.swiss et les convertit en Parquet, trains uniquement.

Chaque fichier quotidien pèse environ 500 Mo et contient tous les arrêts de
tous les transports publics suisses. On ne garde que les trains et les colonnes
utiles, ce qui ramène un jour à quelques Mo.

Usage :
    python pipeline/fetch.py --days 30          # les 30 derniers jours publiés
    python pipeline/fetch.py --url <csv> --date 2026-10-12   # un fichier précis
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import zipfile
import urllib.request
from datetime import date
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
# Le portail a changé d'adresse et d'identifiant au fil du temps : on essaie plusieurs
# combinaisons, y compris le miroir officiel opendata.swiss qui référence les mêmes fichiers.
CKAN_HOSTS = [
    "https://opentransportdata.swiss",
    "https://data.opentransportdata.swiss",
    "https://ckan.opendata.swiss",
]
PACKAGE_IDS = [
    "ist-daten-v2", "istdaten", "ist-daten-actual-data", "ist-daten",
    "0edc74a3-ad4d-486e-8657-f8f3b34a0979",
]

# Colonnes indispensables. Le script s'arrête avec un message clair si l'une manque.
REQUIRED = [
    "BETRIEBSTAG", "FAHRT_BEZEICHNER", "BETREIBER_ABK", "PRODUKT_ID",
    "LINIEN_TEXT", "VERKEHRSMITTEL_TEXT", "FAELLT_AUS_TF", "BPUIC",
    "HALTESTELLEN_NAME", "ANKUNFTSZEIT", "AN_PROGNOSE", "AN_PROGNOSE_STATUS",
    "ABFAHRTSZEIT", "AB_PROGNOSE", "AB_PROGNOSE_STATUS",
]
OPTIONAL = ["ZUSATZFAHRT_TF", "DURCHFAHRT_TF", "BETREIBER_NAME", "LINIEN_ID"]

DATE_IN_NAME = re.compile(r"(\d{4}-\d{2}-\d{2})")


def http_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "cff-ponctualite (github.com/Toumil94)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def _files_from_package(pkg: dict) -> list[tuple[str, str]]:
    files = []
    for res in pkg.get("resources", []):
        url = res.get("url") or res.get("download_url") or ""
        name = f"{res.get('name') or ''} {url}"
        m = DATE_IN_NAME.search(name)
        if m and "ist" in name.lower() and url.lower().split("?")[0].endswith((".csv", ".zip")):
            files.append((m.group(1), url))
    return files


def list_daily_files() -> list[tuple[str, str]]:
    """Renvoie [(date ISO, url du CSV)] trié du plus récent au plus ancien."""
    attempts = []
    for host in CKAN_HOSTS:
        candidates = [f"{host}/api/3/action/package_show?id={pid}" for pid in PACKAGE_IDS]
        candidates.append(f"{host}/api/3/action/package_search?q=istdaten&rows=10")
        for url in candidates:
            try:
                data = http_json(url)
            except Exception as e:  # noqa: BLE001
                attempts.append(f"{url} -> {e}")
                continue
            result = data.get("result") or {}
            packages = result.get("results") if "results" in result else [result]
            files = [f for pkg in packages for f in _files_from_package(pkg)]
            if files:
                print(f"Source : {url} ({len(files)} fichiers quotidiens)")
                return sorted(set(files), reverse=True)
            attempts.append(f"{url} -> aucun fichier quotidien")
    sys.exit("Impossible de lister les fichiers Ist-Daten. Essais : " + " | ".join(attempts))


def download(url: str, day: str) -> Path:
    """Télécharge le fichier en flux (il fait ~500 Mo) et le décompresse s'il est zippé."""
    tmp = RAW_DIR / f"_tmp_{day}"
    req = urllib.request.Request(url, headers={"User-Agent": "cff-ponctualite (github.com/Toumil94)"})
    with urllib.request.urlopen(req, timeout=600) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, length=1 << 20)
    if zipfile.is_zipfile(tmp):
        with zipfile.ZipFile(tmp) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
            csv = RAW_DIR / f"_tmp_{day}.csv"
            with z.open(name) as src, open(csv, "wb") as dst:
                shutil.copyfileobj(src, dst, length=1 << 20)
        tmp.unlink()
        return csv
    csv = tmp.with_suffix(".csv")
    tmp.rename(csv)
    return csv


def convert(url: str, day: str) -> Path:
    out = RAW_DIR / f"istdaten_{day}.parquet"
    if out.exists():
        print(f"{day} : déjà présent, ignoré")
        return out
    local = download(url, day)
    con = duckdb.connect()
    src = f"read_csv('{local}', delim=';', header=true, all_varchar=true, ignore_errors=true)"
    cols = [r[0].upper() for r in con.execute(f"DESCRIBE SELECT * FROM {src}").fetchall()]
    missing = [c for c in REQUIRED if c not in cols]
    if missing:
        sys.exit(f"{day} : colonnes manquantes {missing}. Colonnes trouvées : {cols}")
    # Les colonnes optionnelles absentes sont créées vides pour garder un schéma stable.
    select = ", ".join([f'"{c}"' for c in REQUIRED] + [f'"{c}"' if c in cols else f'NULL::VARCHAR AS "{c}"' for c in OPTIONAL])
    # Les noms peuvent arriver en minuscules : DuckDB est insensible à la casse ici.
    con.execute(f"""
        COPY (
            SELECT {select}
            FROM {src}
            WHERE upper(trim(PRODUKT_ID)) IN ('ZUG', 'TRAIN', 'RAIL')
        ) TO '{out}' (FORMAT parquet, COMPRESSION zstd)
    """)
    n = con.execute(f"SELECT count(*) FROM read_parquet('{out}')").fetchone()[0]
    local.unlink(missing_ok=True)
    print(f"{day} : {n:,} arrêts de trains conservés".replace(",", "'"))
    if n == 0:
        out.unlink()
        sys.exit(f"{day} : aucun train trouvé, vérifier les valeurs de PRODUKT_ID")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7, help="nombre de jours récents à récupérer")
    ap.add_argument("--url", help="URL d'un CSV précis")
    ap.add_argument("--date", help="date ISO du CSV précis")
    args = ap.parse_args()
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    if args.url:
        convert(args.url, args.date or date.today().isoformat())
        return
    for day, url in list_daily_files()[: args.days]:
        try:
            convert(url, day)
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001  un jour défectueux ne bloque pas les autres
            print(f"{day} : échec ({e}), jour ignoré")


if __name__ == "__main__":
    main()
