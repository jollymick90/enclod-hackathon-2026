#!/usr/bin/env python3
"""Importa i confini comunali della provincia di Vicenza in PostGIS e li registra nel catalogo.

Sorgente: data/dataset/extracted/comuni/c0104011_comuni_VI.shp (EPSG:3003, 121 comuni).
Produce: tabella data.comuni_vicenza + riga in public.layers (slug 'comuni-vicenza').
Idempotente: DROP/CREATE se eseguito di nuovo.

Uso:
    .venv/bin/python3.14 work/src/import_comuni.py
"""
import json
from pathlib import Path

import geopandas as gpd
import psycopg
import shapely

ROOT     = Path(__file__).resolve().parents[2]
SHP_PATH = ROOT / "data" / "dataset" / "extracted" / "comuni" / "c0104011_comuni_VI.shp"
DSN      = "host=localhost port=5433 dbname=geosentinel user=postgres password=postgres"

STYLE = {
    "paint": {
        "fill-color": "#6366f1",
        "fill-opacity": 0.08,
        "fill-outline-color": "#6366f1",
    },
    "filters": ["nomcom"],
    "legend": [{"label": "Comuni (VI)", "color": "#6366f1"}],
}


def main():
    print("Leggo shapefile comuni…")
    gdf = gpd.read_file(SHP_PATH).to_crs(4326)
    gdf.columns = [c.lower() for c in gdf.columns]
    print(f"{len(gdf)} comuni, colonne: {list(gdf.columns)}")

    geoms = shapely.set_srid(gdf.geometry.values, 4326)
    wkb   = shapely.to_wkb(geoms, hex=True, include_srid=True)

    attr_cols = [c for c in gdf.columns if c != "geometry"]

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS data.comuni_vicenza CASCADE")
            ddl = ", ".join(f'"{c}" text' for c in attr_cols)
            cur.execute(
                f"CREATE TABLE data.comuni_vicenza ("
                f"  id bigserial PRIMARY KEY,"
                f"  geom geometry(MultiPolygon, 4326) NOT NULL,"
                f"  {ddl}"
                f")"
            )
            col_list = ", ".join(["geom"] + [f'"{c}"' for c in attr_cols])
            with cur.copy(f"COPY data.comuni_vicenza ({col_list}) FROM STDIN") as cp:
                for g, row in zip(wkb, gdf[attr_cols].itertuples(index=False, name=None)):
                    cp.write_row((g, *row))
            cur.execute("CREATE INDEX comuni_geom_gist ON data.comuni_vicenza USING GIST (geom)")
            cur.execute("CREATE INDEX comuni_nomcom_idx ON data.comuni_vicenza (nomcom)")
            cur.execute("ANALYZE data.comuni_vicenza")

        minx, miny, maxx, maxy = gdf.total_bounds
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        descr = (
            f"Confini amministrativi dei {len(gdf)} comuni della provincia di Vicenza "
            f"(fonte: Regione Veneto, dati della challenge). "
            f"Contorno viola semitrasparente, filtrabile per nome comune."
        )
        style_json = json.dumps(STYLE)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.layers WHERE slug = 'comuni-vicenza'")
            cur.execute(
                """INSERT INTO public.layers
                     (slug, title, description, kind, geom_type, source_table,
                      bbox, default_center, default_zoom, style, tags, source_url)
                   VALUES (%s,%s,%s,'vector','polygon','comuni_vicenza',
                           ST_MakeEnvelope(%s,%s,%s,%s,4326),
                           ST_SetSRID(ST_MakePoint(%s,%s),4326),
                           10, %s::jsonb, %s, NULL)""",
                ("comuni-vicenza", "Comuni — Provincia di Vicenza", descr,
                 minx, miny, maxx, maxy, cx, cy,
                 style_json, ["vicenza", "comuni", "vettoriale"]),
            )
        conn.commit()

    print(f"OK: {len(gdf)} comuni → data.comuni_vicenza + catalogo 'comuni-vicenza'")
    print("Ora: cd work/map && docker compose restart martin")


if __name__ == "__main__":
    main()
