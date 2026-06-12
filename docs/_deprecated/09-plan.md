# PLAN — chiusura sfida (riferimenti: docs/08-spec.md)

Due binari paralleli che si incrociano su contratti file/tabella già definiti:
nessuno dei due si blocca mai aspettando l'altro.

## Binario 1 — Piattaforma (Michele + Claude)

### P0 — da fare subito (sbloccano Daghem e chiudono i requisiti UI)
1. **[C2]** Togliere `training-incidenti` dai default del MVP (resta in Explorer).
2. **[A5]** Script `build_segment_features.py`: join spaziale `osm_traffic` (+maxspeed
   da `osm_roads`) sui 179 segmenti → colonna conteggi in `data.road_segments`,
   popup arricchito, e **output `segment_features.csv` + `training_arricchito.csv`
   per Daghem** ← consegna prioritaria.
3. **[A6]** Pagina `/priorita`: tabella segmenti ordinata per indice, filtro/raggruppa
   per comune e strada, link "vedi su mappa". Dati già in `data.road_segments`.

### P1 — appena Daghem consegna
4. **[B1]** Script `load_segment_risk.py` (CSV → tabella) + selettore scenario sul MVP
   (select meteo + fascia → colora i segmenti con `risk`).
5. **[A3]** Card "Fattori di rischio" nel MVP da `feature_importance.json` (+ SHAP png).
6. **[B2]** `meteo_per_data.py`: data → stazione più vicina al segmento → categorie
   meteo → scenario; nel MVP un date-picker che imposta lo scenario.

### P2 — se c'è tempo (effetto wow)
7. **[B3/B4]** What-if: toggle "aggiungi illuminazione/autovelox" su un segmento →
   re-score client-side o endpoint → delta indice. Richiede modello v2 di Daghem.
8. **[C3]** UX filtri (etichette mesi, ordinamenti, layout).

## Binario 2 — Modello (Daghem) — in ordine di valore

1. **Validazione anti-leakage del modello attuale** (30 min, critica per il pitch):
   - i negativi sintetici hanno `segnaletica`/`tipo_luogo` uniformi, i positivi no →
     verificare con SHAP che il modello non stia classificando "da che distribuzione
     viene la riga". Test: togliere `segnaletica` e `tipo_luogo`, guardare quanto
     cala. Se cala poco → ok; se cala tanto → tenerne conto nel pitch.
   - DecisionTree puro overfitta: confrontare con `RandomForestClassifier` /
     `HistGradientBoostingClassifier` (3 righe) e tenere il migliore su validation.
2. **Batch scoring → `segment_risk.csv`** (sblocca B1, il cuore della demo):
   per ogni segmento (da `segment_features.csv`: nome_strada, comune) × meteo(6) ×
   fascia(4): costruire la riga con le stesse dummy del training, `predict_proba`
   → `risk`. Fissare mese/giorno al valore mediano oppure mediare su 12 mesi.
   ~4.300 predizioni. Attenzione: `pd.get_dummies` deve avere le stesse colonne del
   fit → usare `X.reindex(columns=train_cols, fill_value=0)`.
3. **Modello v2 con feature di segmento** (sblocca il what-if B3):
   retrain su `training_arricchito.csv` (stesse righe + n_semafori, n_attraversamenti,
   illuminazione, maxspeed…). Se le nuove feature hanno importance > 0 → il what-if
   è difendibile. Rigenerare scoring (passo 2) e `feature_importance.json`.
4. **`feature_importance.json` + SHAP summary png** → A3 (5 minuti, alto valore pitch).
5. (Se avanza tempo) `gravita_incidenti`: secondo modello severità → colore/badge
   "se qui succede, quanto è grave" sui segmenti.

## Ordine consigliato delle prossime 3 ore
| # | Chi | Cosa |
|---|-----|------|
| 1 | Claude | P0.2 `segment_features.csv` + `training_arricchito.csv` (sblocca tutto il binario 2) |
| 2 | Daghem | validazione modello (2.1) mentre arriva il punto 1 |
| 3 | Claude | P0.1 + P0.3 (pulizia MVP + pagina priorità) |
| 4 | Daghem | scoring `segment_risk.csv` (2.2) |
| 5 | Claude | P1.4 caricamento + scenario sul MVP → **demo end-to-end completa** |
| 6 | entrambi | v2 + what-if (P2.7 / 2.3) solo se la demo base è solida |

## Story della demo (3 minuti)
1. *Problema*: 738 incidenti, 14 anni, 3 corridoi — la PA dove interviene prima?
2. *Analitico*: mappa → segmento rosso SP 046 km 50 (36 incidenti) → pagina priorità
   per comune = lista interventi pronta.
3. *Predittivo*: cambio meteo a "Pioggia" + fascia "Sera" → la mappa si riconfigura;
   data 10/10/2025 con meteo ARPAV reale.
4. *Decisione*: what-if illuminazione sul km 50 → l'indice scende → costo/beneficio.
5. *Onestà*: limiti (no AADT, 3 corridoi) + scalabilità (pipeline pronta per tutte le SP).
