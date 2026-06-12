# 01 — Strategia

## Challenge: 01 — Road Condition Intelligence

Scelta giusta per te: i dataset rilasciati pesano nettamente verso le infrastrutture
(incidenti, sensori IoT, rete stradale, spargimento sale, Sentinel-1 SAR), ed è il
binario dove la tua expertise di dominio (manutenzione predittiva / monitoraggio
infrastrutturale, futuro lavoro in CAEmate) ti dà credibilità reale davanti alla
giuria. Sai cosa serve davvero a un manutentore.

**Rovescio della medaglia**: proprio perché è il binario "ovvio" dato il dataset,
sarà probabilmente il più affollato. Non vinci con "l'ennesima mappa degli incidenti".
Vinci legando fonti eterogenee in una **decisione**.

## Angolo proposto: prioritizzazione della manutenzione per segmento stradale

Uno strumento che fonde, per ogni tratta stradale, un **punteggio di rischio/priorità**
a partire da:

- storico incidenti (pattern di rischio per tratta)
- dati sensori (stato infrastrutturale / flussi)
- cicli gelo-disgelo dedotti dallo spargimento sale (usura asfalto)

…con un **copilota AI** che spiega *perché* quel tratto è prioritario e genera un
piano di ispezione. La giuria non vuole un grafico: vuole uno strumento che un
decisore pubblico usa per decidere dove spendere il budget di manutenzione.

## Il differenziatore vero: Sentinel-1 SAR

La deformazione del suolo vicino alle strade (mondo InSAR/monitoraggio, casa tua)
è qualcosa che quasi nessun altro team toccherà. È il pezzo che ti distingue.

- Trattalo come feature **ad alto rischio / alto rendimento**.
- Il `.SAFE` è pesante e ostico in 24h: estrai una slice raster / un indice
  sintetico, non processarlo tutto.
- **Fallback obbligatorio**: la demo core deve funzionare anche senza questo pezzo.
  Se ti mangia tempo, lo droppi e resti comunque con un prototipo solido.

## Stack: ottimizza per la consegna, non per il CV

Il blueprint "Senior" (Svelte 5 Runes + NestJS + pgvector + Threlte 3D) è
over-engineered per 24h: la ricetta per arrivare alle 11:45 con un'architettura
elegante e niente da mostrare. La giuria premia il prototipo funzionante e l'impatto.

Regola: **meno strati, più tempo sulla sostanza.**

- **Da solo / in due → Python tutto**: `geopandas` legge gli `.shp` nativamente,
  `streamlit` (o Dash) ti dà una dashboard con mappa (`pydeck`/`folium`/`kepler.gl`)
  in pochissimo codice, e l'LLM lo attacchi nello stesso linguaggio. Via più rapida
  in assoluto per un prototipo dati+GIS.
- **Con un frontendista forte → React + MapLibre**: UI più curata. React è più
  diffuso di Svelte, quindi più compatibile con eventuali compagni.
- **SvelteKit/3D**: solo con un team già velocissimo in quello stack. Improbabile.

Lo stack definitivo lo decidi domani con chi recluti.

## AI: evita il RAG vettoriale sui dati tabellari

L'idea "RAG con vector DB sugli incidenti" è quasi sempre sbagliata per dati
**tabellari**. Meglio:

- LLM che fa **text-to-SQL** / interroga il dataframe, **oppure**
- LLM che **spiega** la prioritizzazione che hai già calcolato tu.

Il "copilota che spiega la mappa" è una feature più solida e difendibile del
"chatbot che fa RAG sugli incidenti".

## Nota CAEmate

Il codice/know-how proprietario di CAEmate è "pre-existing proprietary" → da non
toccare durante l'evento. La tua **competenza di dominio** (manutenzione predittiva,
InSAR, monitoraggio infrastrutturale) invece è tua: usala quanto vuoi, è il tuo vero
vantaggio competitivo qui.
