#!/usr/bin/env python3
"""Risk engine — feature infrastrutturali per segmento (spec A5, contratti 1-2).

Per ognuno dei 179 segmenti km calcola, entro BUFFER_M dalla geometria:
  - n_attraversamenti, n_semafori, n_stop, n_incroci, n_autovelox, n_lampioni
    (da data.osm_traffic, categorie come il layer "Sicurezza stradale")
  - maxspeed_med: mediana dei limiti OSM mappati (>0) sugli archi vicini
  - comune: dal confine comunale che contiene il centroide del segmento

Aggiorna data.road_segments (i popup della mappa mostrano le nuove colonne) e
produce i due file-contratto per il team ML (vedi docs/08-spec.md):
  - work/output/segment_features.csv
  - work/output/training_arricchito.csv  (training v2 + feature di segmento)

Uso:
    .venv/bin/python3.14 work/src/build_segment_features.py
    cd work/map && docker compose restart martin
"""
from pathlib import Path

import geopandas as gpd
import pandas as pd
import psycopg
import shapely

BUFFER_M   = 50    # raggio di pertinenza segmento ↔ elemento di sicurezza
MAX_DIST_M = 300   # assegnazione punto di training → segmento

ROOT    = Path(__file__).resolve().parents[2]
SHP_COM = ROOT / "data" / "dataset" / "extracted" / "comuni" / "c0104011_comuni_VI.shp"
TRAIN   = ROOT / "work" / "output" / "training_dataset.csv"
OUT_DIR = ROOT / "work" / "output"
DSN     = "host=localhost port=5433 dbname=geosentinel user=postgres password=postgres"

CATEGORIE = {
    'n_attraversamenti': ['pedestrian_crossing'],
    'n_semafori':        ['traffic_signals'],
    'n_stop':            ['stop'],
    'n_incroci':         ['mini_roundabout', 'motorway_junction', 'turning_circle',
                          'railway_crossing'],
    'n_autovelox':       ['speed_camera'],
    'n_lampioni':        ['street_lamp'],
}
FEATURE_COLS = list(CATEGORIE) + ['maxspeed_med']


def leggi_gdf(conn, sql: str, cols: list[str]) -> gpd.GeoDataFrame:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=cols + ['wkb'])
    geom = shapely.from_wkb(df.pop('wkb').values)
    return gpd.GeoDataFrame(df, geometry=geom, crs=4326)


