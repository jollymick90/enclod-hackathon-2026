#!/usr/bin/env python3
"""A3 — fattori di rischio: importanza delle feature del modello (contratto 4).

Riusa lo STESSO training di score_segments.py (stesso DecisionTree, stessi dati,
stesso seed) ed estrae `model.feature_importances_`. Poiché il modello è allenato
su colonne one-hot (`pd.get_dummies(drop_first=True)`), le importanze grezze sono
per-dummy (es. meteo_Pioggia, fondo_Bagnato, nome_strada_SP 349 Costo…): qui le
RIaggreghiamo per feature ORIGINALE sommandole, così la dashboard mostra "quanto
pesa ogni fattore" (Meteo, Strada, Fondo, …) in linguaggio comprensibile.

Output: work/output/feature_importance.json  -> [{feature, importance}] ordinato.
La sezione /previsione lo carica e renderizza il riquadro "Cosa pesa di più sul
rischio" (compare da solo quando il file esiste).

Uso:
    .venv/bin/python3.14 work/src/build_feature_importance.py
"""
import json
import sys
from pathlib import Path

# riusa la replica fedele del notebook (single source of truth del modello)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_segments import carica_training, addestra, FEATURES  # noqa: E402

OUT_PATH = Path(__file__).resolve().parents[2] / "work" / "output" / "feature_importance.json"

# etichette leggibili per i decisori (niente nomi-colonna grezzi in dashboard)
LABELS = {
    'meteo':            'Meteo',
    'fondo':            'Fondo stradale',
    'tipo_luogo':       'Tipo di luogo',
    'nome_strada':      'Strada',
    'comune':           'Comune',
    'fascia_oraria':    'Fascia oraria',
    'giorno_settimana': 'Giorno',
    'segnaletica':      'Segnaletica',
    'mese':             'Mese',
}


def main():
    df = carica_training()
    print(f"Training: {len(df)} righe ({df['incidente'].sum()} positivi)")
    model, train_cols = addestra(df)

    imp = dict(zip(train_cols, model.feature_importances_))

    # somma le importanze delle colonne one-hot che appartengono alla stessa feature
    aggregato = []
    for feat in FEATURES:
        peso = sum(v for col, v in imp.items() if col == feat or col.startswith(feat + '_'))
        aggregato.append({'feature': LABELS[feat], 'importance': round(float(peso), 4)})

    aggregato.sort(key=lambda d: d['importance'], reverse=True)

    OUT_PATH.write_text(json.dumps(aggregato, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nOK -> {OUT_PATH}")
    print("\nFattori di rischio (somma importanze del DecisionTree):")
    for d in aggregato:
        print(f"  {d['feature']:18} {d['importance']:.4f}")


if __name__ == "__main__":
    main()
