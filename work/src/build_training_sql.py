#!/usr/bin/env python3
"""Genera il seed SQL del layer "dataset di training" per la piattaforma mappa.

Legge work/output/training_dataset.csv (incidenti reali con incidente=1 + negativi
sintetici con incidente=0, tutti geolocalizzati) e produce il seed che crea
data.training_points e registra il layer in public.layers, colorato per `esito`
(incidente vs sicuro) e filtrabile.

Output: work/map/infra/postgres/03-training.sql
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "work" / "output" / "training_dataset.csv"
OUT_PATH = ROOT / "work" / "map" / "infra" / "postgres" / "03-training.sql"


def q(val) -> str:
    if val is None:
        return "NULL"
    s = str(val).strip()
    if s == "":
        return "NULL"
    return "'" + s.replace("'", "''") + "'"


def to_int(val) -> int:
    try:
        return int(float(str(val).strip().replace("*", "")))
    except (ValueError, TypeError):
        return 0


def to_float(val):
    try:
        return float(str(val).strip())
    except (ValueError, TypeError):
        return None


STYLE = {
    "paint": {
        "circle-color": [
            "match", ["get", "esito"],
            "incidente", "#dc2626",
            "sicuro", "#16a34a",
            "#9ca3af",
        ],
        "circle-radius": [
            "interpolate", ["linear"], ["zoom"], 8, 3, 12, 5, 15, 8
        ],
        "circle-stroke-width": 0.6,
        "circle-stroke-color": "#ffffff",
        "circle-opacity": 0.6,
    },
    "filters": ["esito", "comune", "fascia_oraria", "meteo", "fondo"],
    "legend": [
        {"label": "Incidente (reale)", "color": "#dc2626"},
        {"label": "Sicuro (sintetico)", "color": "#16a34a"},
    ],
}


def main() -> None:
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            lon = to_float(r.get("lon"))
            lat = to_float(r.get("lat"))
            if lon is None or lat is None:
                continue
            inc = to_int(r.get("incidente"))
            rows.append({
                "lon": lon, "lat": lat,
                "mese": to_int(r.get("mese")),
                "giorno_settimana": r.get("giorno_settimana"),
                "fascia_oraria": r.get("fascia_oraria"),
                "comune": r.get("comune"),
                "nome_strada": r.get("nome_strada"),
                "tipo_luogo": r.get("tipo_luogo"),
                "kmt_etm": to_float(r.get("kmt_etm")),
                "fondo": r.get("fondo"),
                "segnaletica": r.get("segnaletica"),
                "meteo": r.get("meteo"),
                "incidente": inc,
                "esito": "incidente" if inc == 1 else "sicuro",
            })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    n_pos = sum(1 for r in rows if r["incidente"] == 1)
    n_neg = len(rows) - n_pos
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        w = out.write
        w("-- Generato da work/src/build_training_sql.py — NON modificare a mano.\n")
        w(f"-- Dataset di training: {n_pos} incidenti reali + {n_neg} negativi sintetici.\n\n")
        w("DROP TABLE IF EXISTS data.training_points CASCADE;\n")
        w("""CREATE TABLE data.training_points (
  id               bigserial PRIMARY KEY,
  geom             geometry(Point, 4326) NOT NULL,
  mese             smallint,
  giorno_settimana text,
  fascia_oraria    text,
  comune           text,
  nome_strada      text,
  tipo_luogo       text,
  kmt_etm          real,
  fondo            text,
  segnaletica      text,
  meteo            text,
  incidente        smallint NOT NULL,
  esito            text NOT NULL
);\n\n""")

        cols = ("geom", "mese", "giorno_settimana", "fascia_oraria", "comune", "nome_strada",
                "tipo_luogo", "kmt_etm", "fondo", "segnaletica", "meteo", "incidente", "esito")
        w(f"INSERT INTO data.training_points ({', '.join(cols)}) VALUES\n")
        vals = []
        for r in rows:
            geom = f"ST_SetSRID(ST_MakePoint({r['lon']}, {r['lat']}), 4326)"
            kmt = "NULL" if r["kmt_etm"] is None else r["kmt_etm"]
            vals.append(
                f"({geom}, {r['mese']}, {q(r['giorno_settimana'])}, {q(r['fascia_oraria'])}, "
                f"{q(r['comune'])}, {q(r['nome_strada'])}, {q(r['tipo_luogo'])}, {kmt}, "
                f"{q(r['fondo'])}, {q(r['segnaletica'])}, {q(r['meteo'])}, {r['incidente']}, {q(r['esito'])})"
            )
        w(",\n".join(vals) + ";\n\n")

        w("CREATE INDEX training_geom_gist   ON data.training_points USING GIST (geom);\n")
        w("CREATE INDEX training_esito_idx   ON data.training_points (esito);\n")
        w("CREATE INDEX training_comune_idx  ON data.training_points (comune);\n\n")

        lons = [r["lon"] for r in rows]
        lats = [r["lat"] for r in rows]
        cx, cy = sum(lons) / len(lons), sum(lats) / len(lats)
        style_json = json.dumps(STYLE).replace("'", "''")
        w("DELETE FROM public.layers WHERE slug = 'training-incidenti';\n")
        w(f"""INSERT INTO public.layers (
  slug, title, description, kind, geom_type, source_table,
  bbox, default_center, default_zoom, style, tags, source_url
) VALUES (
  'training-incidenti',
  'Dataset di training — incidenti vs strade sicure',
  'Dataset per il modello predittivo: {n_pos} incidenti reali (rosso) e {n_neg} record di controllo sintetici "strada sicura" (verde), ancorati alle stesse posizioni reali ma con condizioni spazio-temporali diverse. Filtra per esito, comune, fascia oraria, meteo e fondo per esplorare i pattern.',
  'vector',
  'point',
  'training_points',
  ST_MakeEnvelope({min(lons)}, {min(lats)}, {max(lons)}, {max(lats)}, 4326)::geometry(Polygon, 4326),
  ST_SetSRID(ST_MakePoint({cx:.5f}, {cy:.5f}), 4326)::geometry(Point, 4326),
  10,
  '{style_json}'::jsonb,
  ARRAY['vicenza', 'training', 'ml', 'incidenti', 'vector'],
  'https://enclod.dihvicenza.it/'
);\n""")

    print(f"OK: {len(rows)} punti ({n_pos} incidenti / {n_neg} sicuri) -> {OUT_PATH}")


if __name__ == "__main__":
    main()
