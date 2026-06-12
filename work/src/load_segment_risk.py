#!/usr/bin/env python3
"""Carica le predizioni del modello (contratto 3, docs/08-spec.md) in data.segment_risk.

Input atteso: work/output/segment_risk.csv con colonne
    segment_id, meteo, fascia_oraria, risk
(risk in [0,1]; una riga per segmento × scenario; separatore ',').

Uso:
    .venv/bin/python3.14 work/src/load_segment_risk.py [path_csv]
"""
import sys
from pathlib import Path

import pandas as pd
import psycopg

ROOT = Path(__file__).resolve().parents[2]
CSV  = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "work" / "output" / "segment_risk.csv"
DSN  = "host=localhost port=5433 dbname=geosentinel user=postgres password=postgres"

REQUIRED = ['segment_id', 'meteo', 'fascia_oraria', 'risk']


def main():
    df = pd.read_csv(CSV)
    mancanti = [c for c in REQUIRED if c not in df.columns]
    if mancanti:
        sys.exit(f"Colonne mancanti in {CSV.name}: {mancanti} (attese: {REQUIRED})")

    fuori = df[(df['risk'] < 0) | (df['risk'] > 1)]
    if len(fuori):
        sys.exit(f"{len(fuori)} righe con risk fuori da [0,1] — controlla lo scoring")

    df = df.drop_duplicates(subset=['segment_id', 'meteo', 'fascia_oraria'])

    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM data.road_segments")
            validi = {r[0] for r in cur.fetchall()}
            orfane = ~df['segment_id'].isin(validi)
            if orfane.any():
                print(f"ATTENZIONE: {orfane.sum()} righe con segment_id inesistente, scartate")
                df = df[~orfane]

            cur.execute("TRUNCATE data.segment_risk")
            with cur.copy(
                "COPY data.segment_risk (segment_id, meteo, fascia_oraria, risk) FROM STDIN"
            ) as cp:
                for r in df[REQUIRED].itertuples(index=False, name=None):
                    cp.write_row(r)
        conn.commit()

        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*), count(DISTINCT segment_id),
                       count(DISTINCT meteo), count(DISTINCT fascia_oraria),
                       round(avg(risk)::numeric, 3)
                FROM data.segment_risk""")
            n, nseg, nmeteo, nfascia, media = cur.fetchone()

    print(f"OK: {n} predizioni caricate "
          f"({nseg} segmenti × {nmeteo} meteo × {nfascia} fasce, risk medio {media})")
    print("Il selettore scenario sul MVP ora ha i dati.")


if __name__ == "__main__":
    main()
