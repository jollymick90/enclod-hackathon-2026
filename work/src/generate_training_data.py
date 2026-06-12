"""
Genera il dataset di training (positivi reali + negativi sintetici)
e produce un report HTML interattivo per validare visivamente i dati.

v2 — I negativi sono campionati LUNGO LA GEOMETRIA REALE dei 3 corridoi
provinciali coperti dal dataset incidenti (SP 46 Pasubio, SP 349 Costo,
SP 350 Val d'Astico + varianti), usando il grafo "SP OSM 6707".
Questo evita il sampling bias: i negativi vivono sulle stesse strade dei
positivi, coprendone però l'intera lunghezza.

NOTA: kmt_etm è escluso dalle feature (è 0 in 601/738 incidenti reali).
La posizione è codificata da lon/lat.

Output:
  work/output/training_dataset.csv   — dataset pronto per il modello
  work/output/training_report.html   — mappa + grafici di distribuzione
"""

import pandas as pd
import numpy as np
import geopandas as gpd
import folium
import matplotlib.pyplot as plt
import base64
import io
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────
N_NEGATIVI = 2200   # ~3x i positivi (738). Modifica questo valore per sperimentare.
SEED       = 42
SP_TARGET  = {'46', '349', '350'}  # corridoi coperti dal dataset incidenti

# Distribuzione climatologica del meteo durante la guida (vicentino, stima di
# dominio — da tarare col team). Deve sommare a 1. Con campionamento uniforme
# (1/6 di neve) il modello impara "neve = riga sintetica = sicura" e inverte
# la direzione del rischio (leakage verificato sui numeri).
METEO_PESI = {
    'Sereno': 0.60, 'Pioggia': 0.15, 'Nebbia': 0.07,
    'Neve': 0.03, 'Vento forte': 0.05, 'Altro': 0.10,
}
# Fondo ammesso per ogni meteo (ripetizioni = pesi impliciti)
FONDI_PER_METEO = {
    'Sereno':      ['Asciutto', 'Asciutto', 'Asciutto', 'Bagnato'],
    'Pioggia':     ['Bagnato', 'Bagnato', 'Sdrucciolevole'],
    'Nebbia':      ['Asciutto', 'Bagnato'],
    'Neve':        ['Innevato', 'Sdrucciolevole', 'Ghiacciato'],
    'Vento forte': ['Asciutto', 'Bagnato'],
    'Altro':       ['Asciutto', 'Bagnato', 'Sdrucciolevole'],
}

ROOT     = Path(__file__).parent.parent.parent
CSV_PATH = ROOT / "data" / "dataset" / "Incidenti_Comuni_ProVI_2010-2023.csv"
GPKG_SP  = ROOT / "data" / "dataset" / "extracted" / "sp_osm" / "SP OSM 6707.gpkg"
SHP_COM  = ROOT / "data" / "dataset" / "extracted" / "comuni" / "c0104011_comuni_VI.shp"
OUT_DIR  = Path(__file__).parent.parent / "output"
OUT_DIR.mkdir(exist_ok=True)

FEATURE_COLS = [
    'mese', 'giorno_settimana', 'fascia_oraria',
    'comune', 'nome_strada', 'tipo_luogo',
    'fondo', 'segnaletica', 'meteo',
]

MESI = {1:'Gen',2:'Feb',3:'Mar',4:'Apr',5:'Mag',6:'Giu',
        7:'Lug',8:'Ago',9:'Set',10:'Ott',11:'Nov',12:'Dic'}


# ── Caricamento dati ───────────────────────────────────────────────────────

def load_incidenti() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH, sep=';', encoding='utf-8-sig')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    return df.dropna(subset=['lon', 'lat'])


def nome_strada_da_sp(sp: str) -> str:
    """Mappa il nome del grafo OSM sul naming usato nel dataset incidenti."""
    s = sp.lower()
    if s.startswith('46'):
        if 'racc' in s:
            return 'SP 046 rac Pasubio Raccordo del Sole'
        if 'torrebelvicino' in s:
            return 'SP 046 var Torrebelvicino'
        return 'SP 046 Pasubio'  # include la variante Costabissara (tratto sud)
    if s.startswith('349'):
        if 'var' in s:
            return 'SP 349 var Costo Variante'
        return 'SP 349 Costo'
    return "SP 350 Val d'Astico"


