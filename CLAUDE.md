# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Contesto

Repo per l'**ENCLOD Open Data Hackathon** (Vicenza, 12–13 giugno 2026), Challenge 01
"Road Condition Intelligence": indice di pericolosità storico + predittivo per i
corridoi provinciali SP 46 Pasubio, SP 349 Costo, SP 350 Val d'Astico.

- Tutto il repo (docs, commenti, commit) è in **italiano** — mantieni la lingua.
- Il codice soluzione vive in `work/` e per regolamento (Art. 6.6) deve nascere
  durante l'evento.
- Il documento canonico è **`docs/sfida-scelta.md`**: sfide scelte (1.2 primaria,
  1.1 secondaria) e la sezione "Descrizione" con la traccia di soluzione committata
  (dashboard: tool analitico + tool predittivo meteo + piano manutenzioni + dashboard
  cittadino).
- Tutto il resto della vecchia documentazione (strategia, spec A1–C3, plan, risk
  engine…) è in `docs/_deprecated/` — consultabile come storico ma non più
  vincolante. I contratti di integrazione piattaforma ⇄ modello descritti in
  `_deprecated/08-spec.md` restano però quelli implementati dagli script.

## Ambiente

- Python: venv in `.venv/` (python3.14 homebrew). Esegui sempre con
  **`.venv/bin/python3.14`** (pandas, geopandas, folium, scikit-learn, psycopg…).
- Frontend: SvelteKit 2 + Svelte 5 + Tailwind 4 + MapLibre, pnpm, in `work/map/web/`.
  Type-check: `pnpm check`. Non ci sono test automatici nel repo.

## Piattaforma mappa (`work/map/`)

Stack Docker Compose: SvelteKit (web, porta **3030**) + Martin vector tiles
(porta **3010**) + PostgreSQL 16/PostGIS (porta **5433**, db `geosentinel`,
user/password `postgres`).

```bash
cd work/map
docker compose up -d --build      # apri http://localhost:3030
docker compose down -v            # reset totale (riesegue i seed al boot)
```

- Al primo boot il DB esegue in ordine `infra/postgres/01-init.sql` (schema `data` +
  catalogo `public.layers`), `02-accidents.sql`, `03-training.sql`. I seed 02 e 03 sono
  **generati** da `work/src/build_accidents_sql.py` e `build_training_sql.py` — non
  editarli a mano.
- **Gotcha Martin**: scopre le tabelle dello schema `data` solo all'avvio. Dopo aver
  aggiunto/ricaricato una tabella: `docker compose restart martin`.
- I layer OSM (`data.osm_*`) NON sono nei seed: dopo un `down -v` vanno reimportati
  con `import_osm_layers.py` (vedi pipeline sotto).
- Per aggiungere un layer: tabella `data.<nome>` con colonna `geom geometry(...,4326)`
  + riga in `public.layers`; il campo `style` jsonb accetta `paint` MapLibre più due
  chiavi meta `filters` e `legend`, lette da `LayerMap.svelte`. Poi restart di Martin.
- Pagine principali: `/` (catalogo), `/mvp` (prodotto finale), `/priorita`
  (classifica segmenti), `/explorer`, `/layers/<slug>`.

## Pipeline dati (`work/src/`, in ordine di dipendenza)

Tutti gli script usano il DSN hardcoded `localhost:5433 / geosentinel` — lo stack
deve essere su. Dopo ogni script che tocca tabelle `data.*`: restart di Martin.

1. `generate_training_data.py` → `work/output/training_dataset.csv` +
   `training_report.html` (mappa folium di validazione visiva). Genera i 2200 negativi
   sintetici campionati LUNGO la geometria reale dei 3 corridoi (grafo "SP OSM 6707").
   Vincolo: i negativi devono stare su strade provinciali, non comunali.
2. `build_accidents_sql.py` / `build_training_sql.py` → rigenerano i seed SQL in
   `work/map/infra/postgres/`.
3. `build_road_segments.py` → taglia i corridoi in **179 segmenti da ~1 km** con
   indice storico 0–100 (`data.road_segments`, layer `rischio-storico`) e crea la
   tabella-contratto vuota `data.segment_risk`. I pesi morti/feriti/danni sono
   costanti in cima allo script: scelta di dominio, da tarare insieme all'utente.
4. `import_osm_layers.py` → ritaglia gli shapefile Geofabrik sulla provincia di
   Vicenza e scrive `data.osm_*` via COPY (`--list`, `--only roads,buildings`).
5. `build_segment_features.py` → feature infrastrutturali per segmento (conteggi
   `osm_traffic` entro 50 m) → aggiorna `data.road_segments` e produce i contratti
   `segment_features.csv` + `training_arricchito.csv` per il team ML.
6. `score_segments.py` → replica il DecisionTree di
   `work/notebooks/previsione_incidenti.ipynb` (stesso seed/split) e scora ogni
   segmento × scenario (meteo × fascia oraria) con marginalizzazione Monte Carlo →
   `segment_risk.csv`.
7. `load_segment_risk.py [csv]` → valida e carica le predizioni in `data.segment_risk`.

## Vincoli noti sui dati (da non riscoprire)

- Il CSV incidenti (`Incidenti_Comuni_ProVI_2010-2023.csv`, 738 righe) copre SOLO i
  3 corridoi SP — la challenge è deliberatamente scopata lì.
- `kmt_etm` è 0 in 601/738 righe: inutilizzabile, escluso dalle feature.
- I CSV meteo ARPAV partono da ottobre 2025: non coprono il periodo incidenti
  2010–2023 (limite da dichiarare nel pitch).
- Grafo stradale e confini: zip in `data/`, estratti in
  `data/dataset/extracted/{sp_osm,comuni}/` (SP OSM in EPSG:6707 metri, comuni in
  EPSG:3003).
- I negativi sintetici riusano coordinate lungo gli stessi corridoi dei positivi: in
  mappa si sovrappongono, si separano col filtro `esito`.
