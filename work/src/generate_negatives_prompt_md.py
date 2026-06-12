"""
Genera "Negative Cases" sintetici seguendo le istruzioni di docs/_deprecated/PROMPT.md:

- >= 2 record di NON-incidente per ogni record reale (scenario/contesto)
- comune, nome_strada, tipo_luogo, indirizzo (e lon/lat/kmt_etm) INVARIATI rispetto alla fonte
- campi dinamica/violazione (natura, des_circ_*, veicolo_*, avaria_*, des_psico_*) vuoti
- contatori morti/feriti tassativamente a 0
- variazione intelligente di meteo/fondo/orario con COERENZA:
  * fondo compatibile col meteo (mai "Pioggia" + "Asciutto")
  * neve/ghiaccio solo nei mesi invernali (Nov-Mar)
- stessa struttura posizionale a 29 colonne del CSV originale, separatore ';'

Output: work/output/negative_cases_prompt.csv
"""

import pandas as pd
import numpy as np
from pathlib import Path

NEG_PER_RECORD = 2
SEED           = 42

ROOT     = Path(__file__).parent.parent.parent
CSV_PATH = ROOT / "data" / "dataset" / "Incidenti_Comuni_ProVI_2010-2023.csv"
OUT_PATH = Path(__file__).parent.parent / "output" / "negative_cases_prompt.csv"

# Campi da azzerare/svuotare: nessun evento = nessuna dinamica, nessun coinvolto
CAMPI_DINAMICA = ['natura', 'des_circ_a', 'des_circ_b', 'veicolo_a', 'avaria_a',
                  'des_psico_a', 'veicolo_b', 'avaria_b', 'des_psico_b', 'veicolo_c']
CAMPI_CONTATORI = ['veicoli_oltre_a_b_c', 'pedoni_morti_feriti', 'tot_morti', 'tot_feriti']

# Coerenza meteo -> fondi ammessi (derivata dalle coppie osservate nel dataset,
# ripulita dalle incoerenze tipo "Pioggia + Asciutto")
FONDI_PER_METEO = {
    'Sereno':      ['Asciutto', 'Asciutto', 'Asciutto', 'Bagnato'],  # pesi impliciti
    'Pioggia':     ['Bagnato', 'Bagnato', 'Sdrucciolevole'],
    'Nebbia':      ['Asciutto', 'Bagnato'],
    'Neve':        ['Innevato', 'Sdrucciolevole', 'Ghiacciato'],
    'Vento forte': ['Asciutto', 'Bagnato'],
    'Altro':       ['Asciutto', 'Bagnato', 'Sdrucciolevole'],
}
# TODO(decisione di dominio): pesi climatologici del meteo per i giorni "normali"
# di guida nel vicentino. Con None il campionamento è uniforme (1/6 ciascuno →
# nevica nel 17% dei negativi, irrealistico). I pesi devono sommare a 1 e seguire
# l'ordine di FONDI_PER_METEO: [Sereno, Pioggia, Nebbia, Neve, Vento forte, Altro]
METEO_PESI = None  # es. [0.60, 0.15, 0.07, 0.03, 0.05, 0.10]

METEO_SOLO_INVERNO = {'Neve'}
FONDI_SOLO_INVERNO = {'Innevato', 'Ghiacciato'}
MESI_INVERNO  = [11, 12, 1, 2, 3]
MESI_TUTTI    = list(range(1, 13))


def genera(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    fasce  = df['fascia_oraria'].dropna().unique()
    giorni = df['giorno_settimana'].dropna().unique()
    segnal = df['segnaletica'].dropna().unique()
    meteo_opzioni = list(FONDI_PER_METEO.keys())

    negativi = []
    for _, fonte in df.iterrows():
        for _ in range(NEG_PER_RECORD):
            rec = fonte.copy()

            # Variazione coerente delle condizioni di guida
            met = rng.choice(meteo_opzioni, p=METEO_PESI)
            mesi_ok = MESI_INVERNO if met in METEO_SOLO_INVERNO else MESI_TUTTI
            fondo = rng.choice(FONDI_PER_METEO[met])
            mese = int(rng.choice(MESI_INVERNO if fondo in FONDI_SOLO_INVERNO else mesi_ok))

            rec['anno']             = int(rng.integers(2010, 2024))
            rec['mese']             = mese
            rec['giorno_settimana'] = rng.choice(giorni)
            rec['fascia_oraria']    = rng.choice(fasce)
            rec['meteo']            = met
            rec['fondo']            = fondo
            rec['segnaletica']      = rng.choice(segnal)

            # Guida sicura/regolare: niente dinamica, contatori a zero
            rec[CAMPI_DINAMICA]  = ''
            rec[CAMPI_CONTATORI] = 0

            negativi.append(rec)

    neg = pd.DataFrame(negativi).reset_index(drop=True)

    # Integrità: scarta i sintetici che coincidono con un incidente reale
    # sulla stessa combinazione spazio-temporale
    chiave = ['comune', 'nome_strada', 'indirizzo', 'anno', 'mese',
              'giorno_settimana', 'fascia_oraria']
    df_chiave = df.copy()
    df_chiave['anno'] = df_chiave['anno'].astype(str).str.extract(r'(\d+)')[0].astype(int)
    df_chiave['mese'] = df_chiave['mese'].astype(int)
    reali = df_chiave[chiave].drop_duplicates().assign(_real=1)
    neg = neg.merge(reali, on=chiave, how='left')
    neg = neg[neg['_real'].isna()].drop(columns='_real')

    # E i duplicati interni (stesso luogo + stesso momento generato due volte)
    return neg.drop_duplicates(subset=chiave).reset_index(drop=True)


def main():
    rng = np.random.default_rng(SEED)
    df = pd.read_csv(CSV_PATH, sep=';', encoding='utf-8-sig')
    print(f"Record reali (fonte): {len(df)}")

    neg = genera(df, rng)
    print(f"Negativi generati: {len(neg)} (target {len(df) * NEG_PER_RECORD}, "
          f"scartati {len(df) * NEG_PER_RECORD - len(neg)} per collisioni/duplicati)")

    neg.to_csv(OUT_PATH, sep=';', index=False)
    print(f"Salvato: {OUT_PATH}")

    print("\nCoppie meteo/fondo generate (verifica coerenza):")
    print(neg.groupby(['meteo', 'fondo']).size().sort_values(ascending=False).to_string())
    print("\nNeve/ghiaccio per mese (deve essere solo Nov-Mar):")
    inverno = neg[neg['fondo'].isin(FONDI_SOLO_INVERNO) | (neg['meteo'] == 'Neve')]
    print(sorted(inverno['mese'].unique()))


if __name__ == '__main__':
    main()