def load_corridoi() -> gpd.GeoDataFrame:
    """I segmenti del grafo SP appartenenti ai 3 corridoi, esplosi in LineString."""
    rete = gpd.read_file(GPKG_SP)  # EPSG:6707, metri
    rete['sp_base'] = rete['SP'].astype(str).str.extract(r'^(\d+)')[0]
    corridoi = rete[rete['sp_base'].isin(SP_TARGET)].copy()
    corridoi['nome_strada'] = corridoi['SP'].astype(str).map(nome_strada_da_sp)
    corridoi = corridoi.explode(index_parts=False).reset_index(drop=True)
    corridoi['seg_len'] = corridoi.geometry.length
    return corridoi


# ── Generazione negativi ───────────────────────────────────────────────────

def genera_negativi(df: pd.DataFrame, corridoi: gpd.GeoDataFrame,
                    n: int = N_NEGATIVI, seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_gen = int(n * 1.3)

    # 1. Punti casuali lungo le linee, probabilità proporzionale alla lunghezza
    probs = corridoi['seg_len'] / corridoi['seg_len'].sum()
    seg_idx = rng.choice(len(corridoi), size=n_gen, p=probs.values)
    punti = [
        corridoi.geometry.iloc[i].interpolate(rng.uniform(0, corridoi['seg_len'].iloc[i]))
        for i in seg_idx
    ]
    neg = gpd.GeoDataFrame(
        {'nome_strada': corridoi['nome_strada'].iloc[seg_idx].values},
        geometry=punti, crs=corridoi.crs,
    )

    # 2. Comune via join spaziale (nearest gestisce i punti sul confine)
    comuni = gpd.read_file(SHP_COM).to_crs(corridoi.crs)
    neg = gpd.sjoin_nearest(neg, comuni[['nomcom', 'geometry']], how='left')
    neg['comune'] = neg['nomcom'].str.upper()
    neg = neg.drop(columns=['nomcom', 'index_right'])

    # 3. Coordinate WGS84 per il modello e la mappa
    neg_wgs = neg.to_crs(4326)
    neg['lon'] = neg_wgs.geometry.x
    neg['lat'] = neg_wgs.geometry.y

    # 4. Condizioni temporali/ambientali: distribuzione UNIFORME
    #    (non quella degli incidenti, che sovrarappresenta le condizioni a rischio)
    neg['mese']             = rng.integers(1, 13, size=n_gen)
    neg['giorno_settimana'] = rng.choice(df['giorno_settimana'].dropna().unique(), size=n_gen)
    neg['fascia_oraria']    = rng.choice(df['fascia_oraria'].dropna().unique(), size=n_gen)
    # meteo con pesi climatologici (esposizione reale) e fondo coerente col meteo
    neg['meteo'] = rng.choice(list(METEO_PESI), size=n_gen, p=list(METEO_PESI.values()))
    neg['fondo'] = [rng.choice(FONDI_PER_METEO[m]) for m in neg['meteo']]
    neg['segnaletica']      = rng.choice(df['segnaletica'].dropna().unique(), size=n_gen)
    neg['tipo_luogo']       = rng.choice(df['tipo_luogo'].dropna().unique(), size=n_gen)
    neg['incidente']        = 0

    # 5. Scarta le combinazioni spazio-temporali che coincidono con incidenti reali
    chiave = ['nome_strada', 'comune', 'mese', 'giorno_settimana', 'fascia_oraria']
    reali = df[chiave].drop_duplicates().assign(_real=1)
    neg = neg.merge(reali, on=chiave, how='left')
    neg = neg[neg['_real'].isna()].drop(columns='_real')

    return pd.DataFrame(neg.drop(columns='geometry')).head(n).reset_index(drop=True)


# ── Visualizzazione ────────────────────────────────────────────────────────

def _fig_to_base64(fig) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=120)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode()


def build_distribution_charts(positivi: pd.DataFrame, negativi: pd.DataFrame) -> str:
    features = [
        ('mese',             'Mese'),
        ('fascia_oraria',    'Fascia oraria'),
        ('giorno_settimana', 'Giorno settimana'),
        ('meteo',            'Meteo'),
        ('fondo',            'Fondo stradale'),
        ('nome_strada',      'Strada (corridoio)'),
    ]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    fig.suptitle('Distribuzione feature: Incidenti reali vs Negativi sintetici', fontsize=14, fontweight='bold')
    axes = axes.flatten()

    for ax, (col, label) in zip(axes, features):
        cats = sorted(set(positivi[col].dropna()) | set(negativi[col].dropna()), key=str)
        if col == 'mese':
            cats = sorted(cats, key=int)

        pos_counts = positivi[col].value_counts(normalize=True).reindex(cats, fill_value=0)
        neg_counts = negativi[col].value_counts(normalize=True).reindex(cats, fill_value=0)

        x = np.arange(len(cats))
        w = 0.35
        ax.bar(x - w/2, pos_counts.values, w, label='Reali (incidente=1)', color='#e74c3c', alpha=0.85)
        ax.bar(x + w/2, neg_counts.values, w, label='Sintetici (incidente=0)', color='#3498db', alpha=0.85)

        ax.set_title(label, fontsize=11)
        ax.set_xticks(x)
        xticklabels = [MESI.get(c, str(c)) for c in cats] if col == 'mese' else [str(c) for c in cats]
        ax.set_xticklabels(xticklabels, rotation=35, ha='right', fontsize=8)
        ax.set_ylabel('Frequenza relativa')
        ax.legend(fontsize=8)
        ax.grid(axis='y', alpha=0.3)

    plt.tight_layout()
    encoded = _fig_to_base64(fig)
    plt.close(fig)
    return encoded


