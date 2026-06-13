#!/usr/bin/env python3
"""Importa i layer OSM (Geofabrik Nord-Est Italia) nella piattaforma mappa.

I 20 shapefile in "data/dataset/OpenStreetMap Data for the North-Est of Italy
(May 2026)" coprono l'intero Nord-Est (1,6M strade, 4,6M edifici): qui vengono
ritagliati sulla provincia di Vicenza (unione dei confini comunali + buffer
500 m), caricati in PostGIS via COPY e registrati nel catalogo public.layers.

I seed SQL in infra/postgres/ girano solo al primo boot e non possono contenere
gigabyte di geometrie: questo script è la via per i dati pesanti. È idempotente
(DROP/CREATE per tabella) e va rilanciato dopo un `docker compose down -v`.

Uso:
    .venv/bin/python3.14 work/src/import_osm_layers.py            # tutti i layer
    .venv/bin/python3.14 work/src/import_osm_layers.py --only roads,buildings
    .venv/bin/python3.14 work/src/import_osm_layers.py --list

Dopo l'import: cd work/map && docker compose restart martin
(Martin scopre le tabelle dello schema `data` solo all'avvio).
"""
import argparse
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import psycopg
import pyogrio
import shapely

ROOT = Path(__file__).resolve().parents[2]
OSM_DIR = ROOT / "data" / "dataset" / "OpenStreetMap Data for the North-Est of Italy (May 2026)"
COMUNI_SHP = ROOT / "data" / "dataset" / "extracted" / "comuni" / "c0104011_comuni_VI.shp"
DSN = "host=localhost port=5433 dbname=geosentinel user=postgres password=postgres"
SOURCE_URL = "https://download.geofabrik.de/europe/italy/nord-est.html"

ZOOM_WIDTH = ["interpolate", ["linear"], ["zoom"], 8, 0.4, 12, 1.5, 15, 3]
ZOOM_RADIUS = ["interpolate", ["linear"], ["zoom"], 10, 2, 13, 4, 16, 7]

ROAD_COLORS = [
    "match", ["get", "fclass"],
    "motorway", "#e8590c", "motorway_link", "#e8590c",
    "trunk", "#f08c00", "trunk_link", "#f08c00",
    "primary", "#f59f00", "primary_link", "#f59f00",
    "secondary", "#fcc419", "secondary_link", "#fcc419",
    "tertiary", "#74b816", "tertiary_link", "#74b816",
    "residential", "#868e96", "living_street", "#868e96", "pedestrian", "#868e96",
    "service", "#adb5bd", "unclassified", "#adb5bd",
    "#ced4da",
]
ROAD_LEGEND = [
    {"label": "Autostrada", "color": "#e8590c"},
    {"label": "Statale/trunk", "color": "#f08c00"},
    {"label": "Primaria", "color": "#f59f00"},
    {"label": "Secondaria", "color": "#fcc419"},
    {"label": "Terziaria", "color": "#74b816"},
    {"label": "Urbana/residenziale", "color": "#868e96"},
    {"label": "Altro", "color": "#ced4da"},
]
LANDUSE_COLORS = [
    "match", ["get", "fclass"],
    "forest", "#2b8a3e",
    "grass", "#8ce99a", "meadow", "#8ce99a", "scrub", "#8ce99a", "heath", "#8ce99a",
    "farmland", "#ffe999", "farmyard", "#ffe999",
    "vineyard", "#94d82d", "orchard", "#94d82d", "allotments", "#94d82d",
    "residential", "#ced4da",
    "industrial", "#b197fc", "commercial", "#b197fc", "retail", "#b197fc",
    "quarry", "#868e96", "military", "#868e96",
    "#dee2e6",
]
LANDUSE_LEGEND = [
    {"label": "Bosco", "color": "#2b8a3e"},
    {"label": "Prato/incolto", "color": "#8ce99a"},
    {"label": "Agricolo", "color": "#ffe999"},
    {"label": "Vigneto/frutteto", "color": "#94d82d"},
    {"label": "Residenziale", "color": "#ced4da"},
    {"label": "Industriale/commerciale", "color": "#b197fc"},
]


def line_style(color, legend_label, minzoom=None, color_expr=None, legend=None):
    s = {
        "paint": {"line-color": color_expr or color, "line-width": ZOOM_WIDTH},
        "filters": ["fclass"],
        "legend": legend or [{"label": legend_label, "color": color}],
    }
    if minzoom is not None:
        s["minzoom"] = minzoom
    return s


def fill_style(color, legend_label, opacity=0.45, minzoom=None, color_expr=None, legend=None):
    s = {
        "paint": {
            "fill-color": color_expr or color,
            "fill-opacity": opacity,
            "fill-outline-color": color,
        },
        "filters": ["fclass"],
        "legend": legend or [{"label": legend_label, "color": color}],
    }
    if minzoom is not None:
        s["minzoom"] = minzoom
    return s


