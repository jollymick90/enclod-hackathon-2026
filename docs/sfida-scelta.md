## elenco sfide scelte
### sfida secondaria
Sfida 1.1 “Sicurezza e Esperienza dell’Utente Finale”: Come è possibile valorizzare
gli Open Data per migliorare la
sicurezza e l’esperienza di viaggio per autisti e pendolari?

### sfida primaria
Sfida 1.2 “Suppor
to al Decision Making”: È possibile usare gli Open Data per assiste
le PA e i gestori della rete st
radale nel pianificare investimenti e inter
venti di
manutenzione con maggiore efficienza ed efficacia?


## appunti soluzione pensata
la dashboard 
1 tool analitico per migliorare l'analisi dei dati storici sugli icidenti

2 tool predittivo per supportare le decisioni pubbliche per migliorare la sicurezza stradale

3
tool analitico:
mappa interattiva
indice di incidente per tratto stradale
analisi dei fattori di rischio
analisi delle cause associate

tool preditivo:
definizione di misure per la riduzione del rischio

possibilità di valutare l'effetto potenziale della misura azione sulla riduzione dell'indice di incidente. 

vorremmo aggiungere un elemento di predittività con il meteo. prendere i dati del meteo che abbiamo e 'predirre' per esempio per il 10 ottobre 2025 il pezzo di strada X quale sarà il suo indice di pericolosità di incidente, con il modello trainato. 

inoltre vorremmo avere un elenco delle strade in ordine di priorità di manutenzione. il indice e indice_grezzo sono quell'elemento che può determinare l'ordine. e l'ordine ha senso che sia intersecato con i comuni interessati, i pezzi dei pezzi di strada e dei pezzi di strada nei comuni.

visto che abbiamo i dati di solo 3-4 strade, le informazioni di  Attraversamenti, Semafori, Stop, Incroci/rotatorie, Autovelox, Illuminazione, Altro (parcheggi…), voglio che siano intersecati con le strade di interesse. 

il layer delle strade deve avere di default acceso 

"incidenti vs strade sicure" non va visualizzato nel prodotto finale.

questi filtri:

"Incidenti stradali — Provincia di Vicenza (2010-2023)
Anno

Tutti
Mese

Tutti
Giorno settimana

Tutti
Fascia oraria

Tutti
Comune

Tutti
Nome strada

Tutti
Natura

Tutti
Fondo

Tutti
Meteo

Tutti
Gravita
"
 sono importanti ma va migliorata la user friendly


la 'predizione' della pericolosità, non è un puro risultato di predzione ML, ma un mix tra:
1) data la probabilità che in quel pezzo di strada succeda un incidente
2) il dato storico ci dice che in media la gravità è TOT

