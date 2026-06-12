Agisci come un esperto Data Scientist e Data Engineer. Ho bisogno del tuo aiuto per generare dati sintetici di "Negative Cases" (ovvero record in cui NON è avvenuto alcun incidente) per bilanciare un dataset destinato ad addestrare un modello di classificazione binaria.

Ti fornirò un esempio di tracciato record reale (che rappresenta un incidente avvenuto) e una riga parziale. Nel file finale che utilizzerò saranno presenti i 
nomi delle feature nella prima riga (header), quindi genera l'output includendo una riga di header fittizia ma coerente, seguita dai dati sintetici in formato 
CSV (separati da punto e virgola).

Ecco i dati di partenza per comprendere il contesto geografico, le variabili e la struttura:
- Record Incidente: "2010;Polizia Municipale;11;Sabato;Sera;SANTORSO;SP 350 Val d'Astico;Rettilineo;VIA IV NOVEMBRE, 57 SP 350 VAL D'ASTICO;11.
3856020;45.7320280;0;Bagnato;Orizzontale;Pioggia;Tamponamento;Procedeva senza mantenere la distanza di sicurezza (art.149);;Autovettura privata;;;Autovettura privata;;;;0;0;0;1"
- Frammento coerente: "11;Sabato;Sera;SANTORSO;SP 350 Val d'Astico;Rettilineo;VIA IV NOVEMBRE, 57 SP 350 VAL D'ASTICO;Sereno;Pioggia;"

**ISTRUZIONI PER LA GENERAZIONE DEI DATI SINTETICI (NO INCIDENTI):**
1. Genera almeno 2 record di "NON incidente" per ciascuno scenario/contesto derivabile dai dati sopra.
2. I record devono rappresentare situazioni di guida sicura o regolare. Pertanto:
   - Le feature relative alla dinamica (es. "Tamponamento") o alla violazione (es. "art. 149") devono essere vuote, nulle o 
valorizzate con stringhe che indicano assenza di evento/regolarità.
   - I contatori finali relativi a feriti, morti o coinvolgimenti negativi devono essere tassativamente tutti a 0 (es. 0;0;0;0).
3. Per rendere il dataset robusto per l'addestramento, varia intelligentemente i valori che influenzano la guida 
(es. condizioni meteo, stato dell'asfalto, orario) mantenendo però la coerenza di base (es. se l'asfalto è "Asciutto", il meteo non sarà "Pioggia intensa").
4. Mantieni la struttura posizionale delle feature (stesso numero di punti e virgola del record di esempio).
5. Mantieni invariate le seguenti feature comune,nome_strada,tipo_luogo e indirizzo rispetto alla fonte dal quale generi il dato sintetico. 
Generami l'output direttamente in un blocco di codice in formato CSV standard.
