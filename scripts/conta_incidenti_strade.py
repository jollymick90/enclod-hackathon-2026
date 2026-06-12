import csv
from collections import Counter
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / "data" / "dataset" / "Incidenti_Comuni_ProVI_2010-2023.csv"

contatore = Counter()

with open(CSV_PATH, encoding="utf-8") as f:
    reader = csv.DictReader(f, delimiter=";")
    for riga in reader:
        strada = riga["nome_strada"].strip()
        if strada:  # salta righe senza nome strada
            contatore[strada] += 1

strada_max, n_max = contatore.most_common(1)[0]
strada_min, n_min = contatore.most_common()[-1]

print(f"Strade distinte: {len(contatore)}")
print(f"Strada con PIU' incidenti:  {strada_max} ({n_max} incidenti)")
print(f"Strada con MENO incidenti: {strada_min} ({n_min} incidenti)")

print("\nTop 5:")
for strada, n in contatore.most_common(5):
    print(f"  {n:5d}  {strada}")

print("\nUltime 5:")
for strada, n in contatore.most_common()[-5:]:
    print(f"  {n:5d}  {strada}")
