# SPEC — Road Condition Intelligence (prodotto finale)

Sfida primaria 1.2 (supporto al decision making PA) + secondaria 1.1 (sicurezza utente).
Prodotto: **dashboard web** (già su, `work/map`) con due tool sopra gli stessi dati.

Stato: ✅ fatto · 🔶 parziale · ⬜ da fare

## A. Tool analitico (dato passato)

| ID | Requisito | Criterio di accettazione | Stato |
|----|-----------|--------------------------|-------|
| A1 | Mappa interattiva | layer toggleabili, popup al clic, filtri | ✅ |
| A2 | Indice di incidente per tratto stradale | 179 segmenti km colorati 0-100, clic → dettagli | ✅ |
| A3 | Analisi fattori di rischio | feature importance / SHAP del modello visibili in dashboard (immagine o tabella nella pagina MVP) | ⬜ |
| A4 | Analisi cause associate | distribuzione `natura` (tamponamento, fuoriuscita…) per segmento/strada nel popup o in pagina dedicata | ⬜ |
| A5 | Elementi sicurezza ∩ strade di interesse | per ogni segmento: n. attraversamenti, semafori, stop, incroci, autovelox, lampioni entro ~50 m → nel popup del segmento e come feature del modello | ⬜ |
| A6 | Priorità di manutenzione | elenco segmenti ordinati per `indice`/`indice_grezzo`, raggruppabile per comune e per strada; pagina dedicata `/priorita` con tabella | ⬜ |

## B. Tool predittivo (dato futuro)

| ID | Requisito | Criterio di accettazione | Stato |
|----|-----------|--------------------------|-------|
| B1 | Modello predittivo integrato | il DecisionTree del notebook scora i 179 segmenti × scenario → `data.segment_risk`; mappa colorabile per scenario (meteo/fascia) | 🔶 (tabella e contratto pronti, scoring da fare) |
| B2 | Predizione con meteo reale | scelta una data (es. 10/10/2025), il sistema legge il meteo osservato dalle stazioni ARPAV (CSV da ott 2025), lo mappa su {Sereno, Pioggia, …} e mostra l'indice predetto per segmento | ⬜ |
| B3 | Valutazione effetto misura (what-if) | selezionando una misura (es. +illuminazione, autovelox) su un segmento si vede la variazione dell'indice predetto. **Richiede il retrain con le feature A5** | ⬜ |
| B4 | Misure suggerite | per i top-N segmenti, misura con il delta migliore (deriva da B3) | ⬜ |

## C. Requisiti UI (dal documento sfida)

| ID | Requisito | Stato |
|----|-----------|-------|
| C1 | Layer strade acceso di default | ✅ |
| C2 | "incidenti vs strade sicure" (training-incidenti) NON visibile nel prodotto finale | ⬜ togliere dal MVP (resta in Explorer/Catalog per uso interno) |
| C3 | Filtri incidenti più user-friendly | ⬜ etichette mesi/giorni leggibili, ordina valori, layout compatto |

## Contratti di integrazione (piattaforma ⇄ modello)

1. **`work/output/segment_features.csv`** (produce: piattaforma → consuma: Daghem)
   una riga per segmento: `segment_id, nome_strada, comune, lunghezza_m, n_attraversamenti,
   n_semafori, n_stop, n_incroci, n_autovelox, n_lampioni, maxspeed_med, indice_storico`
2. **`work/output/training_arricchito.csv`** (produce: piattaforma)
   training attuale (738+2200) + join spaziale con le feature di segmento → per il retrain B3.
3. **`data.segment_risk`** (produce: Daghem → consuma: piattaforma)
   `(segment_id, meteo, fascia_oraria, risk∈[0,1])` — PK composta, ~4.300 righe.
   Riempimento anche via CSV `work/output/segment_risk.csv` se il DB non è raggiungibile
   (la piattaforma ha lo script di load).
4. **`work/output/feature_importance.json`** (produce: Daghem)
   `[{feature, importance}]` ordinato — la dashboard lo rende come grafico (A3).

## Vincolo noto da dichiarare nel pitch
Niente dati di traffico (AADT) → l'output è un **indice di pericolosità relativo**,
non probabilità per veicolo. Punto di forza compensativo: spiegabilità (SHAP) e
what-if sulle misure = esattamente "supporto al decision making".
