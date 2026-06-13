#!/usr/bin/env python3
"""Estrae i punti (coordinate lon/lat) dallo shapefile 'opendata_incidenti_comune_vicenza'
e li salva come colonne in un file CSV, insieme a tutti gli altri attributi.
"""
from pathlib import Path
import geopandas as gpd

# Definizione dei percorsi
ROOT = Path(__file__).resolve().parents[1]
SHP_PATH = ROOT / "data" / "dataset" / "opendata_incidenti_comune_vicenza" / "opendata_incidenti_comune_vicenza.shp"
OUT_CSV = ROOT / "data" / "dataset" / "opendata_incidenti_comune_vicenza_punti.csv"

def main():
    print(f"Lettura dello shapefile: {SHP_PATH.name}...")
    if not SHP_PATH.exists():
        print(f"Errore: lo shapefile {SHP_PATH} non esiste!")
        return

    # Carica lo shapefile con geopandas
    gdf = gpd.read_file(SHP_PATH)

    # Assicuriamoci che sia proiettato in EPSG:4326 (coordinate geografiche lon/lat)
    if gdf.crs != "EPSG:4326":
        print(f"Riproiezione del CRS da {gdf.crs} a EPSG:4326...")
        gdf = gdf.to_crs("EPSG:4326")

    print("Estrazione delle coordinate...")
    # Estrae longitudine (x) e latitudine (y) dalle geometrie di tipo Point
    gdf["longitude"] = gdf.geometry.x
    gdf["latitude"] = gdf.geometry.y

    # Rimuove la colonna geometry per salvare un CSV pulito senza rappresentazione WKT/WKB
    df = gdf.drop(columns="geometry")

    print(f"Salvataggio in corso di {len(df)} righe in CSV...")
    df.to_csv(OUT_CSV, sep=";", index=False, encoding="utf-8-sig")
    print(f"Completato con successo! File salvato in: {OUT_CSV}")

if __name__ == "__main__":
    main()
