# Risk engine — segmenti chilometrici

Obiettivo: cliccare un pezzo di strada (chunk da ~1 km) e leggere l'indice di
pericolosità, sia storico (dato passato) sia predittivo (modello, dato futuro).

## Step 1 — indice storico (fatto)

`work/src/build_road_segments.py` taglia i corridoi SP 46 / SP 349 / SP 350 in
**179 segmenti da ~1 km** (144 km totali, geometria reale dal grafo "SP OSM 6707")
e assegna ogni incidente 2010-2023 al segmento più vicino (entro 300 m; 702/738
assegnati, i restanti hanno coordinate lontane dal corridoio).

Indice storico 0-100 per segmento:

```
indice_grezzo = (morti×10 + feriti×3 + solo_danni×1) / km / 14_anni
indice        = 100 × indice_grezzo / max(indice_grezzo)
```

I pesi sono costanti in cima allo script (`PESO_MORTO`, `PESO_FERITO`,
`PESO_DANNI`): cambiarli sposta quali segmenti diventano rossi. Da tarare
insieme — è una scelta di dominio, non tecnica.

Risultato in mappa: layer **`rischio-storico`** (verde→rosso), clic sul
segmento → popup con n. incidenti, morti, feriti, indice. Top 3 attuale:
SP 046 Pasubio km 50 (indice 100), SP 046 km 35 (62), SP 349 Costo km 59 (39).

## Step 2 — scoring del modello (contratto per il team ML)

Tabella già creata in PostGIS (`docker compose` su, porta 5433, db `geosentinel`):

```sql
CREATE TABLE data.segment_risk (
  segment_id    bigint REFERENCES data.road_segments(id),
  meteo         text,    -- 'Sereno','Pioggia','Nebbia','Neve','Vento forte','Altro'
  fascia_oraria text,    -- valori del dataset incidenti ('Mattina','Pomeriggio','Sera','Notte')
  risk          real,    -- probabilità/score del modello in [0,1]
  PRIMARY KEY (segment_id, meteo, fascia_oraria)
);
```

Come riempirla: per ogni riga di `data.road_segments` (id, centroide del
segmento → lon/lat, nome_strada, comune ricavabile) × ogni combinazione
meteo × fascia_oraria, chiamare `model.predict_proba(...)` e inserire lo score.
~179 segmenti × 6 meteo × 4 fasce ≈ **4.300 predizioni**, batch da pochi secondi.

Feature del modello disponibili per segmento: lon/lat (centroide), nome_strada;
mese/giorno_settimana si possono fissare a valori tipici o aggiungere come
dimensioni extra dello scenario (la PK va estesa di conseguenza).

Quando la tabella è piena, il frontend aggiunge i selettori di scenario sul
layer e colora i segmenti con `risk` invece di `indice` (passaggio rapido).

## Limite noto (per il pitch)

Senza dati di traffico (AADT, non presenti negli open data della challenge)
l'indice misura la **densità di danno**, non il rischio per veicolo: va
presentato come "indice di pericolosità", non come probabilità individuale.
