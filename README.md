# ENCLOD Open Data Hackathon — Vicenza, 12–13 Giugno 2026

Cartella di lavoro per l'evento. Tutto quello che c'è in `docs/` è **materiale di
riferimento** (strategia, note sui dataset, template del pitch, IP): preparazione
lecita, non codice-soluzione. Il codice della soluzione va scritto **durante**
l'evento, dentro `work/` (vedi regola sotto).

---

## Struttura della cartella

```
enclod-hackathon-2026/
├── README.md                 ← questo file (indice + orientamento)
├── data/                     ← TUTTI i dataset scaricati (una sottocartella per dataset)
├── docs/
│   ├── sfida-scelta.md       ← documento canonico: sfide scelte + descrizione soluzione
│   └── _deprecated/          ← vecchia documentazione (strategia, spec, plan…), solo storico
├── work/                     ← QUI si costruisce live (vuoto adesso, è giusto così)
│   ├── notebooks/            ← esplorazione dati, prototipi
│   ├── src/                  ← codice della soluzione
│   └── output/               ← geojson convertiti, export, ecc.
└── pitch/                    ← slide / demo finale
```

## Come organizzare `data/`

Una sottocartella per dataset. Attenzione a due formati:

- **Shapefile (`.shp`)**: NON è un file singolo. Porta con sé `.shx`, `.dbf`,
  `.prj` (e a volte altri). Tienili **tutti insieme** nella stessa cartella o
  geopandas non apre il file.
- **Copernicus `.SAFE`**: è una **cartella** intera, pesante, con dentro dati
  raster scientifici. Non aprirla a mano: estrai la slice/indice che ti serve.

Struttura suggerita (adatta ai nomi reali di ciò che scarichi):

```
data/
├── accidents/         CSV incidenti 2010–2023
├── sensors/           CSV sensori stazioni enCLOD
├── road-network/      SHP rete stradale (+ file gemelli)
├── salt-spreading/    PDF spargimento sale
├── boundaries/        SHP confini comunali (+ file gemelli)
├── osm/               SHP OpenStreetMap NE Italia (+ file gemelli)
├── istat-census/      CSV censimento ISTAT
├── arpav-pfas/        CSV PFAS ARPAV
├── sentinel-1/        .SAFE radar SAR
└── sentinel-2/        .SAFE ottico multispettrale
```

---

## ⚠️ Regola d'oro sull'IP / codice (da non violare)

- **Vietato**: portare dati proprietari/privati o una soluzione già costruita prima
  e spacciarla per lavoro dell'hackathon (regolamento Art. 6.6: vai dichiarato che
  la soluzione nasce durante l'evento).
- **Lecito ed esplicitamente richiesto**: ambiente pronto, toolchain installata,
  dataset già studiati, tecnica di base nelle mani. Tutto ciò che è in `docs/`.
- In caso di dubbio su una fonte dati → chiedi allo staff (le guidelines stesse lo
  dicono). Contatto: info@dihvicenza.it

## Timeline

| Quando | Cosa |
|---|---|
| 12 Giu 08:00 | Kickoff. Recluta team, blocca lo scope MVP nelle prime ore. |
| 12–13 Giu | Hacking continuativo. |
| 13 Giu 11:45 | **Final pitch** davanti alla giuria. |
| 13 Giu pomeriggio | Premiazione. |

## Link utili

- Repository dataset: https://enclod.dihvicenza.it/
- Guidelines: https://enclod.dihvicenza.it/guidelines
- API Docs: https://enclod.dihvicenza.it/api-docs
- Workshops (video+slide): https://enclod.dihvicenza.it/workshops
- Pagina evento: https://www.epcsrl.eu/it/enclod-hackathon/
