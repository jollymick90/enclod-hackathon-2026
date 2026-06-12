#!/usr/bin/env python3
"""Genera il seed SQL per pubblicare gli incidenti come layer vettoriale su geo-sentinel.

Legge il CSV incidenti (delimiter ';', encoding utf-8-sig) e produce uno script SQL che:
  - crea data.accidents (Point 4326 + attributi + colonna derivata `gravita`)
  - inserisce tutte le righe geolocalizzate
  - crea gli indici
  - registra il layer in public.layers con uno stile data-driven per gravita

Uso:
    python3 work/src/build_accidents_sql.py
Output:
    work/output/accidents_seed.sql
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "data" / "dataset" / "Incidenti_Comuni_ProVI_2010-2023.csv"
OUT_PATH = ROOT / "work" / "map" / "infra" / "postgres" / "02-accidents.sql"


def q(val: str) -> str:
    """Cita una stringa per SQL (raddoppia gli apici), o NULL se vuota."""
    if val is None:
        return "NULL"
    val = val.strip()
    if val == "":
        return "NULL"
    return "'" + val.replace("'", "''") + "'"


def to_int(val: str) -> int:
    val = (val or "").strip().replace("*", "")  # '2023*' -> 2023
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return 0


def gravita(morti: int, feriti: int) -> str:
    if morti > 0:
        return "mortale"
    if feriti > 0:
        return "feriti"
    return "danni"


# Stile del layer. `paint` viene fuso sopra il default circle dal frontend (applyStyle).
# Le chiavi meta `filters` e `legend` NON sono spec MapLibre: il frontend le estrae
# per costruire la barra filtri e la legenda, e non le passa a map.addLayer().
STYLE = {
    "paint": {
        "circle-color": [
            "match", ["get", "gravita"],
            "mortale", "#dc2626",
            "feriti", "#f59e0b",
            "danni", "#9ca3af",
            "#9ca3af",
        ],
        "circle-radius": [
            "interpolate", ["linear"], ["get", "tot_feriti"],
            0, 4, 2, 7, 5, 11, 15, 18,
        ],
        "circle-stroke-width": 1,
        "circle-stroke-color": "#ffffff",
        "circle-opacity": 0.85,
    },
    # Campi su cui il frontend costruisce dei <select> (valori distinti calcolati lato server).
    "filters": ["anno", "mese", "giorno_settimana", "fascia_oraria", "comune", "nome_strada", "natura", "fondo", "meteo", "gravita"],
    "legend": [
        {"label": "Mortale", "color": "#dc2626"},
        {"label": "Con feriti", "color": "#f59e0b"},
        {"label": "Solo danni", "color": "#9ca3af"},
    ],
}


def main() -> None:
    rows = []
    with open(CSV_PATH, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f, delimiter=";")
        for r in reader:
            lon = (r.get("lon") or "").strip()
            lat = (r.get("lat") or "").strip()
            if not lon or not lat or lon in ("0", "0.0"):
                continue  # senza geolocalizzazione non va in mappa
            morti = to_int(r.get("tot_morti"))
            feriti = to_int(r.get("tot_feriti"))
            rows.append({
                "lon": float(lon),
                "lat": float(lat),
                "anno": to_int(r.get("anno")),
                "mese": to_int(r.get("mese")),
                "giorno_settimana": r.get("giorno_settimana"),
                "fascia_oraria": r.get("fascia_oraria"),
                "comune": r.get("comune"),
                "nome_strada": r.get("nome_strada"),
                "natura": r.get("natura"),
                "fondo": r.get("fondo"),
                "meteo": r.get("meteo"),
                "tot_morti": morti,
                "tot_feriti": feriti,
                "gravita": gravita(morti, feriti),
            })

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as out:
        w = out.write
        w("-- Generato da work/src/build_accidents_sql.py — NON modificare a mano.\n")
        w(f"-- Incidenti Provincia di Vicenza 2010-2023 ({len(rows)} righe geolocalizzate).\n\n")
        w("DROP TABLE IF EXISTS data.accidents CASCADE;\n")
        w("""CREATE TABLE data.accidents (
  id               bigserial PRIMARY KEY,
  geom             geometry(Point, 4326) NOT NULL,
  anno             smallint,
  mese             smallint,
  giorno_settimana text,
  fascia_oraria    text,
  comune           text,
  nome_strada      text,
  natura           text,
  fondo            text,
  meteo            text,
  tot_morti        smallint NOT NULL DEFAULT 0,
  tot_feriti       smallint NOT NULL DEFAULT 0,
  gravita          text NOT NULL
);\n\n""")

        cols = ("geom", "anno", "mese", "giorno_settimana", "fascia_oraria", "comune",
                "nome_strada", "natura", "fondo", "meteo", "tot_morti", "tot_feriti", "gravita")
        w(f"INSERT INTO data.accidents ({', '.join(cols)}) VALUES\n")
        values = []
        for r in rows:
            geom = f"ST_SetSRID(ST_MakePoint({r['lon']}, {r['lat']}), 4326)"
            values.append(
                f"({geom}, {r['anno']}, {r['mese']}, {q(r['giorno_settimana'])}, "
                f"{q(r['fascia_oraria'])}, {q(r['comune'])}, {q(r['nome_strada'])}, "
                f"{q(r['natura'])}, {q(r['fondo'])}, {q(r['meteo'])}, "
                f"{r['tot_morti']}, {r['tot_feriti']}, {q(r['gravita'])})"
            )
        w(",\n".join(values) + ";\n\n")

        w("CREATE INDEX accidents_geom_gist ON data.accidents USING GIST (geom);\n")
        w("CREATE INDEX accidents_anno_idx   ON data.accidents (anno);\n")
        w("CREATE INDEX accidents_comune_idx ON data.accidents (comune);\n\n")

        # Centro e bbox sull'Alto Vicentino (dove sono gli incidenti).
        lons = [r["lon"] for r in rows]
        lats = [r["lat"] for r in rows]
        cx, cy = sum(lons) / len(lons), sum(lats) / len(lats)
        style_json = json.dumps(STYLE).replace("'", "''")
        w("DELETE FROM public.layers WHERE slug = 'incidenti-vicenza';\n")
        w(f"""INSERT INTO public.layers (
  slug, title, description, kind, geom_type, source_table,
  bbox, default_center, default_zoom, style, tags, source_url
) VALUES (
  'incidenti-vicenza',
  'Incidenti stradali — Provincia di Vicenza (2010-2023)',
  'Localizzazione dei {len(rows)} incidenti rilevati nella Provincia di Vicenza tra il 2010 e il 2023. Colore per gravita (rosso=mortale, arancio=feriti, grigio=solo danni), raggio per numero di feriti. Fonte: open data enCLOD.',
  'vector',
  'point',
  'accidents',
  ST_MakeEnvelope({min(lons)}, {min(lats)}, {max(lons)}, {max(lats)}, 4326)::geometry(Polygon, 4326),
  ST_SetSRID(ST_MakePoint({cx:.5f}, {cy:.5f}), 4326)::geometry(Point, 4326),
  10,
  '{style_json}'::jsonb,
  ARRAY['vicenza', 'incidenti', 'sicurezza', 'vector'],
  'https://enclod.dihvicenza.it/'
);\n""")

    print(f"OK: {len(rows)} incidenti -> {OUT_PATH}")
    print(f"centro=({cx:.5f},{cy:.5f}) bbox=({min(lons):.4f},{min(lats):.4f},{max(lons):.4f},{max(lats):.4f})")


if __name__ == "__main__":
    main()