def main():
    with psycopg.connect(DSN) as conn:
        seg = leggi_gdf(conn, """
            SELECT id, nome_strada, km_idx, lunghezza_m, n_incidenti, tot_morti,
                   tot_feriti, indice_grezzo, indice, ST_AsBinary(geom)
            FROM data.road_segments""",
            ['id', 'nome_strada', 'km_idx', 'lunghezza_m', 'n_incidenti',
             'tot_morti', 'tot_feriti', 'indice_grezzo', 'indice'])
        traffic = leggi_gdf(conn, """
            SELECT fclass, ST_AsBinary(geom) FROM data.osm_traffic""", ['fclass'])
        roads = leggi_gdf(conn, """
            SELECT maxspeed, ST_AsBinary(geom) FROM data.osm_roads
            WHERE maxspeed > 0""", ['maxspeed'])

        seg_m     = seg.to_crs(6707)
        traffic_m = traffic.to_crs(6707)
        roads_m   = roads.to_crs(6707)

        # Elementi di sicurezza entro BUFFER_M dal segmento
        buffer = seg_m[['id']].copy()
        buffer['geometry'] = seg_m.geometry.buffer(BUFFER_M)
        buffer = gpd.GeoDataFrame(buffer, crs=seg_m.crs)
        join = gpd.sjoin(traffic_m, buffer, predicate='within')
        for col, fclasses in CATEGORIE.items():
            conteggi = join[join['fclass'].isin(fclasses)].groupby('id').size()
            seg[col] = seg['id'].map(conteggi).fillna(0).astype(int)

        # Limite di velocità mediano sugli archi OSM vicini
        jr = gpd.sjoin(roads_m, buffer, predicate='intersects')
        med = jr.groupby('id')['maxspeed'].median()
        seg['maxspeed_med'] = seg['id'].map(med).round().astype('Int64')

        # Comune dal centroide
        comuni = gpd.read_file(SHP_COM).to_crs(6707)
        cent = seg_m.copy()
        cent['geometry'] = seg_m.geometry.centroid
        cj = gpd.sjoin_nearest(cent[['id', 'geometry']], comuni[['nomcom', 'geometry']])
        seg['comune'] = seg['id'].map(cj.set_index('id')['nomcom'].str.upper())

        # Aggiorna il DB (popup mappa + pagina priorità)
        with conn.cursor() as cur:
            cur.execute("""ALTER TABLE data.road_segments
                ADD COLUMN IF NOT EXISTS comune text,
                ADD COLUMN IF NOT EXISTS n_attraversamenti int,
                ADD COLUMN IF NOT EXISTS n_semafori int,
                ADD COLUMN IF NOT EXISTS n_stop int,
                ADD COLUMN IF NOT EXISTS n_incroci int,
                ADD COLUMN IF NOT EXISTS n_autovelox int,
                ADD COLUMN IF NOT EXISTS n_lampioni int,
                ADD COLUMN IF NOT EXISTS maxspeed_med int""")
            cur.executemany("""
                UPDATE data.road_segments SET comune=%s, n_attraversamenti=%s,
                  n_semafori=%s, n_stop=%s, n_incroci=%s, n_autovelox=%s,
                  n_lampioni=%s, maxspeed_med=%s WHERE id=%s""",
                [(r.comune, r.n_attraversamenti, r.n_semafori, r.n_stop,
                  r.n_incroci, r.n_autovelox, r.n_lampioni,
                  None if pd.isna(r.maxspeed_med) else int(r.maxspeed_med), r.id)
                 for r in seg.itertuples()])
        conn.commit()

    # ── Contratto 1: feature per segmento ────────────────────────────────
    out_cols = ['id', 'nome_strada', 'comune', 'km_idx', 'lunghezza_m',
                *FEATURE_COLS, 'n_incidenti', 'indice_grezzo', 'indice']
    features = seg[out_cols].rename(columns={'id': 'segment_id'})
    features.to_csv(OUT_DIR / 'segment_features.csv', index=False)

    # ── Contratto 2: training arricchito ────────────────────────────────
    train = pd.read_csv(TRAIN)
    pts = gpd.GeoDataFrame(
        train, geometry=gpd.points_from_xy(train['lon'], train['lat']), crs=4326,
    ).to_crs(6707)
    nearest = gpd.sjoin_nearest(
        pts, seg.to_crs(6707)[['id', *FEATURE_COLS, 'geometry']],
        how='left', max_distance=MAX_DIST_M, distance_col='dist_m',
    ).sort_values('dist_m').groupby(level=0).head(1).sort_index()
    arr = nearest.drop(columns=['geometry', 'index_right', 'dist_m']).rename(
        columns={'id': 'segment_id'})
    n_orfani = arr['segment_id'].isna().sum()
    for c in CATEGORIE:
        arr[c] = arr[c].fillna(0).astype(int)
    arr['maxspeed_med'] = arr['maxspeed_med'].fillna(
        features['maxspeed_med'].median()).astype(int)
    arr.to_csv(OUT_DIR / 'training_arricchito.csv', index=False)

    print(f"segment_features.csv:    {len(features)} segmenti")
    print(f"training_arricchito.csv: {len(arr)} righe "
          f"({n_orfani} senza segmento entro {MAX_DIST_M} m, feature=0/mediana)")
    print("\nTotali elementi per categoria sui corridoi:")
    print(features[list(CATEGORIE)].sum().to_string())
    print("\nOra: cd work/map && docker compose restart martin")


if __name__ == "__main__":
    main()
