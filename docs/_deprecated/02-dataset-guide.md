# 02 — Guida ai dataset (checklist di esplorazione)

> ⚠️ I nomi/formati qui sotto vengono da un'analisi preliminare. **Verifica contro
> ciò che hai effettivamente scaricato** dal repository: nomi esatti, anni coperti,
> colonne reali. Capire i dati è ~50% del lavoro ed è l'unica prep davvero ad alto
> rendimento. Annota anche la **licenza** di ogni dataset mentre lo apri (serve poi
> per IP/commercializzazione).

Per ogni dataset, in 5 minuti, rispondi a: *quante righe? quali colonne chiave?
c'è un join geografico possibile (coordinate, ID comune, ID tratta)? copertura
temporale? buchi/NaN evidenti?*

---

## Core per la soluzione (l'MVP gira su questi 3)

### Accident Data Vicenza 2010–2023 — `CSV`
- Cerca: colonne di **localizzazione** (lat/lon? indirizzo? ID strada?), data/ora,
  gravità, tipo incidente.
- Domanda chiave: **come si aggancia alla rete stradale?** (coordinate da snappare
  sul segmento più vicino, o un ID strada già presente?). Questo è il join che
  abilita tutta la prioritizzazione.
- Output utile: conteggio/gravità incidenti **per segmento** → primo fattore di rischio.

### enCLOD Stations Sensor Data — `CSV`
- Cerca: ID stazione, coordinate stazione, timestamp, metriche (flusso? temperatura?
  stato infrastrutturale?).
- Domanda chiave: è **real-time/storico**? Con che frequenza? Quante stazioni e
  dove sono rispetto alle strade?
- Output utile: stato/flusso per zona → secondo fattore.

### Road Network of Province of Vicenza — `SHP`
- È la **spina dorsale geografica**: ogni analisi si appende qui.
- Apri in QGIS al volo per vedere com'è fatto: i segmenti hanno un ID? attributi
  (tipo strada, nome)? CRS dichiarato nel `.prj`?
- Converti in **GeoJSON** per il frontend (geopandas → `to_file(..., driver="GeoJSON")`).
- ⚠️ ricorda i file gemelli (`.shx`, `.dbf`, `.prj`) nella stessa cartella.

---

## Booster ad alto valore

### Salt Spreading Data — `PDF`
- Formato scomodo (PDF). Vale la pena solo se l'estrazione è rapida.
- Obiettivo: dedurre **cicli gelo-disgelo / frequenza interventi** per zona → proxy
  di usura asfalto. Terzo fattore del punteggio.
- Se l'estrazione dal PDF è un incubo, declassalo a "fattore qualitativo" e vai avanti.

### Copernicus Sentinel-1 SAR — `.SAFE` (il differenziatore)
- **Alto rischio / alto rendimento.** Deformazione del suolo vicino alle strade (InSAR).
- NON processare tutto il `.SAFE`: estrai una **slice raster** su un'area ristretta
  o un **indice sintetico**.
- Decidi presto un **time-box** (es. max 3h). Se sfori → fallback, la demo core
  regge senza.

---

## Contesto / arricchimento (usali se avanzano tempo)

### Municipal Boundaries — `SHP`
- Per **aggregare** i risultati a livello comune (utile per il pitch: "il comune X
  ha N tratte prioritarie"). Mascheramento/aggregazione GIS.

### OpenStreetMap NE Italia — `SHP`
- POI, edifici, geometrie. Utile per **contestualizzare** (scuole/ospedali vicino a
  tratte rischiose → priorità sociale) o come basemap.

### ISTAT Census 1995–2011 — `CSV`
- Demografia per sezione. Aggiunge un layer "quante persone impattate" alla priorità.
  Attenzione: dati vecchi (fino 2011).

### Sentinel-2 ottico — `.SAFE`
- Uso del suolo / vegetazione. Probabilmente fuori scope per la 01, salvo idee
  ambientali specifiche.

### ARPAV PFAS — `CSV`
- Ambientale, fuori tema road condition. Ignora salvo pivot di challenge.

---

## Conversione veloce SHP → GeoJSON (da rifare live, è tecnica non soluzione)

```python
import geopandas as gpd
g = gpd.read_file("data/road-network/road_network.shp")
print(g.crs, len(g), g.columns.tolist())
g = g.to_crs(4326)                       # WGS84 per il web
g.to_file("work/output/roads.geojson", driver="GeoJSON")
```
