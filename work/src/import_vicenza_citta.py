#!/usr/bin/env python3
"""Layer "Incidenti Vicenza città" (2011–2020) — import diretto in PostGIS.

Pubblica i 4.475 incidenti geocodificati del COMUNE di Vicenza (fonte open data
del Comune, contesto urbano) come layer vettoriale `data.incidenti_vicenza_citta`.
È un dato SEPARATO dai 738 incidenti dei 3 corridoi SP e NON entra nel modello:
serve alla pagina /vicenza-citta e alla narrazione "scalabilità del catalogo".

Pattern come import_osm_layers.py / import_comuni.py: scrive direttamente nel DB
(non un seed), quindi finisce nel dump usato per il deploy. Dopo un
`docker compose down -v` va rilanciato (come i layer OSM).

Uso:
    .venv/bin/python3.14 work/src/import_vicenza_citta.py
    cd work/map && docker compose restart martin
"""
import json
import re
from pathlib import Path

import geopandas as gpd
import psycopg

ROOT = Path(__file__).resolve().parents[2]
SHP  = ROOT / "data" / "dataset" / "opendata_incidenti_comune_vicenza" / "opendata_incidenti_comune_vicenza.shp"
DSN  = "host=localhost port=5433 dbname=geosentinel user=postgres password=postgres"

# bbox largo della provincia di Vicenza (scarta geometrie palesemente sbagliate)
BBOX = (10.8, 45.2, 12.2, 46.1)  # minlon, minlat, maxlon, maxlat

# Stile gemello del layer provinciale (palette/legenda coerenti tra i due).
STYLE = {
    "paint": {
        "circle-color": ["match", ["get", "gravita"],
                         "mortale", "#dc2626", "feriti", "#f59e0b", "danni", "#9ca3af", "#9ca3af"],
        "circle-radius": ["interpolate", ["linear"], ["get", "feriti"], 0, 4, 2, 7, 5, 11, 15, 18],
        "circle-opacity": 0.85,
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 1,
    },
    "legend": [
        {"color": "#dc2626", "label": "Mortale"},
        {"color": "#f59e0b", "label": "Con feriti"},
        {"color": "#9ca3af", "label": "Solo danni"},
    ],
    "filters": ["anno", "gravita", "natura"],
}


def _testo(v) -> str | None:
    """Normalizza un valore testuale, trattando NaN/vuoti come None."""
    if v is None:
        return None
    s = str(v).strip()
    if s.lower() in ("", "nan", "none", "<na>"):
        return None
    return s


def pulisci_via(v) -> str | None:
    s = _testo(v)
    return re.sub(r"^\d+\s+", "", s) if s else None  # "8220 VIALE..." -> "VIALE..."


def gravita(morti: int, feriti: int) -> str:
    if morti > 0:
        return "mortale"
    if feriti > 0:
        return "feriti"
    return "danni"


def main():
    g = gpd.read_file(SHP)
    if g.crs is None or g.crs.to_epsg() != 4326:
        g = g.to_crs(4326)

    righe, scarti = [], 0
    for _, r in g.iterrows():
        geom = r.geometry
        if geom is None or geom.is_empty:
            scarti += 1
            continue
        lon, lat = geom.x, geom.y
        if not (BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]):
            scarti += 1
            continue
        anno = int(r["ANNO"]) if r["ANNO"] is not None else None
        if anno is None or not (2011 <= anno <= 2020):
            scarti += 1
            continue
        morti = int(r["MORTI"] or 0)
        feriti = int(r["FERITI"] or 0)
        righe.append((
            anno,
            int(r["MESE"]) if r["MESE"] is not None else None,
            int(r["GIORNO"]) if r["GIORNO"] is not None else None,
            pulisci_via(r["VIA1"]),
            pulisci_via(r["VIA2"]),
            _testo(r["NATURA_INC"]),
            int(r["NUMERO_VEI"]) if r["NUMERO_VEI"] is not None else None,
            feriti, morti, gravita(morti, feriti), lon, lat,
        ))

    tot_morti = sum(x[8] for x in righe)
    tot_feriti = sum(x[7] for x in righe)
    print(f"Righe valide: {len(righe)} (scartate: {scarti}) — morti {tot_morti}, feriti {tot_feriti}")

    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS data.incidenti_vicenza_citta CASCADE")
        cur.execute("""
            CREATE TABLE data.incidenti_vicenza_citta (
                id           serial PRIMARY KEY,
                anno         int  NOT NULL,
                mese         int,
                giorno       int,
                via          text,
                via_incrocio text,
                natura       text,
                n_veicoli    int,
                feriti       int  NOT NULL,
                morti        int  NOT NULL,
                gravita      text NOT NULL,
                geom         geometry(Point, 4326) NOT NULL
            )
        """)
        cur.executemany(
            """INSERT INTO data.incidenti_vicenza_citta
               (anno, mese, giorno, via, via_incrocio, natura, n_veicoli, feriti, morti, gravita, geom)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, ST_SetSRID(ST_MakePoint(%s,%s),4326))""",
            righe,
        )
        cur.execute("CREATE INDEX incidenti_vicenza_citta_geom_gist ON data.incidenti_vicenza_citta USING gist (geom)")

        # riga di catalogo (idempotente)
        cur.execute("""
            INSERT INTO public.layers
              (slug, title, description, kind, geom_type, source_table,
               default_center, default_zoom, style, tags)
            VALUES (
              'incidenti-vicenza-citta',
              'Incidenti stradali — Comune di Vicenza (2011–2020)',
              %s, 'vector', 'point', 'incidenti_vicenza_citta',
              ST_SetSRID(ST_MakePoint(11.546, 45.547), 4326), 12, %s,
              ARRAY['soluzione','citta']
            )
            ON CONFLICT (slug) DO UPDATE
              SET title = EXCLUDED.title, description = EXCLUDED.description,
                  style = EXCLUDED.style, default_center = EXCLUDED.default_center,
                  default_zoom = EXCLUDED.default_zoom
        """, (
            f"{len(righe)} incidenti geocodificati del Comune di Vicenza (2011–2020), "
            "fonte open data del Comune. Dato urbano, FUORI dal perimetro del modello "
            "predittivo (che copre i 3 corridoi provinciali).",
            json.dumps(STYLE),
        ))
        conn.commit()

    print("OK. Ora: cd work/map && docker compose restart martin")


if __name__ == "__main__":
    main()
