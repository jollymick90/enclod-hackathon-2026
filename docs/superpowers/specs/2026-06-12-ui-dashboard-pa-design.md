# Design — UI dashboard PA "SaferRoads Vicenza" (3+1 punti)

Data: 2026-06-12 · Stato: approvato a voce, in attesa di review scritta
Riferimento prodotto: `docs/sfida-scelta.md` (sezione "Descrizione")

## Obiettivo

Rifare la UI di `work/map/web` perché risponda ai 3+1 punti della Descrizione
(tool analitico, tool predittivo, piano manutenzioni, dashboard cittadino) con un
pubblico preciso: **decisori PA non tecnici** (politici, oltre ai tecnici). La
domanda tipo — "che rischio c'è sulla strada X con pioggia di notte?" — deve avere
una risposta immediata in linguaggio semplice, con la possibilità di scendere nei
dettagli. La UI attuale (pagine /mvp, /priorita, popup tecnici) si può stravolgere.

## Decisioni prese (con l'utente)

1. **Home = dashboard a riquadri**: indice a 4 card di sezione + numeri chiave
   (layout A dei mockup).
2. **+1 Cittadino funzionante minimale**: form di segnalazione che salva davvero
   in PostGIS e appare su mappa. Mobile-first obbligatorio.
3. **Rischio espresso con livelli verbali + numero**: Basso / Moderato / Alto /
   Critico in primo piano con frase raccontabile; indice 0–100 piccolo e nei
   dettagli. Soglie: `<15 / 15–39 / 40–69 / ≥70` (le stesse dei badge attuali).
   La "frase raccontabile" è generata da template deterministici sui dati (es.
   "tra le {n} tratte più pericolose della provincia con {meteo}", dal ranking
   dell'indice) — nessuna generazione libera.
4. **Drill-down = scheda tratta laterale** (pannello, non pagina dedicata, non
   popup), condivisa tra le sezioni.
5. **Approccio implementativo: shell nuova + riuso componenti mappa**
   (`MultiLayerMap`/`LayerMap`), niente rifacimento da zero.
6. **Shell a viewport pieno**: la UI attuale costringe a scroll continuo; le
   pagine con mappa diventano app a schermo pieno (header fisso, mappa =
   `100dvh − header`, pannelli flottanti). Lo scroll esiste solo dentro i
   pannelli, mai sulla pagina.

## Architettura UI

### Shell (tutte le pagine)

- Header fisso: brand "SaferRoads Vicenza" + nav alle 4 sezioni, sempre visibile.
- Sotto l'header: `flex:1; overflow:hidden` per le pagine-mappa; pagine normali
  (home, priorità) entro l'altezza schermo dove possibile.
- Mobile: nav compatta; la scheda tratta diventa **bottom-sheet** trascinabile
  (pattern Google Maps); i selettori diventano barra compatta.
- Le route esistenti `/mvp`, `/explorer`, `/catalog`, `/layers/*` restano
  raggiungibili ma escono dalla navigazione (uso interno).
- Mai gergo tecnico in superficie: niente "layer", "modello", "feature".

### Route nuove

| Route | Punto | Contenuto |
|---|---|---|
| `/` | indice | 4 card sezione + fascia numeri chiave (738 incidenti 2010–23, 144 km, N tratte critiche dal DB — "critica" = indice storico ≥ 70, cioè livello Critico). Ogni card: titolo piano, KPI vivo, riga di spiegazione. |
| `/analisi` | tool analitico | Mappa viewport pieno: incidenti reali + rischio storico. Filtri rifatti: pannello compatto (anno, meteo, gravità) + "Altri filtri" espandibile; etichette leggibili (mesi a nome, giorni ordinati) — chiude il requisito C3. Clic tratta → scheda. |
| `/previsione` | tool predittivo | Selettore scenario (meteo + fascia) in alto a sx; la mappa si ricolora da `data.segment_risk`. Clic tratta → scheda con livello verbale grande ("● ALTO con pioggia di notte") e frase raccontabile. Ospita il riquadro "Fattori di rischio" (A3) quando esiste `feature_importance.json`. |
| `/priorita` | piano manutenzioni | Tabella ristrutturata gerarchica **Comune → Strada → Tratto**, righe espandibili, badge verbali al posto dell'indice nudo. Colonne tecniche (A/S/V/L, limite) nel dettaglio espanso. "Vedi su mappa" → `/analisi` centrata con scheda aperta. |
| `/cittadino` | +1 | Mobile-first. Mappa pubblica semplificata (solo rischio + segnalazioni, zero filtri tecnici), bottom-sheet di dettaglio, bottone "＋ Segnala un problema". |

### Componente `SchedaTratta` (condiviso)

Dall'alto: nome leggibile ("SP 46 Pasubio — km 50, Torrebelvicino") · livello
verbale a colore + indice piccolo · frase raccontabile · storia 2010–23
(incidenti/morti/feriti) · cause principali (distribuzione `natura`, requisito A4)
· dotazioni di sicurezza presenti (A5) · mini-griglia rischio meteo×fascia ·
link "dettagli tecnici" che espande i dati grezzi. In `/cittadino` versione
ridotta (senza griglia scenari e dati grezzi).

### Form segnalazione (Cittadino)

3 campi: tipo (`incidente_lieve` | `strada_danneggiata` | `pericolo`),
descrizione testuale, posizione (punto toccato su mappa o GPS del dispositivo).
Submit → conferma visiva ("Grazie, la tua segnalazione è sulla mappa") e la
segnalazione appare subito.

## Dati e API

- **Nuova tabella** `data.segnalazioni`: `id serial, tipo text, descrizione text,
  geom geometry(Point,4326), created_at timestamptz default now()` + riga nel
  catalogo `public.layers`; Martin la pubblica dopo restart.
- **`POST /api/segnalazioni`** (SvelteKit): validazione dei 3 campi lato server,
  messaggi in italiano.
- **`GET /api/tratte/[id]`**: aggrega in una risposta l'anagrafica del segmento
  (da `data.road_segments`, che ha già storia e dotazioni), la distribuzione
  cause `natura` (join spaziale `ST_DWithin` 300 m con gli incidenti — stesso
  criterio dello script di build) e la griglia rischio per scenario (da
  `data.segment_risk`, già caricata — commit B1).
- Nessun nuovo script Python: mappe, filtri e classifica usano dati già in PostGIS.

## Gestione errori

- Scenario assente in `segment_risk` → scheda: "previsione non disponibile per
  questo scenario"; mappa in grigio.
- `feature_importance.json` assente → il riquadro Fattori di rischio non si
  renderizza (nessun errore).
- Form segnalazione: errori di validazione inline in italiano; errore DB →
  messaggio generico e segnalazione non persa (i campi restano compilati).

## Verifica

Niente framework di test nel repo: `pnpm check` (svelte-check) + checklist
manuale per pagina su desktop e viewport mobile ≈390 px. Criterio esplicito:
**nessuna pagina con mappa ha scroll verticale di pagina**.

## Ordine di costruzione (ogni passo committabile)

1. Shell (header fisso + layout viewport) + Home a 4 card
2. `/previsione` (riuso mappa + selettore scenario esistente, `SchedaTratta` v1)
3. `/analisi` (filtri rifatti compatti)
4. `/priorita` (ristrutturazione gerarchica)
5. `/cittadino` (tabella + API + pagina mobile-first)
6. Rifinitura mobile delle altre sezioni — solo se avanza tempo

Vincolo di contesto: pitch il 13/06 alle 11:45 — se il tempo stringe si taglia
dalla coda della lista e la demo resta coerente.

## Fuori scope

- Dataset esterno segnato in `data/ulteriore_fonte_dati.md` (da valutare dopo).
- What-if misure (B3/B4 della vecchia spec) — dipende dal modello v2.
- Autenticazione/moderazione delle segnalazioni cittadino (si dichiara nel pitch).
