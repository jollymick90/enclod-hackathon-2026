# Design — Layer "Incidenti Vicenza" su geo-sentinel

**Data:** 2026-06-12 · **Contesto:** enCLOD Hackathon, Challenge 01 (Road Condition Intelligence)

## Obiettivo

Visualizzare i 738 incidenti stradali della Provincia di Vicenza (2010–2023) come
layer interattivo su mappa, riusando la piattaforma GIS esistente `geo-sentinel`
(`/Users/jollymick/SProject/geo-sentinel`). Base su cui ragionare per la soluzione
di prioritizzazione manutenzione.

## Nota IP

`geo-sentinel` è una piattaforma di **pubblicazione GIS generica** (SvelteKit +
PostGIS + Martin + TiTiler + MapLibre), non una soluzione road-condition. Rientra
nella toolchain/infrastruttura ("lecito" da regolamento). Il *layer incidenti* e
gli arricchimenti sono costruiti durante l'evento. In caso di dubbio: check con lo staff.

## Architettura (nessuna modifica strutturale)

geo-sentinel auto-pubblica via **Martin** ogni tabella nello schema `data`, e
`LayerMap.svelte` rende i layer vettoriali leggendo una riga da `public.layers`.
Il flusso per aggiungere gli incidenti:

1. **Seed script Python** (`work/src/build_accidents_sql.py`): legge il CSV
   (delimiter `;`, encoding `utf-8-sig`) → genera SQL che:
   - crea `data.accidents` con `geom geometry(Point,4326)` da `lon`/`lat`;
   - colonne attributo: `anno, mese, giorno_settimana, fascia_oraria, comune,
     nome_strada, natura, fondo, meteo, tot_morti, tot_feriti`;
   - colonna derivata `gravita` ∈ {`mortale`, `feriti`, `danni`} (morti>0 →
     mortale; feriti>0 → feriti; else danni);
   - indici GIST su `geom` e btree su `anno`, `comune`.
2. **Catalog row**: `INSERT` in `public.layers` (slug `incidenti-vicenza`,
   kind `vector`, geom `point`, centro Alto Vicentino ~[11.43, 45.72], zoom 10,
   `style` jsonb data-driven per gravità).

## Visualizzazione (scope approvato: layer + popup + filtri)

- **Colore per gravità** via `style` jsonb (data-driven `circle-color`): mortale
  rosso, feriti arancio, danni grigio. Raggio data-driven su `tot_feriti`.
  → nessuna modifica frontend.
- **Popup al click**: aggiunta a `LayerMap.svelte` — su `click` del layer vettoriale,
  mostra data/comune/strada/natura/morti/feriti. Cursore pointer su hover.
- **Filtri** (anno, comune, gravità): pannello controlli sopra la mappa che applica
  `map.setFilter()` sul layer. Le opzioni (anni, comuni) derivano dagli attributi.

## Componenti toccati

| Dove | Cosa | Tipo |
|---|---|---|
| `work/src/build_accidents_sql.py` (hackathon repo) | CSV → SQL seed | nuovo |
| `geo-sentinel` DB | tabella `data.accidents` + riga `public.layers` | seed SQL |
| `geo-sentinel/web/.../LayerMap.svelte` | popup + filtri | modifica |

## Verifica

`docker compose up -d` su geo-sentinel → `http://localhost:3030/layers/incidenti-vicenza`
mostra 738 punti colorati per gravità; click → popup; filtri restringono la mappa.

## Out of scope (per ora)

Scoring di rischio per tratta, snap alla rete stradale (SHP), copilota AI, layer
sensori/meteo. Aggiungibili come layer/feature successivi.
