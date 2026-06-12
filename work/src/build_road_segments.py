#!/usr/bin/env python3
"""Risk engine — step 1: segmenti chilometrici dei corridoi SP con indice storico.

Taglia i 3 corridoi (SP 46, SP 349, SP 350) in segmenti da 1 km sulla geometria
reale del grafo "SP OSM 6707" (EPSG:6707, metri), assegna ogni incidente reale
al segmento più vicino (entro MAX_DIST_M) e calcola un indice di pericolosità
storica 0-100 per segmento.

Crea inoltre la tabella-contratto `data.segment_risk` per lo step 2: lo scoring
del modello predittivo per scenario (segmento × meteo × fascia oraria) — vedi
docs/_deprecated/07-risk-engine.md.

Output:
  - data.road_segments (PostGIS) + layer catalogo 'rischio-storico'
  - data.segment_risk (vuota, da riempire con le predizioni del modello)

Uso:
    .venv/bin/python3.14 work/src/build_road_segments.py
    cd work/map && docker compose restart martin
"""
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
import psycopg
import shapely
from shapely.ops import linemerge, substring

# ── Parametri da tarare (decisione di dominio) ────────────────────────────
# Pesi della formula dell'indice storico: quanto "pesa" un morto rispetto a
# un ferito o a un incidente con soli danni. Cambiarli sposta quali segmenti
# diventano rossi sulla mappa.
PESO_MORTO  = 10.0
PESO_FERITO = 3.0
PESO_DANNI  = 1.0   # incidente senza morti né feriti

SEG_LEN_M  = 1000   # lunghezza segmento (metri)
MAX_DIST_M = 300    # distanza max incidente→segmento per l'assegnazione
ANNI       = 14     # copertura dataset incidenti: 2010-2023

SP_TARGET = {'46', '349', '350'}

ROOT     = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "dataset" / "Incidenti_Comuni_ProVI_2010-2023.csv"
GPKG_SP  = ROOT / "data" / "dataset" / "extracted" / "sp_osm" / "SP OSM 6707.gpkg"
DSN      = "host=localhost port=5433 dbname=geosentinel user=postgres password=postgres"


def nome_strada_da_sp(sp: str) -> str:
    s = sp.lower()
    if s.startswith('46'):
        if 'racc' in s:
            return 'SP 046 rac Pasubio Raccordo del Sole'
        if 'torrebelvicino' in s:
            return 'SP 046 var Torrebelvicino'
        return 'SP 046 Pasubio'
    if s.startswith('349'):
        if 'var' in s:
            return 'SP 349 var Costo Variante'
        return 'SP 349 Costo'
    return "SP 350 Val d'Astico"


def costruisci_segmenti() -> gpd.GeoDataFrame:
    """Unisce gli archi di ogni corridoio e li taglia in chunk da SEG_LEN_M."""
    rete = gpd.read_file(GPKG_SP)  # EPSG:6707, metri
    rete['sp_base'] = rete['SP'].astype(str).str.extract(r'^(\d+)')[0]
    corridoi = rete[rete['sp_base'].isin(SP_TARGET)].copy()
    corridoi['nome_strada'] = corridoi['SP'].astype(str).map(nome_strada_da_sp)

    righe = []
    for nome, grp in corridoi.groupby('nome_strada'):
        merged = linemerge(shapely.union_all(grp.geometry.values))
        parti = list(merged.geoms) if merged.geom_type == 'MultiLineString' else [merged]
        km_idx = 0
        for parte in parti:
            pos = 0.0
            while pos < parte.length:
                fine = min(pos + SEG_LEN_M, parte.length)
                seg = substring(parte, pos, fine)
                # scarta i moncherini sotto i 100 m (rumore del grafo)
                if seg.length >= 100:
                    righe.append({
                        'nome_strada': nome,
                        'km_idx': km_idx,
                        'lunghezza_m': round(seg.length),
                        'geometry': seg,
                    })
                    km_idx += 1
                pos = fine

    return gpd.GeoDataFrame(righe, crs=rete.crs)