def point_style(color, legend_label, minzoom=None, color_expr=None, legend=None):
    s = {
        "paint": {
            "circle-color": color_expr or color,
            "circle-radius": ZOOM_RADIUS,
            "circle-opacity": 0.75,
            "circle-stroke-width": 0.5,
            "circle-stroke-color": "#ffffff",
        },
        "filters": ["fclass"],
        "legend": legend or [{"label": legend_label, "color": color}],
    }
    if minzoom is not None:
        s["minzoom"] = minzoom
    return s


# Elementi di sicurezza stradale colorati per categoria (usati dai toggle in /analisi).
TRAFFIC_COLORS = [
    "match", ["get", "fclass"],
    "pedestrian_crossing", "#1971c2",
    "traffic_signals", "#e03131",
    "stop", "#f08c00",
    ["mini_roundabout", "motorway_junction", "turning_circle", "railway_crossing"], "#9c36b5",
    "speed_camera", "#212529",
    "street_lamp", "#ffd43b",
    "#adb5bd",
]
TRAFFIC_LEGEND = [
    {"label": "Attraversamenti", "color": "#1971c2"},
    {"label": "Semafori", "color": "#e03131"},
    {"label": "Stop", "color": "#f08c00"},
    {"label": "Incroci/rotatorie", "color": "#9c36b5"},
    {"label": "Autovelox", "color": "#212529"},
    {"label": "Lampioni", "color": "#ffd43b"},
]


# chiave breve -> (shapefile, tabella, geom_type catalogo, titolo, descrizione tema, style, zoom)
THEMES = {
    "roads": ("gis_osm_roads_free_1.shp", "osm_roads", "line",
              "OSM — Rete stradale", "tutta la viabilità (da autostrade a sentieri), colorata per classe",
              line_style("#868e96", "Strada", color_expr=ROAD_COLORS, legend=ROAD_LEGEND), 10),
    "railways": ("gis_osm_railways_free_1.shp", "osm_railways", "line",
                 "OSM — Ferrovie", "linee ferroviarie, tram e funivie",
                 line_style("#495057", "Ferrovia"), 10),
    "waterways": ("gis_osm_waterways_free_1.shp", "osm_waterways", "line",
                  "OSM — Corsi d'acqua", "fiumi, torrenti e canali",
                  line_style("#4dabf7", "Corso d'acqua"), 10),
    "water": ("gis_osm_water_a_free_1.shp", "osm_water", "polygon",
              "OSM — Specchi d'acqua", "laghi, bacini e aree fluviali",
              fill_style("#74c0fc", "Acqua", opacity=0.55), 10),
    "buildings": ("gis_osm_buildings_a_free_1.shp", "osm_buildings", "polygon",
                  "OSM — Edifici", "impronte degli edifici (visibili da zoom 12)",
                  fill_style("#adb5bd", "Edificio", opacity=0.6, minzoom=12), 13),
    "landuse": ("gis_osm_landuse_a_free_1.shp", "osm_landuse", "polygon",
                "OSM — Uso del suolo", "bosco, agricolo, residenziale, industriale…",
                fill_style("#8ce99a", "Uso del suolo", color_expr=LANDUSE_COLORS,
                           legend=LANDUSE_LEGEND), 10),
    "natural": ("gis_osm_natural_free_1.shp", "osm_natural", "point",
                "OSM — Elementi naturali (punti)", "cime, sorgenti, alberi monumentali…",
                point_style("#40c057", "Elemento naturale", minzoom=10), 10),
    "natural_areas": ("gis_osm_natural_a_free_1.shp", "osm_natural_areas", "polygon",
                      "OSM — Elementi naturali (aree)", "aree naturali (ghiacciai, zone umide…)",
                      fill_style("#69db7c", "Area naturale"), 10),
    "protected_areas": ("gis_osm_protected_areas_a_free_1.shp", "osm_protected_areas", "polygon",
                        "OSM — Aree protette", "parchi e riserve naturali",
                        fill_style("#37b24d", "Area protetta", opacity=0.3), 10),
    "adminareas": ("gis_osm_adminareas_a_free_1.shp", "osm_adminareas", "polygon",
                   "OSM — Confini amministrativi", "comuni e suddivisioni amministrative",
                   fill_style("#495057", "Confine", opacity=0.06), 10),
    "places": ("gis_osm_places_free_1.shp", "osm_places", "point",
               "OSM — Località (punti)", "città, paesi, frazioni e località",
               point_style("#7048e8", "Località"), 10),
    "places_areas": ("gis_osm_places_a_free_1.shp", "osm_places_areas", "polygon",
                     "OSM — Località (aree)", "perimetri delle località",
                     fill_style("#9775fa", "Località", opacity=0.25), 10),
    "pois": ("gis_osm_pois_free_1.shp", "osm_pois", "point",
             "OSM — Punti di interesse", "POI: servizi, negozi, scuole… (da zoom 11)",
             point_style("#e64980", "POI", minzoom=11), 12),
    "pois_areas": ("gis_osm_pois_a_free_1.shp", "osm_pois_areas", "polygon",
                   "OSM — Punti di interesse (aree)", "POI areali (campus, impianti sportivi…)",
                   fill_style("#f783ac", "POI areale", minzoom=11), 12),
    "pofw": ("gis_osm_pofw_free_1.shp", "osm_pofw", "point",
             "OSM — Luoghi di culto (punti)", "chiese, capitelli e altri luoghi di culto",
             point_style("#9c36b5", "Luogo di culto", minzoom=11), 12),
    "pofw_areas": ("gis_osm_pofw_a_free_1.shp", "osm_pofw_areas", "polygon",
                   "OSM — Luoghi di culto (aree)", "edifici di culto areali",
                   fill_style("#b563d6", "Luogo di culto", minzoom=11), 12),
    "traffic": ("gis_osm_traffic_free_1.shp", "osm_traffic", "point",
                "OSM — Infrastruttura traffico (punti)",
                "semafori, attraversamenti, dossi, autovelox… (da zoom 11)",
                point_style("#fab005", "Traffico", minzoom=11,
                            color_expr=TRAFFIC_COLORS, legend=TRAFFIC_LEGEND), 12),
    "traffic_areas": ("gis_osm_traffic_a_free_1.shp", "osm_traffic_areas", "polygon",
                      "OSM — Infrastruttura traffico (aree)", "parcheggi e aree di servizio",
                      fill_style("#ffd43b", "Traffico areale", minzoom=11), 12),
    "transport": ("gis_osm_transport_free_1.shp", "osm_transport", "point",
                  "OSM — Trasporto pubblico (punti)", "fermate bus, stazioni, funivie",
                  point_style("#15aabf", "Trasporto pubblico", minzoom=10), 11),
    "transport_areas": ("gis_osm_transport_a_free_1.shp", "osm_transport_areas", "polygon",
                        "OSM — Trasporto pubblico (aree)", "aree di stazioni e terminal",
                        fill_style("#3bc9db", "Trasporto areale", minzoom=10), 11),
}


