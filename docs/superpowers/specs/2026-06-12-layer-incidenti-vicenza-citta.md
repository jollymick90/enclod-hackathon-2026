# Spec — Layer "Incidenti Vicenza città" (2011–2020)

Data: 2026-06-12 · Stato: proposto
Riferimento prodotto: `docs/sfida-scelta.md`; dataset segnati in `data/ulteriore_fonte_dati.md`

## Obiettivo

Pubblicare sulla piattaforma mappa i **4.475 incidenti geocodificati del comune di
Vicenza (2011–2020)** come nuovo layer vettoriale. Non entra nel modello (contesto
urbano, fuori dai 3 corridoi SP): serve alla **narrazione del pitch** — "dove un
comune pubblica dati granulari, la piattaforma copre subito quel territorio senza
cambiare una riga di codice" — e a dimostrare la scalabilità del catalogo layer.

## Sorgente

`data/dataset/opendata_incidenti_comune_vicenza/opendata_incidenti_comune_vicenza.shp`
(EPSG:4326, 4.475 punti). Colonne: `GIORNO, MESE, ANNO, VIA1, VIA2, CIVICO,
NATURA_INC, NUMERO_VEI, FERITI, MORTI, cod_istat, geometry`.
Totali di controllo: 57 morti, 5.779 feriti; anni 2011–2020 (303–510 incidenti/anno).

## Approccio (pattern seed esistente)

Nuovo script **`work/src/build_vicenza_citta_sql.py`**, gemello di
`build_accidents_sql.py`: legge lo shapefile con geopandas e genera il seed
**`work/map/infra/postgres/04-vicenza-citta.sql`** (eseguito al primo boot; per lo
stack già attivo si applica con `psql` su `localhost:5433/geosentinel` e poi
`docker compose restart martin`). Il seed NON va editato a mano (stessa regola di
02 e 03).

### Tabella `data.incidenti_vicenza_citta`

```sql
id          serial PRIMARY KEY,
anno        int  NOT NULL,
mese        int  NOT NULL,
giorno      int,
via         text,            -- VIA1 senza il prefisso numerico ("8220 VIALE..." → "VIALE...")
via_incrocio text,           -- VIA2, stessa pulizia
natura      text,            -- NATURA_INC
n_veicoli   int,
feriti      int  NOT NULL,
morti       int  NOT NULL,
gravita     text NOT NULL,   -- derivata: 'mortale' | 'feriti' | 'solo danni'
geom        geometry(Point, 4326) NOT NULL
```

`gravita` usa la stessa classificazione del layer `incidenti-vicenza`
(morti>0 → mortale; feriti>0 → feriti; altrimenti solo danni) così palette e
legenda restano coerenti tra i due layer.

Validazioni nello script (righe scartate → conteggio a log, non errore):
geometria nulla o fuori dal bbox della provincia; `ANNO` fuori 2011–2020.

### Riga in `public.layers`

- slug `incidenti-vicenza-citta`, kind `vector`, geom_type `point`,
  source_table `incidenti_vicenza_citta`.
- title: "Incidenti stradali — Comune di Vicenza (2011–2020)".
- description: citare i 4.475 punti, la fonte (open data Comune di Vicenza) e che
  il dato è **fuori dal perimetro del modello predittivo** (contesto urbano).
- `style`: riusare paint/`legend` del layer `incidenti-vicenza` (colore per
  `gravita`, raggio per `feriti`); `filters` su `anno`, `gravita`, `natura`.
- `default_center`: centro di Vicenza città; `default_zoom` ~12; bbox dal dato.

## Coordinamento col lavoro UI in corso

**Nessun file di `work/map/web` viene toccato.** Il layer è solo DB + catalogo:
appare da solo nel catalogo `/` e in `/layers/incidenti-vicenza-citta` tramite
`LayerMap.svelte`. Chi sta rifacendo la UI decide poi se e dove richiamarlo
(candidato naturale: pagina `/analisi` o slide del pitch). Zero conflitti git
(file nuovi: 1 script, 1 seed generato).

## Verifica

1. `SELECT count(*) FROM data.incidenti_vicenza_citta` = 4.475 (meno gli scarti
   dichiarati a log dallo script).
2. Somme di controllo: `sum(morti)=57`, `sum(feriti)=5779`.
3. Dopo `docker compose restart martin`: tile servite per la nuova tabella.
4. `http://localhost:3030/layers/incidenti-vicenza-citta` renderizza punti,
   filtri `anno`/`gravita`/`natura` funzionanti, legenda coerente col layer
   incidenti provinciale.
5. Riavvio da zero (`down -v` + `up`) ricarica il layer dal seed 04 — da provare
   solo se c'è tempo: distrugge anche i layer OSM (vanno reimportati).

## Fuori scope

- Uso di questi punti nel training o nello scoring (domain shift urbano: si
  dichiara nel pitch come "lavoro futuro").
- Geocoding dei CSV per-comune boxxapps (1–19 righe, senza coordinate, in gran
  parte fuori provincia): non pubblicabili come layer sensato.
- "Termometro completezza open data" (incrocio portale regionale × open data
  comunali): eventuale spec separata, è un widget/slide, non un layer.