def assegna_incidenti(segmenti: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    df = pd.read_csv(CSV_PATH, sep=';', encoding='utf-8-sig')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df = df.dropna(subset=['lon', 'lat'])
    inc = gpd.GeoDataFrame(
        df[['tot_morti', 'tot_feriti']].astype(int),
        geometry=gpd.points_from_xy(df['lon'], df['lat']), crs=4326,
    ).to_crs(segmenti.crs)

    seg_geo = segmenti[['geometry']].copy()
    join = gpd.sjoin_nearest(inc, seg_geo, how='inner', max_distance=MAX_DIST_M,
                             distance_col='dist_m')
    # un incidente equidistante da 2 segmenti comparirebbe 2 volte: tieni il più vicino
    join = join.sort_values('dist_m').groupby(level=0).head(1)
    print(f"Incidenti assegnati: {len(join)}/{len(inc)} (entro {MAX_DIST_M} m)")

    join['solo_danni'] = ((join['tot_morti'] == 0) & (join['tot_feriti'] == 0)).astype(int)
    agg = join.groupby('index_right').agg(
        n_incidenti=('tot_morti', 'size'),
        tot_morti=('tot_morti', 'sum'),
        tot_feriti=('tot_feriti', 'sum'),
        n_solo_danni=('solo_danni', 'sum'),
    )

    out = segmenti.join(agg)
    for c in ['n_incidenti', 'tot_morti', 'tot_feriti', 'n_solo_danni']:
        out[c] = out[c].fillna(0).astype(int)
    return out


def calcola_indice(seg: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Indice 0-100: gravità pesata, normalizzata per km e per anno, scalata sul max."""
    grezzo = (
        PESO_MORTO * seg['tot_morti']
        + PESO_FERITO * seg['tot_feriti']
        + PESO_DANNI * seg['n_solo_danni']
    ) / (seg['lunghezza_m'] / 1000.0) / ANNI
    seg['indice_grezzo'] = grezzo.round(3)
    seg['indice'] = (100 * grezzo / grezzo.max()).round(1)
    return seg


STYLE = {
    "paint": {
        "line-color": [
            "interpolate", ["linear"], ["get", "indice"],
            0, "#2f9e44", 15, "#ffd43b", 40, "#f76707", 70, "#c92a2a",
        ],
        "line-width": ["interpolate", ["linear"], ["zoom"], 8, 2.5, 12, 6, 15, 10],
        "line-opacity": 0.85,
    },
    "filters": ["nome_strada"],
    "legend": [
        {"label": "Basso (0)", "color": "#2f9e44"},
        {"label": "Medio (15)", "color": "#ffd43b"},
        {"label": "Alto (40)", "color": "#f76707"},
        {"label": "Critico (70+)", "color": "#c92a2a"},
    ],
}


def scrivi_db(seg: gpd.GeoDataFrame):
    seg4326 = seg.to_crs(4326)
    wkb = shapely.to_wkb(shapely.set_srid(seg4326.geometry.values, 4326),
                         hex=True, include_srid=True)

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS data.segment_risk CASCADE")
            cur.execute("DROP TABLE IF EXISTS data.road_segments CASCADE")
            cur.execute("""CREATE TABLE data.road_segments (
                id            bigserial PRIMARY KEY,
                geom          geometry(LineString, 4326) NOT NULL,
                nome_strada   text NOT NULL,
                km_idx        int  NOT NULL,
                lunghezza_m   int  NOT NULL,
                n_incidenti   int  NOT NULL,
                tot_morti     int  NOT NULL,
                tot_feriti    int  NOT NULL,
                n_solo_danni  int  NOT NULL,
                indice_grezzo real NOT NULL,
                indice        real NOT NULL
            )""")
            cols = ('geom', 'nome_strada', 'km_idx', 'lunghezza_m', 'n_incidenti',
                    'tot_morti', 'tot_feriti', 'n_solo_danni', 'indice_grezzo', 'indice')
            with cur.copy(f"COPY data.road_segments ({', '.join(cols)}) FROM STDIN") as cp:
                for g, r in zip(wkb, seg4326[list(cols[1:])].itertuples(index=False, name=None)):
                    cp.write_row((g, *r))
            cur.execute("CREATE INDEX road_segments_geom_gist ON data.road_segments USING GIST (geom)")

            # Step 2 — contratto per il modello predittivo: una riga per
            # segmento × scenario. Il team ML la riempie con le predizioni.
            cur.execute("""CREATE TABLE data.segment_risk (
                segment_id    bigint NOT NULL REFERENCES data.road_segments(id),
                meteo         text   NOT NULL,
                fascia_oraria text   NOT NULL,
                risk          real   NOT NULL CHECK (risk >= 0 AND risk <= 1),
                PRIMARY KEY (segment_id, meteo, fascia_oraria)
            )""")
            cur.execute("ANALYZE data.road_segments")

        minx, miny, maxx, maxy = seg4326.total_bounds
        cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
        n_seg = len(seg4326)
        descr = (
            f"Risk engine (storico): i corridoi SP 46 / SP 349 / SP 350 divisi in {n_seg} "
            f"segmenti da ~1 km. Colore = indice di pericolosità 0-100 calcolato dagli "
            f"incidenti 2010-2023 (morti x{PESO_MORTO:.0f}, feriti x{PESO_FERITO:.0f}, "
            f"solo danni x{PESO_DANNI:.0f}, normalizzato per km e per anno). "
            f"Clicca un segmento per i dettagli."
        )
        with conn.cursor() as cur:
            cur.execute("DELETE FROM public.layers WHERE slug = 'rischio-storico'")
            cur.execute(
                """INSERT INTO public.layers
                     (slug, title, description, kind, geom_type, source_table,
                      bbox, default_center, default_zoom, style, tags, source_url)
                   VALUES (%s,%s,%s,'vector','line','road_segments',
                           ST_MakeEnvelope(%s,%s,%s,%s,4326),
                           ST_SetSRID(ST_MakePoint(%s,%s),4326),
                           11, %s::jsonb, %s, 'https://enclod.dihvicenza.it/')""",
                ("rischio-storico", "Risk engine — Indice storico per km", descr,
                 minx, miny, maxx, maxy, cx, cy,
                 json.dumps(STYLE), ["vicenza", "rischio", "ml", "vector"]),
            )
        conn.commit()
    print(f"OK: {len(seg)} segmenti -> data.road_segments + layer 'rischio-storico'")
    print("Creata data.segment_risk (vuota) per lo scoring del modello (step 2).")


def main():
    seg = costruisci_segmenti()
    print(f"Segmenti generati: {len(seg)} "
          f"({seg['lunghezza_m'].sum() / 1000:.0f} km totali)")
    seg = assegna_incidenti(seg)
    seg = calcola_indice(seg)
    top = seg.nlargest(5, 'indice')[['nome_strada', 'km_idx', 'n_incidenti',
                                     'tot_morti', 'tot_feriti', 'indice']]
    print("\nTop 5 segmenti più pericolosi:")
    print(top.to_string(index=False))
    scrivi_db(seg)
    print("\nOra: cd work/map && docker compose restart martin")


if __name__ == "__main__":
    main()
