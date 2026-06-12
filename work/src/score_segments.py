#!/usr/bin/env python3
"""B1 — scoring del modello sui segmenti km (replica fedele del notebook di previsione).

Replica il training di work/notebooks/previsione_incidenti.ipynb (DecisionTree,
stesso seed, stesso split) e scora ogni segmento × scenario (meteo × fascia):

  - le feature di scenario (meteo, fascia_oraria) sono fissate;
  - le feature di luogo (comune, nome_strada) vengono dal segmento;
  - le feature non osservabili a priori (mese, giorno, tipo_luogo, segnaletica,
    fondo) sono MARGINALIZZATE: per ogni scenario si campionano N_MC combinazioni
    dalla distribuzione empirica del dataset (fondo coerente col meteo) e si media
    la probabilità. La media su N_MC campioni rende continuo l'output 0/1 del
    DecisionTree (le foglie pure danno proba degeneri).

Output: work/output/segment_risk.csv (contratto 3) — poi caricarlo con
    .venv/bin/python3.14 work/src/load_segment_risk.py

Quando Daghem consegna un modello migliore basta sostituire `addestra()` e rilanciare.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import classification_report

N_MC = 150   # campioni Monte Carlo per scenario (marginalizzazione)
SEED = 42

ROOT = Path(__file__).resolve().parents[2]
CSV_INCIDENTI = ROOT / "data" / "dataset" / "Incidenti_Comuni_ProVI_2010-2023.csv"
CSV_NEGATIVI  = ROOT / "work" / "output" / "casi_negativi_sintetici.csv"
CSV_SEGMENTI  = ROOT / "work" / "output" / "segment_features.csv"
OUT_PATH      = ROOT / "work" / "output" / "segment_risk.csv"

FEATURES = ['mese', 'giorno_settimana', 'fascia_oraria', 'comune', 'nome_strada',
            'tipo_luogo', 'fondo', 'segnaletica', 'meteo']

METEO  = ['Sereno', 'Pioggia', 'Nebbia', 'Neve', 'Vento forte', 'Altro']
# fondo coerente col meteo (stessa mappa di generate_negatives_prompt_md.py)
FONDI_PER_METEO = {
    'Sereno':      ['Asciutto', 'Asciutto', 'Asciutto', 'Bagnato'],
    'Pioggia':     ['Bagnato', 'Bagnato', 'Sdrucciolevole'],
    'Nebbia':      ['Asciutto', 'Bagnato'],
    'Neve':        ['Innevato', 'Sdrucciolevole', 'Ghiacciato'],
    'Vento forte': ['Asciutto', 'Bagnato'],
    'Altro':       ['Asciutto', 'Bagnato', 'Sdrucciolevole'],
}


def carica_training() -> pd.DataFrame:
    """Identico alle celle 0-3 del notebook."""
    pos = pd.read_csv(CSV_INCIDENTI, sep=';', encoding='utf-8-sig')[FEATURES]
    pos['incidente'] = 1
    neg = pd.read_csv(CSV_NEGATIVI).drop(columns=['lon', 'lat'])
    return pd.concat([pos, neg], ignore_index=True)


def addestra(df: pd.DataFrame):
    """Identico alla cella 4 del notebook (stesso seed, stesso split)."""
    X = pd.get_dummies(df.drop(columns=['incidente']), drop_first=True)
    y = df['incidente']
    X_temp, X_test, y_temp, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)
    X_train, X_val, y_train, y_val = train_test_split(
        X_temp, y_temp, test_size=0.25, random_state=42, stratify=y_temp)

    model = DecisionTreeClassifier(random_state=42)
    model.fit(X_train, y_train)
    y_val_pred = model.predict_proba(X_val)[:, 1]
    print("Replica del notebook — performance su validation:")
    print(classification_report(y_val, y_val_pred > 0.5))
    return model, list(X.columns)


def scora(model, train_cols: list[str], df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    seg = pd.read_csv(CSV_SEGMENTI)
    fasce  = sorted(df['fascia_oraria'].dropna().unique())
    giorni = df['giorno_settimana'].dropna()
    tipi   = df['tipo_luogo'].dropna()
    segnal = df['segnaletica'].dropna()

    righe = []
    for met in METEO:
        for fascia in fasce:
            # N_MC estrazioni delle condizioni non osservabili, condivise tra i segmenti
            cond = pd.DataFrame({
                'mese':             rng.integers(1, 13, size=N_MC),
                'giorno_settimana': rng.choice(giorni, size=N_MC),
                'fascia_oraria':    fascia,
                'tipo_luogo':       rng.choice(tipi, size=N_MC),
                'fondo':            rng.choice(FONDI_PER_METEO[met], size=N_MC),
                'segnaletica':      rng.choice(segnal, size=N_MC),
                'meteo':            met,
            })
            # prodotto cartesiano segmenti × campioni
            batch = seg[['segment_id', 'comune', 'nome_strada']].merge(cond, how='cross')
            X = pd.get_dummies(batch[FEATURES], drop_first=True)
            X = X.reindex(columns=train_cols, fill_value=False)
            batch['p'] = model.predict_proba(X)[:, 1]
            media = batch.groupby('segment_id')['p'].mean().reset_index()
            media['meteo'] = met
            media['fascia_oraria'] = fascia
            righe.append(media.rename(columns={'p': 'risk'}))
            print(f"  scenario {met:12} × {fascia:12} ok")

    out = pd.concat(righe, ignore_index=True)
    return out[['segment_id', 'meteo', 'fascia_oraria', 'risk']].round({'risk': 4})


def main():
    df = carica_training()
    print(f"Training: {len(df)} righe ({df['incidente'].sum()} positivi)")
    model, train_cols = addestra(df)

    out = scora(model, train_cols, df)
    out.to_csv(OUT_PATH, index=False)
    print(f"\nOK: {len(out)} predizioni -> {OUT_PATH}")
    pivot = out.groupby('meteo')['risk'].mean().sort_values(ascending=False)
    print("\nRischio medio per meteo (sanity check — atteso: Neve/Pioggia > Sereno):")
    print(pivot.to_string())
    print("\nOra: .venv/bin/python3.14 work/src/load_segment_risk.py")


if __name__ == "__main__":
    main()