def provincia_vicenza():
    """Unione dei confini comunali (EPSG:3003) + buffer 500 m, in EPSG:4326."""
    comuni = gpd.read_file(COMUNI_SHP)
    prov = shapely.union_all(comuni.geometry.values).buffer(500)
    prov4326 = gpd.GeoSeries([prov], crs=comuni.crs).to_crs(4326).iloc[0]
    shapely.prepare(prov4326)
    return prov4326


def pg_type(dtype) -> str:
    if pd.api.types.is_integer_dtype(dtype):
        return "bigint"
    if pd.api.types.is_float_dtype(dtype):
        return "double precision"
    if pd.api.types.is_bool_dtype(dtype):
        return "boolean"
    return "text"


def carica_tema(conn, key: str, prov) -> dict | None:
    shp, table, geom_type, title, desc, style, zoom = THEMES[key]
    path = OSM_DIR / shp
    print(f"\n[{key}] leggo {shp} (bbox provincia)…", flush=True)
    gdf = pyogrio.read_dataframe(path, bbox=prov.bounds)
    mask = shapely.intersects(gdf.geometry.values, prov)
    gdf = gdf[mask].reset_index(drop=True)
    print(f"[{key}] {mask.sum()} feature nella provincia ({len(mask)} nel bbox)")
    if gdf.empty:
        print(f"[{key}] vuoto: salto")
        return None

    attr_cols = [c for c in gdf.columns if c != "geometry"]
    ddl_cols = ", ".join(f'"{c}" {pg_type(gdf[c].dtype)}' for c in attr_cols)
    geoms = shapely.set_srid(gdf.geometry.values, 4326)
    wkb = shapely.to_wkb(geoms, hex=True, include_srid=True)

    with conn.cursor() as cur:
        cur.execute(f"DROP TABLE IF EXISTS data.{table} CASCADE")
        cur.execute(
            f"CREATE TABLE data.{table} (id bigserial PRIMARY KEY, "
            f"geom geometry(Geometry, 4326) NOT NULL, {ddl_cols})"
        )
        col_list = ", ".join(["geom"] + [f'"{c}"' for c in attr_cols])
        attrs = gdf[attr_cols]
        attrs = attrs.astype(object).where(pd.notna(attrs), None)
        with cur.copy(f"COPY data.{table} ({col_list}) FROM STDIN") as cp:
            for g, row in zip(wkb, attrs.itertuples(index=False, name=None)):
                cp.write_row((g, *row))
        cur.execute(f"CREATE INDEX {table}_geom_gist ON data.{table} USING GIST (geom)")
        if "fclass" in attr_cols:
            cur.execute(f"CREATE INDEX {table}_fclass_idx ON data.{table} (fclass)")
        cur.execute(f"ANALYZE data.{table}")
    conn.commit()

    minx, miny, maxx, maxy = gdf.total_bounds
    return {
        "slug": f"osm-{key.replace('_', '-')}",
        "table": table,
        "geom_type": geom_type,
        "title": title,
        "n": len(gdf),
        "desc": desc,
        "style": style,
        "zoom": zoom,
        "bounds": (float(minx), float(miny), float(maxx), float(maxy)),
    }