def build_map(positivi: pd.DataFrame, negativi: pd.DataFrame,
              corridoi: gpd.GeoDataFrame) -> folium.Map:
    center_lat = positivi['lat'].mean()
    center_lon = positivi['lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=11,
                   tiles='CartoDB positron')

    # Geometria dei corridoi SP (contesto)
    rete_layer = folium.FeatureGroup(name='Rete SP (corridoi 46/349/350)', show=True)
    for _, r in corridoi.to_crs(4326).iterrows():
        coords = [(lat, lon) for lon, lat in r.geometry.coords]
        folium.PolyLine(coords, color='#7f8c8d', weight=3, opacity=0.6,
                        tooltip=r['nome_strada']).add_to(rete_layer)
    rete_layer.add_to(m)

    # Negativi sintetici (blu) — punti esatti sulla geometria stradale
    neg_layer = folium.FeatureGroup(name='Negativi sintetici (incidente=0)', show=True)
    for _, r in negativi.iterrows():
        folium.CircleMarker(
            location=[r['lat'], r['lon']], radius=4,
            color='#2980b9', fill=True, fill_opacity=0.5, weight=0,
            popup=f"<b>Sintetico</b><br>{r['comune']} — {r['nome_strada']}<br>"
                  f"Mese:{r['mese']} {r['fascia_oraria']}<br>Meteo:{r['meteo']} Fondo:{r['fondo']}"
        ).add_to(neg_layer)
    neg_layer.add_to(m)

    # Incidenti reali (rosso)
    pos_layer = folium.FeatureGroup(name='Incidenti reali (incidente=1)', show=True)
    for _, r in positivi.iterrows():
        folium.CircleMarker(
            location=[r['lat'], r['lon']], radius=6,
            color='#c0392b', fill=True, fill_opacity=0.8, weight=0,
            popup=f"<b>Incidente reale</b><br>{r['comune']} — {r['nome_strada']}<br>"
                  f"Mese:{r['mese']} {r['fascia_oraria']}<br>Meteo:{r['meteo']} Fondo:{r['fondo']}"
        ).add_to(pos_layer)
    pos_layer.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m