def registra_layer(conn, meta: dict):
    minx, miny, maxx, maxy = meta["bounds"]
    cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
    descr = (
        f"Layer OpenStreetMap (estratto Geofabrik Nord-Est, maggio 2026) ritagliato "
        f"sulla provincia di Vicenza: {meta['n']} feature — {meta['desc']}. "
        f"Filtra per classe (fclass) per esplorare le categorie."
    )
    with conn.cursor() as cur:
        cur.execute("DELETE FROM public.layers WHERE slug = %s", (meta["slug"],))
        cur.execute(
            """INSERT INTO public.layers
                 (slug, title, description, kind, geom_type, source_table,
                  bbox, default_center, default_zoom, style, tags, source_url)
               VALUES (%s, %s, %s, 'vector', %s, %s,
                       ST_MakeEnvelope(%s, %s, %s, %s, 4326),
                       ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                       %s, %s::jsonb, %s, %s)""",
            (meta["slug"], meta["title"], descr, meta["geom_type"], meta["table"],
             minx, miny, maxx, maxy, cx, cy, meta["zoom"],
             json.dumps(meta["style"]), ["osm", "vicenza", "vector"], SOURCE_URL),
        )
    conn.commit()


MAXSPEED_STYLE = {
    "filter": [">", ["get", "maxspeed"], 0],
    "paint": {
        "line-color": ["step", ["get", "maxspeed"],
                       "#40c057", 40, "#fab005", 60, "#f76707", 80, "#e03131", 100, "#862e9c"],
        "line-width": ["interpolate", ["linear"], ["zoom"], 8, 1, 12, 2.5, 15, 4],
    },
    "filters": ["maxspeed"],
    "legend": [
        {"label": "≤ 30 km/h", "color": "#40c057"},
        {"label": "40-50 km/h", "color": "#fab005"},
        {"label": "60-70 km/h", "color": "#f76707"},
        {"label": "80-90 km/h", "color": "#e03131"},
        {"label": "≥ 100 km/h", "color": "#862e9c"},
    ],
}


def registra_maxspeed(conn, roads_meta: dict):
    """Layer derivato: stessa tabella osm_roads, colorato per limite di velocità."""
    meta = dict(roads_meta)
    meta.update({
        "slug": "osm-maxspeed",
        "title": "OSM — Limiti di velocità",
        "desc": ("strade colorate per limite di velocità OSM (solo gli archi con "
                 "limite mappato; gli altri sono nascosti)"),
        "style": MAXSPEED_STYLE,
        "geom_type": "line",
        "zoom": 10,
    })
    registra_layer(conn, meta)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", help="lista di temi separati da virgola (default: tutti)")
    ap.add_argument("--list", action="store_true", help="elenca i temi disponibili")
    args = ap.parse_args()

    if args.list:
        for k, (shp, table, gt, title, *_rest) in THEMES.items():
            print(f"{k:18} {gt:8} data.{table:22} {title}")
        return

    keys = [k.strip() for k in args.only.split(",")] if args.only else list(THEMES)
    sconosciuti = [k for k in keys if k not in THEMES]
    if sconosciuti:
        sys.exit(f"Temi sconosciuti: {sconosciuti} (usa --list)")

    print("Costruisco il confine della provincia di Vicenza…")
    prov = provincia_vicenza()

    caricati = []
    with psycopg.connect(DSN) as conn:
        for k in keys:
            meta = carica_tema(conn, k, prov)
            if meta:
                registra_layer(conn, meta)
                caricati.append(meta)
                if k == "roads":
                    registra_maxspeed(conn, meta)

    print(f"\n{'slug':28} {'feature':>9}  tabella")
    for m in caricati:
        print(f"{m['slug']:28} {m['n']:>9}  data.{m['table']}")
    print("\nFatto. Ora: cd work/map && docker compose restart martin")


if __name__ == "__main__":
    main()