def build_html_report(positivi: pd.DataFrame, negativi: pd.DataFrame,
                      map_obj: folium.Map, charts_b64: str) -> str:
    map_html = map_obj._repr_html_()
    n_pos, n_neg = len(positivi), len(negativi)
    strade_pos = positivi['nome_strada'].nunique()
    strade_neg = negativi['nome_strada'].nunique()

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<title>Training Data Report — Incidenti Vicenza</title>
<style>
  body {{ font-family: -apple-system, sans-serif; margin: 0; background: #f5f6fa; color: #2c3e50; }}
  header {{ background: #2c3e50; color: white; padding: 20px 32px; }}
  header h1 {{ margin: 0; font-size: 22px; }}
  header p {{ margin: 4px 0 0; opacity: .7; font-size: 13px; }}
  .stats {{ display: flex; gap: 16px; padding: 24px 32px; flex-wrap: wrap; }}
  .stat {{ background: white; border-radius: 10px; padding: 16px 24px; flex: 1; min-width: 150px;
           box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
  .stat .n {{ font-size: 32px; font-weight: 700; }}
  .stat .l {{ font-size: 12px; opacity: .6; margin-top: 4px; }}
  .stat.red .n  {{ color: #e74c3c; }}
  .stat.blue .n {{ color: #2980b9; }}
  section {{ padding: 0 32px 32px; }}
  h2 {{ font-size: 16px; margin: 0 0 12px; color: #555; }}
  .map-wrap {{ border-radius: 12px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,.12); height: 500px; }}
  .map-wrap iframe {{ width: 100%; height: 100%; border: none; }}
  .charts {{ background: white; border-radius: 12px; padding: 16px;
             box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
  .charts img {{ width: 100%; }}
  .tip {{ background: #eaf4fb; border-left: 4px solid #2980b9; padding: 12px 16px;
          border-radius: 0 8px 8px 0; margin-bottom: 20px; font-size: 13px; }}
</style>
</head>
<body>
<header>
  <h1>Training Data Report — Corridoi SP 46 / SP 349 / SP 350</h1>
  <p>v2 — negativi campionati sulla geometria reale della rete SP (grafo OSM) · kmt_etm escluso (81% zeri)</p>
</header>

<div class="stats">
  <div class="stat red">
    <div class="n">{n_pos}</div>
    <div class="l">Incidenti reali<br>(incidente = 1)</div>
  </div>
  <div class="stat blue">
    <div class="n">{n_neg}</div>
    <div class="l">Negativi sintetici<br>(incidente = 0)</div>
  </div>
  <div class="stat">
    <div class="n">{n_pos + n_neg}</div>
    <div class="l">Righe totali nel dataset</div>
  </div>
  <div class="stat">
    <div class="n">{strade_pos} / {strade_neg}</div>
    <div class="l">Strade nei positivi / nei negativi</div>
  </div>
  <div class="stat">
    <div class="n">{n_neg / n_pos:.1f}x</div>
    <div class="l">Rapporto negativi/positivi</div>
  </div>
</div>

<section>
  <div class="tip">
    <b>Come leggere la mappa:</b> le linee <span style="color:#7f8c8d">grigie</span> sono la geometria
    dei 3 corridoi SP dal grafo OSM. I punti <span style="color:#e74c3c">rossi</span> sono incidenti reali,
    i <span style="color:#2980b9">blu</span> sono negativi sintetici campionati <em>esattamente sulla linea
    stradale</em>. Verifica: i blu devono seguire le linee grigie e coprire anche i tratti senza punti rossi.
  </div>
  <div class="map-wrap">{map_html}</div>
</section>

<section>
  <h2>Distribuzione delle feature: reali vs sintetici</h2>
  <div class="tip">
    <b>Cosa cercare:</b> le barre rosse e blu NON devono essere identiche — i negativi usano distribuzione
    uniforme per meteo/fondo/mese, quindi i picchi delle barre rosse (es. più incidenti con pioggia o di notte)
    sono esattamente il segnale che il modello deve imparare.
  </div>
  <div class="charts">
    <img src="data:image/png;base64,{charts_b64}" alt="Distribution charts">
  </div>
</section>

</body>
</html>"""


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("Carico incidenti e grafo SP...")
    df = load_incidenti()
    corridoi = load_corridoi()
    km_tot = corridoi['seg_len'].sum() / 1000
    print(f"  Incidenti reali: {len(df)}")
    print(f"  Segmenti corridoio: {len(corridoi)} ({km_tot:.1f} km totali)")

    print(f"Genero {N_NEGATIVI} negativi lungo la rete...")
    negativi = genera_negativi(df, corridoi, n=N_NEGATIVI)
    print(f"  Negativi generati: {len(negativi)}")

    positivi = df[FEATURE_COLS + ['lon', 'lat']].copy()
    positivi['incidente'] = 1
    negativi_out = negativi[FEATURE_COLS + ['lon', 'lat', 'incidente']]

    training = pd.concat([positivi, negativi_out], ignore_index=True)
    out_csv = OUT_DIR / 'training_dataset.csv'
    training.to_csv(out_csv, index=False)
    print(f"  Salvato: {out_csv}")

    # Consegna al team ML: positivi e negativi anche come file separati
    out_pos = OUT_DIR / 'casi_positivi.csv'
    out_neg = OUT_DIR / 'casi_negativi_sintetici.csv'
    positivi.to_csv(out_pos, index=False)
    negativi_out.to_csv(out_neg, index=False)
    print(f"  Salvato: {out_pos}")
    print(f"  Salvato: {out_neg}")

    print("Costruisco la visualizzazione...")
    charts_b64 = build_distribution_charts(positivi, negativi_out)
    map_obj    = build_map(positivi, negativi_out, corridoi)
    html       = build_html_report(positivi, negativi_out, map_obj, charts_b64)

    out_html = OUT_DIR / 'training_report.html'
    out_html.write_text(html, encoding='utf-8')
    print(f"  Salvato: {out_html}")
    print("\nFatto! Apri nel browser:")
    print(f"  open {out_html}")


if __name__ == '__main__':
    main()
