# UI Dashboard PA "SaferRoads Vicenza" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rifare la UI di `work/map/web` come dashboard per decisori PA non tecnici: home a 4 card, sezioni `/analisi` `/previsione` `/priorita` `/cittadino` a viewport pieno (zero scroll di pagina), scheda tratta in linguaggio semplice, segnalazioni cittadino su PostGIS.

**Architecture:** Shell nuova (header fisso + `main` flex) sopra i componenti esistenti. Due componenti nuovi: `SectionMap` (mappa full-height per le sezioni, derivata da MultiLayerMap ma senza sidebar) e `SchedaTratta` (drill-down condiviso). Due API nuove: `GET /api/tratte/[id]` e `GET|POST /api/segnalazioni`. Una tabella nuova: `data.segnalazioni`.

**Tech Stack:** SvelteKit 2 + Svelte 5 (runes), Tailwind 4, MapLibre, PostGIS, Martin. Spec di riferimento: `docs/superpowers/specs/2026-06-12-ui-dashboard-pa-design.md`.

**Nota su TDD:** il repo non ha alcun framework di test JS e installarne uno a poche ore dal pitch è fuori scope (decisione di spec). La verifica per ogni task è: `pnpm check` (svelte-check) + verifica manuale/`curl` specificata nel task. Non saltarla mai.

**Ambiente di sviluppo:**
```bash
# stack dati (db 5433, martin 3010) già su; se non lo è:
cd work/map && docker compose up -d
# dev server della web app SUL HOST (i default di db.ts/martin.ts puntano già a localhost:5433/3010):
cd work/map/web && pnpm install && pnpm dev   # → http://localhost:5173
```
Tutti i path dei file sotto sono relativi a `work/map/web/` salvo dove indicato.

---

### Task 1: `lib/risk.ts` — fonte unica di livelli, colori e frasi

**Files:**
- Create: `src/lib/risk.ts`
- Modify: `src/lib/components/MultiLayerMap.svelte` (righe ~156–219: rimuovere costanti/funzioni duplicate, importare)

- [ ] **Step 1: Creare `src/lib/risk.ts`**

```ts
// Livelli verbali, colori e frasi del rischio — fonte unica per tutta la UI.

export const SCENARIO_METEO = ['Sereno', 'Pioggia', 'Nebbia', 'Neve', 'Vento forte', 'Altro'];
export const SCENARIO_FASCE = ['Mattino', 'Pomeriggio', 'Sera', 'Notte'];

export type Livello = {
	label: 'Basso' | 'Moderato' | 'Alto' | 'Critico';
	color: string; // colore pieno per mappa/pallini
	badge: string; // classi tailwind per il badge testuale
};

// Soglie sull'indice storico 0-100 (le stesse dei colori mappa e dei badge attuali).
export function livelloIndice(indice: number): Livello {
	if (indice >= 70) return { label: 'Critico', color: '#c92a2a', badge: 'bg-red-100 text-red-800' };
	if (indice >= 40) return { label: 'Alto', color: '#f76707', badge: 'bg-orange-100 text-orange-800' };
	if (indice >= 15) return { label: 'Moderato', color: '#eab308', badge: 'bg-yellow-100 text-yellow-800' };
	return { label: 'Basso', color: '#2f9e44', badge: 'bg-green-100 text-green-800' };
}

// Il risk del modello (0..1) satura visivamente a RISK_FULL → riportato in scala 0-100.
export const RISK_FULL = 0.5;
export function livelloRisk(risk: number): Livello {
	return livelloIndice(Math.min(risk / RISK_FULL, 1) * 100);
}

// Gradiente continuo per il colore-mappa del risk del modello (0 → verde, RISK_FULL → rosso).
export function riskColor(r: number): string {
	const stops: [number, string][] = [
		[0, '#2f9e44'], [0.15, '#ffd43b'], [0.3, '#f76707'], [0.5, '#c92a2a'],
	];
	const t = Math.min(r, RISK_FULL);
	for (let i = stops.length - 1; i >= 0; i--) if (t >= stops[i][0]) {
		if (i === stops.length - 1) return stops[i][1];
		const [a, ca] = stops[i], [b, cb] = stops[i + 1];
		const k = (t - a) / (b - a);
		const hex = (c: string) => [1, 3, 5].map((j) => parseInt(c.slice(j, j + 2), 16));
		const [r1, g1, b1] = hex(ca), [r2, g2, b2] = hex(cb);
		const mix = (x: number, y: number) => Math.round(x + (y - x) * k);
		return `rgb(${mix(r1, r2)},${mix(g1, g2)},${mix(b1, b2)})`;
	}
	return stops[0][1];
}

// Espressione MapLibre per il colore storico dei segmenti (indice 0-100).
export const STORICO_COLOR = [
	'interpolate', ['linear'], ['get', 'indice'],
	0, '#2f9e44', 15, '#ffd43b', 40, '#f76707', 70, '#c92a2a',
] as unknown[];

// Frase "raccontabile" dal ranking storico — template deterministici, niente testo libero.
export function frasePosizione(posizione: number, totale: number): string {
	if (posizione === 1) return `È la tratta più pericolosa tra le ${totale} monitorate.`;
	if (posizione <= 5) return `È tra le 5 tratte più pericolose delle ${totale} monitorate.`;
	if (posizione <= Math.ceil(totale * 0.1))
		return `È nel 10% di tratte più pericolose (${posizione}ª su ${totale}).`;
	return `È la ${posizione}ª tratta su ${totale} per pericolosità storica.`;
}
```

- [ ] **Step 2: DRY in `MultiLayerMap.svelte`**

Nella sezione `// ── Scenario predittivo (B1)` (righe ~156–219):
1. aggiungere all'inizio dello `<script>`: `import { riskColor, STORICO_COLOR, SCENARIO_METEO, SCENARIO_FASCE } from '$lib/risk';`
2. eliminare le dichiarazioni locali di `SCENARIO_METEO`, `SCENARIO_FASCE`, `RISK_FULL`, `riskColor` e `STORICO_COLOR` (la logica di `applicaScenario` resta identica).

- [ ] **Step 3: Verifica**

Run: `cd work/map/web && pnpm check`
Expected: 0 errors. Poi su http://localhost:5173/mvp scegliere meteo+fascia: i segmenti si ricolorano come prima.

- [ ] **Step 4: Commit**

```bash
git add work/map/web/src/lib/risk.ts work/map/web/src/lib/components/MultiLayerMap.svelte
git commit -m "ui: lib/risk.ts — livelli verbali, colori e frasi condivise"
```

---

### Task 2: Shell — header fisso, viewport pieno, vecchie pagine wrappate

**Files:**
- Modify: `src/lib/components/Layout.svelte` (riscrittura completa)
- Modify: `src/routes/+layout.svelte` (titolo)
- Modify: `src/routes/catalog/+page.svelte`, `src/routes/explorer/+page.svelte`, `src/routes/layers/[slug]/+page.svelte`, `src/routes/mvp/+page.svelte`, `src/routes/priorita/+page.svelte`, `src/routes/+page.svelte` (solo wrapper)

- [ ] **Step 1: Riscrivere `src/lib/components/Layout.svelte`**

```svelte
<script lang="ts">
	import { page } from '$app/state';
	let { children } = $props();

	const NAV = [
		{ href: '/analisi', label: 'Analisi' },
		{ href: '/previsione', label: 'Previsione' },
		{ href: '/priorita', label: 'Priorità' },
		{ href: '/cittadino', label: 'Cittadino' },
	];
</script>

<div class="h-dvh flex flex-col bg-neutral-50 text-neutral-900">
	<header class="shrink-0 z-30 border-b border-neutral-200 bg-white">
		<div class="px-3 sm:px-6 h-14 flex items-center justify-between gap-2">
			<a href="/" class="font-semibold tracking-tight text-base sm:text-lg whitespace-nowrap">
				SaferRoads <span class="text-blue-700">Vicenza</span>
			</a>
			<nav class="flex items-center gap-1 sm:gap-3 text-sm overflow-x-auto">
				{#each NAV as item (item.href)}
					<a
						href={item.href}
						class="px-2 py-1 rounded-md whitespace-nowrap transition {page.url.pathname.startsWith(item.href)
							? 'bg-blue-50 text-blue-800 font-medium'
							: 'text-neutral-600 hover:text-neutral-900'}"
					>
						{item.label}
					</a>
				{/each}
			</nav>
		</div>
	</header>

	<main class="flex-1 min-h-0 overflow-y-auto">
		{@render children()}
	</main>
</div>
```

Note: footer eliminato (era branding geo-sentinel/TiTiler). Le pagine-mappa useranno `h-full` dentro `main` → nessuno scroll; le pagine-documento scrollano *dentro* `main`.

- [ ] **Step 2: Titolo in `src/routes/+layout.svelte`**

Sostituire `<title>geo-sentinel</title>` con `<title>SaferRoads Vicenza</title>`.

- [ ] **Step 3: Wrappare le pagine esistenti**

Il contenitore `mx-auto max-w-6xl px-6 py-8` prima viveva in Layout; ora ogni pagina-documento se lo porta da sola. In **ognuno** di questi file — `src/routes/+page.svelte`, `src/routes/catalog/+page.svelte`, `src/routes/explorer/+page.svelte`, `src/routes/layers/[slug]/+page.svelte`, `src/routes/mvp/+page.svelte`, `src/routes/priorita/+page.svelte` — avvolgere tutto il markup top-level (dopo `<svelte:head>`) così:

```svelte
<div class="mx-auto max-w-6xl px-6 py-8">
	<!-- markup esistente invariato -->
</div>
```

(`+page.svelte` e `priorita/+page.svelte` verranno riscritte nei task 4 e 10 — il wrapper serve solo a non romperle nel frattempo.)

- [ ] **Step 4: Verifica**

Run: `pnpm check` → 0 errors. Su http://localhost:5173: header nuovo con nav alle 4 sezioni (link 404 per ora: atteso), `/mvp` e `/priorita` ancora funzionanti e leggibili.

- [ ] **Step 5: Commit**

```bash
git add work/map/web/src
git commit -m "ui: shell viewport pieno — header fisso, nav 4 sezioni, pagine wrappate"
```

---

### Task 3: `lib/server/layers.ts` — loader condiviso del catalogo

**Files:**
- Create: `src/lib/server/layers.ts`

- [ ] **Step 1: Creare il file** (è l'estrazione di `Row`/`toLayer` da `src/routes/mvp/+page.server.ts`, con selezione per slug in ordine di disegno)

```ts
import { db } from '$lib/server/db';
import type { Layer } from '$lib/types';

interface Row {
	id: number; slug: string; title: string; description: string | null;
	kind: 'vector' | 'raster'; geom_type: 'point' | 'line' | 'polygon' | null;
	source_table: string | null; cog_path: string | null;
	lng: number; lat: number; default_zoom: number;
	style: Record<string, unknown> | null; tags: string[];
	source_url: string | null; published_at: Date;
}

function toLayer(r: Row): Layer {
	return {
		id: r.id, slug: r.slug, title: r.title, description: r.description,
		kind: r.kind, geomType: r.geom_type, sourceTable: r.source_table,
		cogPath: r.cog_path, defaultCenter: [r.lng, r.lat],
		defaultZoom: r.default_zoom, style: r.style, tags: r.tags,
		sourceUrl: r.source_url, publishedAt: r.published_at.toISOString(),
	};
}

/**
 * Carica layer dal catalogo. Con `slugs` restituisce SOLO quelli richiesti,
 * nell'ordine dato (= ordine di disegno sulla mappa: il primo sta sotto).
 */
export async function loadLayers(slugs?: string[]): Promise<Layer[]> {
	const result = await db.query<Row>(
		`SELECT id, slug, title, description, kind, geom_type,
		        source_table, cog_path,
		        ST_X(default_center) AS lng, ST_Y(default_center) AS lat,
		        default_zoom, style, tags, source_url, published_at
		 FROM public.layers
		 ${slugs ? 'WHERE slug = ANY($1)' : ''}
		 ORDER BY published_at DESC`,
		slugs ? [slugs] : [],
	);
	const bySlug = new Map(result.rows.map((r) => [r.slug, toLayer(r)]));
	if (!slugs) return [...bySlug.values()];
	return slugs.map((s) => bySlug.get(s)).filter((l): l is Layer => l !== undefined);
}
```

- [ ] **Step 2: Verifica e commit**

Run: `pnpm check` → 0 errors.

```bash
git add work/map/web/src/lib/server/layers.ts
git commit -m "ui: loadLayers — loader condiviso del catalogo per le sezioni"
```

---

### Task 4: Home nuova — 4 card + numeri chiave

**Files:**
- Create/Overwrite: `src/routes/+page.server.ts`
- Overwrite: `src/routes/+page.svelte`

- [ ] **Step 1: `src/routes/+page.server.ts`**

```ts
import { db } from '$lib/server/db';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	const [acc, seg, segn] = await Promise.all([
		db.query<{ n: string; morti: string; feriti: string }>(
			`SELECT count(*) AS n, COALESCE(sum(tot_morti), 0) AS morti,
			        COALESCE(sum(tot_feriti), 0) AS feriti
			 FROM data.accidents`,
		),
		db.query<{ km: string; critiche: string; totale: string }>(
			`SELECT round(sum(lunghezza_m) / 1000.0) AS km,
			        count(*) FILTER (WHERE indice >= 70) AS critiche,
			        count(*) AS totale
			 FROM data.road_segments`,
		),
		// la tabella nasce nel task 11: prima di allora il fallback è 0
		db
			.query<{ n: string }>(`SELECT count(*) AS n FROM data.segnalazioni`)
			.catch(() => ({ rows: [{ n: '0' }] })),
	]);

	return {
		kpi: {
			incidenti: Number(acc.rows[0].n),
			morti: Number(acc.rows[0].morti),
			feriti: Number(acc.rows[0].feriti),
			km: Number(seg.rows[0].km),
			critiche: Number(seg.rows[0].critiche),
			totale: Number(seg.rows[0].totale),
			segnalazioni: Number(segn.rows[0].n),
		},
	};
};
```

- [ ] **Step 2: `src/routes/+page.svelte`**

```svelte
<script lang="ts">
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const CARDS = [
		{
			href: '/analisi', icona: '📊', titolo: 'Analisi storica',
			testo: 'Dove e perché succedono gli incidenti: mappa e fattori, dal 2010 a oggi.',
			kpi: `${data.kpi.incidenti} incidenti analizzati`,
		},
		{
			href: '/previsione', icona: '🌦', titolo: 'Previsione',
			testo: 'Quanto diventa rischiosa ogni tratta quando cambiano meteo e orario.',
			kpi: 'rischio per scenario',
		},
		{
			href: '/priorita', icona: '🛠', titolo: 'Piano manutenzioni',
			testo: 'Dove intervenire prima: comuni, strade e tratte in ordine di priorità.',
			kpi: `${data.kpi.critiche} tratte critiche su ${data.kpi.totale}`,
		},
		{
			href: '/cittadino', icona: '👥', titolo: 'Cittadino',
			testo: 'La mappa pubblica del rischio e le segnalazioni di chi la strada la vive.',
			kpi: `${data.kpi.segnalazioni} segnalazioni ricevute`,
		},
	];
</script>

<svelte:head>
	<title>SaferRoads Vicenza</title>
</svelte:head>

<div class="mx-auto max-w-5xl px-4 sm:px-6 py-8 sm:py-12">
	<h1 class="text-3xl font-bold tracking-tight">Strade più sicure, decisioni più semplici.</h1>
	<p class="mt-2 max-w-2xl text-neutral-600">
		Il rischio di incidente sulle strade provinciali di Vicenza, spiegato in modo che chiunque
		possa capirlo — e usarlo per decidere.
	</p>

	<div class="mt-6 flex flex-wrap gap-3">
		<div class="rounded-xl border border-neutral-200 bg-white px-5 py-3">
			<div class="text-2xl font-bold">{data.kpi.incidenti}</div>
			<div class="text-xs text-neutral-500">incidenti 2010–2023</div>
		</div>
		<div class="rounded-xl border border-neutral-200 bg-white px-5 py-3">
			<div class="text-2xl font-bold">{data.kpi.km} km</div>
			<div class="text-xs text-neutral-500">di strade monitorate</div>
		</div>
		<div class="rounded-xl border border-red-100 bg-red-50 px-5 py-3">
			<div class="text-2xl font-bold text-red-700">{data.kpi.critiche}</div>
			<div class="text-xs text-red-600">tratte a rischio critico</div>
		</div>
	</div>

	<div class="mt-8 grid gap-4 sm:grid-cols-2">
		{#each CARDS as card (card.href)}
			<a
				href={card.href}
				class="group rounded-2xl border border-neutral-200 bg-white p-5 transition hover:border-blue-300 hover:shadow-md"
			>
				<div class="text-2xl">{card.icona}</div>
				<h2 class="mt-2 text-lg font-semibold group-hover:text-blue-800">{card.titolo}</h2>
				<p class="mt-1 text-sm text-neutral-600">{card.testo}</p>
				<div class="mt-3 text-xs font-medium text-blue-700">{card.kpi} →</div>
			</a>
		{/each}
	</div>

	<p class="mt-8 text-xs text-neutral-400">
		Corridoi SP 46 Pasubio · SP 349 Costo · SP 350 Val d'Astico — dati Provincia di Vicenza,
		ARPAV, OpenStreetMap.
	</p>
</div>
```

- [ ] **Step 3: Verifica**

Run: `pnpm check` → 0 errors. Su http://localhost:5173/: 3 KPI reali (738 incidenti, ~144 km), 4 card; nessun gergo tecnico visibile.

- [ ] **Step 4: Commit**

```bash
git add work/map/web/src/routes/+page.server.ts work/map/web/src/routes/+page.svelte
git commit -m "ui: home a 4 card con numeri chiave"
```

---

### Task 5: API `GET /api/tratte/[id]` — dati della scheda tratta

**Files:**
- Create: `src/routes/api/tratte/[id]/+server.ts`
- Modify: `src/lib/types.ts` (aggiunta interfaccia in coda)

- [ ] **Step 1: Aggiungere a `src/lib/types.ts`**

```ts
export interface TrattaDetail {
	segment: {
		id: number; nome_strada: string; km_idx: number; comune: string | null;
		lunghezza_m: number; n_incidenti: number; tot_morti: number; tot_feriti: number;
		n_solo_danni: number; indice: number; indice_grezzo: number;
		n_attraversamenti: number | null; n_semafori: number | null; n_stop: number | null;
		n_incroci: number | null; n_autovelox: number | null; n_lampioni: number | null;
		maxspeed_med: number | null; lng: number; lat: number;
	};
	cause: { natura: string; n: number }[];
	scenari: { meteo: string; fascia_oraria: string; risk: number }[];
	posizione: number;
	totale: number;
}
```

- [ ] **Step 2: Creare `src/routes/api/tratte/[id]/+server.ts`**

```ts
import { json, error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import type { RequestHandler } from './$types';

// GET /api/tratte/42 → TrattaDetail (vedi lib/types.ts)
export const GET: RequestHandler = async ({ params }) => {
	const id = Number(params.id);
	if (!Number.isInteger(id) || id <= 0) throw error(400, 'Identificativo tratta non valido');

	const seg = await db.query(
		`SELECT id, nome_strada, km_idx, comune, lunghezza_m,
		        n_incidenti, tot_morti, tot_feriti, n_solo_danni,
		        indice, indice_grezzo,
		        n_attraversamenti, n_semafori, n_stop, n_incroci, n_autovelox, n_lampioni,
		        maxspeed_med,
		        ST_X(ST_Centroid(geom)) AS lng, ST_Y(ST_Centroid(geom)) AS lat
		 FROM data.road_segments WHERE id = $1`,
		[id],
	);
	if (!seg.rowCount) throw error(404, 'Tratta non trovata');

	const [cause, scenari, rank] = await Promise.all([
		// Incidenti il cui segmento più vicino è questo, entro 300 m:
		// stesso criterio di assegnazione di work/src/build_road_segments.py.
		db.query(
			`SELECT a.natura, count(*)::int AS n
			 FROM data.accidents a
			 WHERE a.natura IS NOT NULL
			   AND ST_DWithin(a.geom::geography,
			                  (SELECT geom::geography FROM data.road_segments WHERE id = $1), 300)
			   AND (SELECT rs.id FROM data.road_segments rs
			        ORDER BY rs.geom <-> a.geom LIMIT 1) = $1
			 GROUP BY a.natura ORDER BY n DESC`,
			[id],
		),
		db.query(
			`SELECT meteo, fascia_oraria, risk FROM data.segment_risk WHERE segment_id = $1`,
			[id],
		),
		db.query(
			`SELECT count(*)::int + 1 AS posizione,
			        (SELECT count(*)::int FROM data.road_segments) AS totale
			 FROM data.road_segments
			 WHERE indice > (SELECT indice FROM data.road_segments WHERE id = $1)`,
			[id],
		),
	]);

	return json({
		segment: seg.rows[0],
		cause: cause.rows,
		scenari: scenari.rows,
		posizione: rank.rows[0].posizione,
		totale: rank.rows[0].totale,
	});
};
```

- [ ] **Step 3: Verifica con curl**

```bash
curl -s http://localhost:5173/api/tratte/1 | python3 -m json.tool | head -30
```
Expected: JSON con chiavi `segment` (con `nome_strada`, `indice`), `cause` (array con `natura`/`n`), `scenari` (24 righe meteo×fascia), `posizione`, `totale` (=179).
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/api/tratte/99999   # → 404
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:5173/api/tratte/abc     # → 400
```

- [ ] **Step 4: Commit**

```bash
git add work/map/web/src/routes/api/tratte work/map/web/src/lib/types.ts
git commit -m "api: GET /api/tratte/[id] — anagrafica, cause, scenari, ranking"
```

---

### Task 6: Componente `SectionMap` — mappa full-height per le sezioni

**Files:**
- Create: `src/lib/components/SectionMap.svelte`

- [ ] **Step 1: Creare il componente**

```svelte
<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { Snippet } from 'svelte';
	import maplibregl from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';

	import type { Layer } from '$lib/types';
	import { martinSource } from '$lib/tiles/martin';
	import { defaults } from '$lib/style/defaults';
	import { applyStyle } from '$lib/style/apply';

	type GeoJsonLayer = {
		id: string;
		data: GeoJSON.FeatureCollection;
		paint: Record<string, unknown>;
	};

	let {
		layers,
		visible,
		interactive = [],
		lineColorBySlug = {},
		filterBySlug = {},
		geojsonLayers = [],
		center = [11.35, 45.65] as [number, number],
		zoom = 10,
		flyTarget = null,
		onFeatureClick,
		onMapClick,
		children,
	}: {
		layers: Layer[];
		visible: Set<string>;
		interactive?: string[];
		lineColorBySlug?: Record<string, unknown>;
		filterBySlug?: Record<string, unknown>;
		geojsonLayers?: GeoJsonLayer[];
		center?: [number, number];
		zoom?: number;
		flyTarget?: { center: [number, number]; zoom: number } | null;
		onFeatureClick?: (
			id: string,
			props: Record<string, unknown>,
			lngLat: { lng: number; lat: number },
		) => void;
		onMapClick?: (lngLat: { lng: number; lat: number }) => void;
		children?: Snippet;
	} = $props();

	let container: HTMLDivElement | undefined = $state();
	let map: maplibregl.Map | undefined;
	let mapReady = $state(false);

	const BASEMAP: maplibregl.StyleSpecification = {
		version: 8,
		sources: {
			osm: {
				type: 'raster',
				tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
				tileSize: 256,
				attribution: '© OpenStreetMap contributors',
			},
		},
		layers: [{ id: 'osm', type: 'raster', source: 'osm' }],
	};

	function mlId(slug: string) {
		return `sm-${slug}`;
	}

	function attachClick(slug: string, id: string) {
		if (!map) return;
		map.on('click', id, (e) => {
			const f = e.features?.[0];
			if (f && onFeatureClick) onFeatureClick(slug, f.properties ?? {}, e.lngLat);
		});
		map.on('mouseenter', id, () => { if (map) map.getCanvas().style.cursor = 'pointer'; });
		map.on('mouseleave', id, () => { if (map) map.getCanvas().style.cursor = ''; });
	}

	onMount(() => {
		if (!container) return;
		map = new maplibregl.Map({ container, style: BASEMAP, center, zoom });
		map.addControl(new maplibregl.NavigationControl(), 'top-right');

		map.on('load', () => {
			if (!map) return;
			// layers in ordine: il primo dell'array sta sotto
			for (const layer of layers) {
				if (layer.kind !== 'vector' || !layer.sourceTable || !layer.geomType) continue;
				map.addSource(`src-${layer.slug}`, martinSource(layer.sourceTable));
				const { filters: _f, legend: _l, minzoom: _mz, ...mapStyle } =
					(layer.style ?? {}) as Record<string, unknown>;
				const base = defaults.vector[layer.geomType] as Record<string, unknown>;
				const merged = applyStyle(
					Object.keys(mapStyle).length ? mapStyle : null, base, layer.sourceTable,
				) as Record<string, unknown>;
				const spec: Record<string, unknown> = {
					...merged,
					id: mlId(layer.slug),
					source: `src-${layer.slug}`,
					layout: {
						...((merged.layout as Record<string, unknown>) ?? {}),
						visibility: visible.has(layer.slug) ? 'visible' : 'none',
					},
				};
				if (typeof _mz === 'number') spec['minzoom'] = _mz;
				map.addLayer(spec as maplibregl.LayerSpecification);
				if (interactive.includes(layer.slug)) attachClick(layer.slug, mlId(layer.slug));
			}

			if (onMapClick) {
				map.on('click', (e) => {
					// non intercettare i click già gestiti dai layer interattivi
					const ids = interactive.map(mlId).filter((id) => map!.getLayer(id));
					const hit = ids.length ? map!.queryRenderedFeatures(e.point, { layers: ids }) : [];
					if (!hit.length) onMapClick(e.lngLat);
				});
			}

			mapReady = true;
		});
	});

	$effect(() => {
		if (!map || !mapReady) return;
		for (const [slug, expr] of Object.entries(lineColorBySlug))
			if (map.getLayer(mlId(slug)))
				map.setPaintProperty(mlId(slug), 'line-color', expr as never);
	});

	$effect(() => {
		if (!map || !mapReady) return;
		for (const [slug, filter] of Object.entries(filterBySlug))
			if (map.getLayer(mlId(slug)))
				map.setFilter(mlId(slug), filter as maplibregl.FilterSpecification | null);
	});

	$effect(() => {
		if (!map || !mapReady) return;
		for (const gl of geojsonLayers) {
			const src = map.getSource(`gj-${gl.id}`) as maplibregl.GeoJSONSource | undefined;
			if (src) {
				src.setData(gl.data);
				continue;
			}
			map.addSource(`gj-${gl.id}`, { type: 'geojson', data: gl.data });
			map.addLayer({
				id: mlId(gl.id),
				source: `gj-${gl.id}`,
				type: 'circle',
				paint: gl.paint,
			} as maplibregl.LayerSpecification);
			if (interactive.includes(gl.id)) attachClick(gl.id, mlId(gl.id));
		}
	});

	$effect(() => {
		if (!map || !mapReady || !flyTarget) return;
		map.flyTo({ center: flyTarget.center, zoom: flyTarget.zoom });
	});

	onDestroy(() => map?.remove());
</script>

<div class="relative h-full w-full overflow-hidden">
	<div bind:this={container} class="absolute inset-0"></div>
	{@render children?.()}
</div>
```

- [ ] **Step 2: Verifica e commit**

Run: `pnpm check` → 0 errors (il componente non è ancora usato: basta che compili).

```bash
git add work/map/web/src/lib/components/SectionMap.svelte
git commit -m "ui: SectionMap — mappa full-height con pannelli flottanti via snippet"
```

---

### Task 7: Componente `SchedaTratta` — drill-down condiviso

**Files:**
- Create: `src/lib/components/SchedaTratta.svelte`

- [ ] **Step 1: Creare il componente**

```svelte
<script lang="ts">
	import type { TrattaDetail } from '$lib/types';
	import {
		livelloIndice, livelloRisk, frasePosizione, riskColor,
		SCENARIO_METEO, SCENARIO_FASCE,
	} from '$lib/risk';

	let {
		segmentId,
		scenario = null,
		variant = 'full',
		onClose,
	}: {
		segmentId: number;
		scenario?: { meteo: string; fascia: string } | null;
		variant?: 'full' | 'ridotta';
		onClose?: () => void;
	} = $props();

	let detail = $state<TrattaDetail | null>(null);
	let err = $state('');
	let loading = $state(true);

	$effect(() => {
		const id = segmentId;
		loading = true;
		err = '';
		detail = null;
		fetch(`/api/tratte/${id}`)
			.then(async (r) => {
				if (!r.ok) throw new Error((await r.json())?.message ?? r.statusText);
				return r.json();
			})
			.then((d: TrattaDetail) => { detail = d; })
			.catch((e) => { err = e instanceof Error ? e.message : 'Errore di caricamento'; })
			.finally(() => { loading = false; });
	});

	const liv = $derived(detail ? livelloIndice(detail.segment.indice) : null);
	const scenRisk = $derived.by(() => {
		if (!detail || !scenario) return null;
		const row = detail.scenari.find(
			(s) => s.meteo === scenario.meteo && s.fascia_oraria === scenario.fascia,
		);
		return row ? row.risk : null;
	});
	const causeMax = $derived(detail?.cause[0]?.n ?? 1);

	const DOTAZIONI: { key: keyof TrattaDetail['segment']; label: string }[] = [
		{ key: 'n_attraversamenti', label: 'Attraversamenti' },
		{ key: 'n_semafori', label: 'Semafori' },
		{ key: 'n_stop', label: 'Stop' },
		{ key: 'n_incroci', label: 'Incroci/rotatorie' },
		{ key: 'n_autovelox', label: 'Autovelox' },
		{ key: 'n_lampioni', label: 'Lampioni' },
	];

	function riskCell(meteo: string, fascia: string): number | null {
		const row = detail?.scenari.find((s) => s.meteo === meteo && s.fascia_oraria === fascia);
		return row ? row.risk : null;
	}
</script>

<div class="h-full flex flex-col rounded-t-2xl md:rounded-xl bg-white shadow-xl border border-neutral-200 overflow-hidden">
	<div class="shrink-0 flex items-start justify-between gap-2 border-b border-neutral-100 px-4 py-3">
		<div>
			{#if detail}
				<h2 class="font-semibold leading-tight">
					{detail.segment.nome_strada} — km {detail.segment.km_idx}
				</h2>
				<p class="text-xs text-neutral-500">{detail.segment.comune ?? 'Comune non assegnato'}</p>
			{:else}
				<h2 class="font-semibold text-neutral-400">Tratta…</h2>
			{/if}
		</div>
		{#if onClose}
			<button
				onclick={onClose}
				class="rounded-md px-2 py-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
				aria-label="Chiudi"
			>✕</button>
		{/if}
	</div>

	<div class="flex-1 overflow-y-auto px-4 py-3 text-sm">
		{#if loading}
			<p class="text-neutral-400">Caricamento…</p>
		{:else if err}
			<p class="text-red-600">{err}</p>
		{:else if detail && liv}
			<!-- livello -->
			{#if scenario}
				{#if scenRisk != null}
					<div class="rounded-lg px-3 py-2 {livelloRisk(scenRisk).badge}">
						<span class="text-lg font-bold">● {livelloRisk(scenRisk).label}</span>
						<span class="text-xs"> con {scenario.meteo.toLowerCase()} · {scenario.fascia.toLowerCase()}</span>
					</div>
				{:else}
					<div class="rounded-lg bg-neutral-100 px-3 py-2 text-neutral-500 text-xs">
						Previsione non disponibile per questo scenario.
					</div>
				{/if}
			{:else}
				<div class="rounded-lg px-3 py-2 {liv.badge}">
					<span class="text-lg font-bold">● {liv.label}</span>
					<span class="text-xs"> rischio storico · indice {detail.segment.indice.toFixed(0)}/100</span>
				</div>
			{/if}
			<p class="mt-2 text-neutral-700">{frasePosizione(detail.posizione, detail.totale)}</p>

			<!-- storia -->
			<h3 class="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">
				Cosa è successo qui (2010–2023)
			</h3>
			<div class="mt-1 grid grid-cols-3 gap-2 text-center">
				<div class="rounded-lg bg-neutral-50 py-2">
					<div class="font-bold">{detail.segment.n_incidenti}</div>
					<div class="text-[11px] text-neutral-500">incidenti</div>
				</div>
				<div class="rounded-lg bg-neutral-50 py-2">
					<div class="font-bold {detail.segment.tot_morti > 0 ? 'text-red-700' : ''}">
						{detail.segment.tot_morti}
					</div>
					<div class="text-[11px] text-neutral-500">morti</div>
				</div>
				<div class="rounded-lg bg-neutral-50 py-2">
					<div class="font-bold">{detail.segment.tot_feriti}</div>
					<div class="text-[11px] text-neutral-500">feriti</div>
				</div>
			</div>

			<!-- cause -->
			{#if detail.cause.length}
				<h3 class="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">
					Cause più frequenti
				</h3>
				<div class="mt-1 flex flex-col gap-1">
					{#each detail.cause.slice(0, 5) as c (c.natura)}
						<div class="flex items-center gap-2 text-xs">
							<span class="w-32 shrink-0 truncate text-neutral-600" title={c.natura}>{c.natura}</span>
							<div class="h-2 rounded bg-blue-200" style="width:{(c.n / causeMax) * 100}%"></div>
							<span class="text-neutral-400">{c.n}</span>
						</div>
					{/each}
				</div>
			{/if}

			{#if variant === 'full'}
				<!-- dotazioni -->
				<h3 class="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">
					Sicurezza presente sulla tratta
				</h3>
				<div class="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
					{#each DOTAZIONI as d (d.key)}
						<div class="flex justify-between border-b border-neutral-50 py-0.5">
							<span class="text-neutral-600">{d.label}</span>
							<span class="font-medium">{detail.segment[d.key] ?? '—'}</span>
						</div>
					{/each}
				</div>

				<!-- griglia scenari -->
				{#if detail.scenari.length}
					<h3 class="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">
						Rischio previsto per scenario
					</h3>
					<table class="mt-1 w-full text-[10px]">
						<thead>
							<tr>
								<th class="text-left font-normal text-neutral-400"></th>
								{#each SCENARIO_FASCE as f (f)}
									<th class="font-normal text-neutral-400">{f}</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each SCENARIO_METEO as m (m)}
								<tr>
									<td class="pr-1 text-neutral-500">{m}</td>
									{#each SCENARIO_FASCE as f (f)}
										{@const r = riskCell(m, f)}
										<td class="p-0.5 text-center">
											{#if r != null}
												<div
													class="rounded py-0.5 font-medium text-white"
													style="background:{riskColor(r)}"
													title="{livelloRisk(r).label}"
												>
													{(r * 100).toFixed(0)}%
												</div>
											{:else}
												<div class="rounded bg-neutral-100 py-0.5 text-neutral-400">—</div>
											{/if}
										</td>
									{/each}
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}

				<!-- dettagli tecnici -->
				<details class="mt-4">
					<summary class="cursor-pointer text-xs text-neutral-400 hover:text-neutral-600">
						Dettagli tecnici
					</summary>
					<div class="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px] text-neutral-500">
						<span>indice: {detail.segment.indice.toFixed(1)}</span>
						<span>indice grezzo: {detail.segment.indice_grezzo.toFixed(3)}</span>
						<span>lunghezza: {detail.segment.lunghezza_m} m</span>
						<span>solo danni: {detail.segment.n_solo_danni}</span>
						<span>limite mediano: {detail.segment.maxspeed_med ?? '—'} km/h</span>
						<span>id segmento: {detail.segment.id}</span>
					</div>
				</details>
			{/if}
		{/if}
	</div>
</div>
```

- [ ] **Step 2: Verifica e commit**

Run: `pnpm check` → 0 errors.

```bash
git add work/map/web/src/lib/components/SchedaTratta.svelte
git commit -m "ui: SchedaTratta — drill-down in linguaggio semplice"
```

---

### Task 8: Sezione `/previsione`

**Files:**
- Create: `src/routes/previsione/+page.server.ts`
- Create: `src/routes/previsione/+page.svelte`

- [ ] **Step 1: `src/routes/previsione/+page.server.ts`**

```ts
import { readFile } from 'node:fs/promises';
import { loadLayers } from '$lib/server/layers';
import type { PageServerLoad } from './$types';

// Contratto 4 (Daghem): se il file non esiste il riquadro A3 non si renderizza.
// In dev il cwd è work/map/web → il file sta in work/output/.
const FI_PATH = '../../output/feature_importance.json';

export const load: PageServerLoad = async () => {
	let featureImportance: { feature: string; importance: number }[] | null = null;
	try {
		const parsed = JSON.parse(await readFile(FI_PATH, 'utf8'));
		if (Array.isArray(parsed)) featureImportance = parsed;
	} catch {
		featureImportance = null; // file assente: nessun errore (da spec)
	}
	return {
		layers: await loadLayers(['osm-roads', 'rischio-storico']),
		featureImportance,
	};
};
```

- [ ] **Step 2: `src/routes/previsione/+page.svelte`**

```svelte
<script lang="ts">
	import SectionMap from '$lib/components/SectionMap.svelte';
	import SchedaTratta from '$lib/components/SchedaTratta.svelte';
	import {
		STORICO_COLOR, riskColor, livelloIndice, SCENARIO_METEO, SCENARIO_FASCE,
	} from '$lib/risk';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// strade di contesto: solo viabilità principale, in grigio
	const ROAD_CTX = ['in', ['get', 'fclass'], ['literal', [
		'motorway', 'motorway_link', 'trunk', 'trunk_link',
		'primary', 'primary_link', 'secondary', 'secondary_link',
	]]];

	let meteo = $state('');
	let fascia = $state('');
	let lineColor = $state<unknown>(STORICO_COLOR);
	let errore = $state('');
	let selected = $state<number | null>(null);

	const scenarioAttivo = $derived(Boolean(meteo && fascia));

	async function applicaScenario() {
		errore = '';
		if (!meteo || !fascia) {
			lineColor = STORICO_COLOR;
			return;
		}
		try {
			const res = await fetch(
				`/api/segment-risk?meteo=${encodeURIComponent(meteo)}&fascia=${encodeURIComponent(fascia)}`,
			);
			if (!res.ok) throw new Error((await res.json())?.message ?? res.statusText);
			const risk: Record<string, number> = await res.json();
			const expr: unknown[] = ['match', ['get', 'id']];
			for (const [id, r] of Object.entries(risk)) expr.push(Number(id), riskColor(r));
			expr.push('#9ca3af'); // tratte senza predizione
			lineColor = expr;
		} catch (e) {
			errore = e instanceof Error ? e.message : 'Previsione non disponibile per questo scenario';
			lineColor = STORICO_COLOR;
		}
	}

	const LIVELLI = [livelloIndice(0), livelloIndice(20), livelloIndice(50), livelloIndice(80)];
</script>

<svelte:head>
	<title>Previsione · SaferRoads Vicenza</title>
</svelte:head>

<div class="h-full">
	<SectionMap
		layers={data.layers}
		visible={new Set(['osm-roads', 'rischio-storico'])}
		interactive={['rischio-storico']}
		lineColorBySlug={{ 'rischio-storico': lineColor, 'osm-roads': '#cbd5e1' }}
		filterBySlug={{ 'osm-roads': ROAD_CTX }}
		onFeatureClick={(slug, props) => { selected = Number(props.id); }}
	>
		<!-- pannello scenario -->
		<div class="absolute left-3 top-3 z-10 w-64 rounded-xl border border-neutral-200 bg-white p-3 shadow-lg">
			<h1 class="text-sm font-semibold">Che rischio c'è…</h1>
			<label class="mt-2 block text-xs text-neutral-500">
				con questo meteo
				<select
					bind:value={meteo}
					onchange={applicaScenario}
					class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
				>
					<option value="">— storico —</option>
					{#each SCENARIO_METEO as m (m)}<option value={m}>{m}</option>{/each}
				</select>
			</label>
			<label class="mt-2 block text-xs text-neutral-500">
				in questa fascia oraria
				<select
					bind:value={fascia}
					onchange={applicaScenario}
					class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
				>
					<option value="">— storico —</option>
					{#each SCENARIO_FASCE as f (f)}<option value={f}>{f}</option>{/each}
				</select>
			</label>
			<p class="mt-2 text-xs leading-snug {errore ? 'text-red-600' : 'text-neutral-500'}">
				{#if errore}{errore}
				{:else if scenarioAttivo}
					Le tratte sono colorate col rischio previsto. Clicca una tratta per i dettagli.
				{:else}
					Scegli meteo e fascia oraria, oppure clicca una tratta per il rischio storico.
				{/if}
			</p>
		</div>

		<!-- fattori di rischio (A3) — solo se Daghem ha consegnato il contratto 4 -->
		{#if data.featureImportance?.length}
			{@const fiMax = data.featureImportance[0].importance || 1}
			<div class="absolute left-3 top-[15.5rem] z-10 hidden w-64 rounded-xl border border-neutral-200 bg-white p-3 shadow-lg md:block">
				<h2 class="text-xs font-semibold uppercase tracking-wide text-neutral-400">
					Cosa pesa di più sul rischio
				</h2>
				<div class="mt-1.5 flex flex-col gap-1">
					{#each data.featureImportance.slice(0, 6) as fi (fi.feature)}
						<div class="flex items-center gap-2 text-xs">
							<span class="w-24 shrink-0 truncate text-neutral-600" title={fi.feature}>{fi.feature}</span>
							<div class="h-2 rounded bg-blue-300" style="width:{(fi.importance / fiMax) * 100}%"></div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- legenda -->
		<div class="absolute bottom-3 left-3 z-10 flex gap-3 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs shadow-lg">
			{#each LIVELLI as l (l.label)}
				<span class="flex items-center gap-1">
					<span class="h-2.5 w-2.5 rounded-full" style="background:{l.color}"></span>{l.label}
				</span>
			{/each}
		</div>

		<!-- scheda tratta: bottom-sheet su mobile, pannello dx su desktop -->
		{#if selected != null}
			<div class="absolute inset-x-0 bottom-0 z-20 max-h-[60%] md:inset-x-auto md:bottom-3 md:right-3 md:top-3 md:w-96 md:max-h-none">
				<SchedaTratta
					segmentId={selected}
					scenario={scenarioAttivo ? { meteo, fascia } : null}
					onClose={() => (selected = null)}
				/>
			</div>
		{/if}
	</SectionMap>
</div>
```

- [ ] **Step 3: Verifica**

Run: `pnpm check` → 0 errors. Su http://localhost:5173/previsione:
1. Nessuno scroll di pagina; mappa piena sotto l'header.
2. Meteo "Pioggia" + fascia "Notte" → tratte ricolorate.
3. Clic su una tratta → scheda a destra con "● {LIVELLO} con pioggia · notte", frase, storia, cause, griglia scenari.
4. Finestra stretta (≈390 px, devtools) → la scheda è un bottom-sheet, i pannelli non si sovrappongono.

- [ ] **Step 4: Commit**

```bash
git add work/map/web/src/routes/previsione
git commit -m "ui: sezione /previsione — scenario, mappa full-height, scheda tratta"
```

---

### Task 9: Sezione `/analisi`

**Files:**
- Create: `src/routes/analisi/+page.server.ts`
- Create: `src/routes/analisi/+page.svelte`

- [ ] **Step 1: `src/routes/analisi/+page.server.ts`**

```ts
import { db } from '$lib/server/db';
import { loadLayers } from '$lib/server/layers';
import type { PageServerLoad } from './$types';

// Campi filtrabili di data.accidents (identificatori costanti, interpolazione sicura).
const FIELDS = [
	'anno', 'mese', 'giorno_settimana', 'fascia_oraria', 'comune',
	'nome_strada', 'natura', 'fondo', 'meteo', 'gravita',
];

export const load: PageServerLoad = async ({ url }) => {
	const layers = await loadLayers(['osm-roads', 'rischio-storico', 'incidenti-vicenza']);

	const filterOptions: Record<string, (string | number)[]> = {};
	for (const f of FIELDS) {
		const res = await db.query<{ v: string | number }>(
			`SELECT DISTINCT "${f}" AS v FROM data.accidents WHERE "${f}" IS NOT NULL ORDER BY v`,
		);
		filterOptions[f] = res.rows.map((r) => r.v);
	}

	// ?tratta=ID (arrivo da /priorita): centra la mappa e apre la scheda
	let trattaIniziale: { id: number; lng: number; lat: number } | null = null;
	const tratta = Number(url.searchParams.get('tratta'));
	if (Number.isInteger(tratta) && tratta > 0) {
		const r = await db.query<{ id: number; lng: number; lat: number }>(
			`SELECT id, ST_X(ST_Centroid(geom)) AS lng, ST_Y(ST_Centroid(geom)) AS lat
			 FROM data.road_segments WHERE id = $1`,
			[tratta],
		);
		trattaIniziale = r.rows[0] ?? null;
	}

	return { layers, filterOptions, trattaIniziale };
};
```

- [ ] **Step 2: `src/routes/analisi/+page.svelte`**

```svelte
<script lang="ts">
	import SectionMap from '$lib/components/SectionMap.svelte';
	import SchedaTratta from '$lib/components/SchedaTratta.svelte';
	import { livelloIndice } from '$lib/risk';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const MESI = [
		'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
		'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre',
	];
	const GIORNI = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica'];

	const PRINCIPALI = ['anno', 'meteo', 'gravita'];
	const SECONDARI = ['mese', 'giorno_settimana', 'fascia_oraria', 'comune', 'nome_strada', 'natura', 'fondo'];

	const LABELS: Record<string, string> = {
		anno: 'Anno', meteo: 'Meteo', gravita: 'Gravità', mese: 'Mese',
		giorno_settimana: 'Giorno', fascia_oraria: 'Fascia oraria',
		comune: 'Comune', nome_strada: 'Strada', natura: 'Natura', fondo: 'Fondo',
	};

	const ROAD_CTX = ['in', ['get', 'fclass'], ['literal', [
		'motorway', 'motorway_link', 'trunk', 'trunk_link',
		'primary', 'primary_link', 'secondary', 'secondary_link',
	]]];

	let sel = $state<Record<string, string>>({});
	let altriOpen = $state(false);
	let selected = $state<number | null>(data.trattaIniziale?.id ?? null);

	// etichette user-friendly (requisito C3): mesi a nome, giorni in ordine, anni decrescenti
	function opzioni(field: string): { value: string; label: string }[] {
		const vals = data.filterOptions[field] ?? [];
		if (field === 'mese')
			return vals.map((v) => ({ value: String(v), label: MESI[Number(v) - 1] ?? String(v) }));
		if (field === 'giorno_settimana')
			return [...vals]
				.sort((a, b) => GIORNI.indexOf(String(a)) - GIORNI.indexOf(String(b)))
				.map((v) => ({ value: String(v), label: String(v) }));
		if (field === 'anno')
			return [...vals]
				.sort((a, b) => Number(b) - Number(a))
				.map((v) => ({ value: String(v), label: String(v) }));
		return vals.map((v) => ({ value: String(v), label: String(v) }));
	}

	const accFilter = $derived.by(() => {
		const conds = Object.entries(sel)
			.filter(([, v]) => v !== '')
			.map(([f, v]) => {
				const typed = (data.filterOptions[f] ?? []).find((o) => String(o) === v) ?? v;
				return ['==', ['get', f], typed];
			});
		return conds.length ? ['all', ...conds] : null;
	});

	const nAttivi = $derived(Object.values(sel).filter((v) => v !== '').length);
	const LIVELLI = [livelloIndice(0), livelloIndice(20), livelloIndice(50), livelloIndice(80)];
</script>

<svelte:head>
	<title>Analisi storica · SaferRoads Vicenza</title>
</svelte:head>

<div class="h-full">
	<SectionMap
		layers={data.layers}
		visible={new Set(['osm-roads', 'rischio-storico', 'incidenti-vicenza'])}
		interactive={['rischio-storico']}
		lineColorBySlug={{ 'osm-roads': '#cbd5e1' }}
		filterBySlug={{ 'osm-roads': ROAD_CTX, 'incidenti-vicenza': accFilter }}
		flyTarget={data.trattaIniziale
			? { center: [data.trattaIniziale.lng, data.trattaIniziale.lat], zoom: 13 }
			: null}
		onFeatureClick={(slug, props) => { selected = Number(props.id); }}
	>
		<!-- pannello filtri -->
		<div class="absolute left-3 top-3 z-10 w-64 max-h-[calc(100%-1.5rem)] overflow-y-auto rounded-xl border border-neutral-200 bg-white p-3 shadow-lg">
			<h1 class="text-sm font-semibold">Gli incidenti, anno per anno</h1>
			<div class="mt-2 flex flex-col gap-2">
				{#each PRINCIPALI as f (f)}
					<label class="block text-xs text-neutral-500">
						{LABELS[f]}
						<select
							bind:value={sel[f]}
							class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
						>
							<option value="">Tutti</option>
							{#each opzioni(f) as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
						</select>
					</label>
				{/each}

				<button
					onclick={() => (altriOpen = !altriOpen)}
					class="mt-1 text-left text-xs font-medium text-blue-700 hover:underline"
				>
					{altriOpen ? '− Meno filtri' : `+ Altri filtri${nAttivi > 0 ? ` (${nAttivi} attivi)` : ''}`}
				</button>

				{#if altriOpen}
					{#each SECONDARI as f (f)}
						<label class="block text-xs text-neutral-500">
							{LABELS[f]}
							<select
								bind:value={sel[f]}
								class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
							>
								<option value="">Tutti</option>
								{#each opzioni(f) as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
							</select>
						</label>
					{/each}
				{/if}
			</div>
		</div>

		<!-- legenda -->
		<div class="absolute bottom-3 left-3 z-10 flex gap-3 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs shadow-lg">
			{#each LIVELLI as l (l.label)}
				<span class="flex items-center gap-1">
					<span class="h-2.5 w-2.5 rounded-full" style="background:{l.color}"></span>{l.label}
				</span>
			{/each}
			<span class="flex items-center gap-1 border-l border-neutral-200 pl-3">
				<span class="h-2.5 w-2.5 rounded-full bg-neutral-700"></span>incidente
			</span>
		</div>

		{#if selected != null}
			<div class="absolute inset-x-0 bottom-0 z-20 max-h-[60%] md:inset-x-auto md:bottom-3 md:right-3 md:top-3 md:w-96 md:max-h-none">
				<SchedaTratta segmentId={selected} onClose={() => (selected = null)} />
			</div>
		{/if}
	</SectionMap>
</div>
```

Nota: i filtri usano `bind:value` ma il filtro mappa passa per la prop reattiva `filterBySlug` di SectionMap (`$effect` → `map.setFilter`), quindi NON soffre del bug storico "bind+$effect non applicava il filtro" legato ai popup di LayerMap.

- [ ] **Step 3: Verifica**

Run: `pnpm check` → 0 errors. Su http://localhost:5173/analisi:
1. Mappa piena, niente scroll; punti incidente + tratte colorate visibili.
2. Filtro Meteo=Pioggia → restano solo gli incidenti con pioggia. "Altri filtri" → Mese mostra nomi ("Gennaio"), Giorno in ordine Lunedì→Domenica.
3. http://localhost:5173/analisi?tratta=1 → mappa centrata sulla tratta e scheda aperta.

- [ ] **Step 4: Commit**

```bash
git add work/map/web/src/routes/analisi
git commit -m "ui: sezione /analisi — filtri compatti user-friendly (C3) + scheda tratta"
```

---

### Task 10: `/priorita` gerarchica — Comune → Strada → Tratto

**Files:**
- Overwrite: `src/routes/priorita/+page.svelte` (il `+page.server.ts` resta invariato)

- [ ] **Step 1: Riscrivere `src/routes/priorita/+page.svelte`**

```svelte
<script lang="ts">
	import { livelloIndice } from '$lib/risk';
	import type { PageData } from './$types';
	import type { SegmentRow } from './+page.server';

	let { data }: { data: PageData } = $props();

	type StradaGruppo = { strada: string; max: number; n: number; tratti: SegmentRow[] };
	type ComuneGruppo = { comune: string; max: number; n: number; strade: StradaGruppo[] };

	const gruppi = $derived.by((): ComuneGruppo[] => {
		const byComune = new Map<string, SegmentRow[]>();
		for (const s of data.segments) {
			const key = s.comune ?? 'Comune non assegnato';
			if (!byComune.has(key)) byComune.set(key, []);
			byComune.get(key)!.push(s);
		}
		return [...byComune.entries()]
			.map(([comune, tratti]) => {
				const byStrada = new Map<string, SegmentRow[]>();
				for (const t of tratti) {
					if (!byStrada.has(t.nome_strada)) byStrada.set(t.nome_strada, []);
					byStrada.get(t.nome_strada)!.push(t);
				}
				const strade = [...byStrada.entries()]
					.map(([strada, ts]) => ({
						strada,
						max: Math.max(...ts.map((t) => t.indice)),
						n: ts.length,
						tratti: ts, // già ordinati per indice desc dal server
					}))
					.sort((a, b) => b.max - a.max);
				return {
					comune,
					max: Math.max(...tratti.map((t) => t.indice)),
					n: tratti.length,
					strade,
				};
			})
			.sort((a, b) => b.max - a.max);
	});

	let openComuni = $state<Set<string>>(new Set());
	let openStrade = $state<Set<string>>(new Set());

	function toggled(set: Set<string>, key: string): Set<string> {
		const next = new Set(set);
		if (next.has(key)) next.delete(key);
		else next.add(key);
		return next;
	}
</script>

<svelte:head>
	<title>Piano manutenzioni · SaferRoads Vicenza</title>
</svelte:head>

<div class="mx-auto max-w-4xl px-4 sm:px-6 py-8">
	<h1 class="text-2xl font-bold tracking-tight">Dove intervenire prima</h1>
	<p class="mt-1 text-sm text-neutral-600">
		Comuni, strade e tratte in ordine di pericolosità storica (2010–2023). Apri un comune per
		vedere le sue strade, una strada per vedere le singole tratte.
	</p>

	<div class="mt-6 flex flex-col gap-2">
		{#each gruppi as g (g.comune)}
			{@const livC = livelloIndice(g.max)}
			<div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
				<button
					onclick={() => (openComuni = toggled(openComuni, g.comune))}
					class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-neutral-50"
				>
					<span class="inline-block rounded-md px-2 py-0.5 text-xs font-semibold {livC.badge}">
						{livC.label}
					</span>
					<span class="font-medium">{g.comune}</span>
					<span class="ml-auto text-xs text-neutral-400">{g.n} tratte</span>
					<span class="text-neutral-400">{openComuni.has(g.comune) ? '▾' : '▸'}</span>
				</button>

				{#if openComuni.has(g.comune)}
					{#each g.strade as st (g.comune + st.strada)}
						{@const livS = livelloIndice(st.max)}
						{@const stradaKey = g.comune + '|' + st.strada}
						<button
							onclick={() => (openStrade = toggled(openStrade, stradaKey))}
							class="flex w-full items-center gap-3 border-t border-neutral-100 px-4 py-2 pl-8 text-left text-sm hover:bg-neutral-50"
						>
							<span class="inline-block rounded-md px-2 py-0.5 text-[11px] font-semibold {livS.badge}">
								{livS.label}
							</span>
							<span>{st.strada}</span>
							<span class="ml-auto text-xs text-neutral-400">{st.n} tratte</span>
							<span class="text-neutral-400">{openStrade.has(stradaKey) ? '▾' : '▸'}</span>
						</button>

						{#if openStrade.has(stradaKey)}
							{#each st.tratti as t (t.id)}
								{@const livT = livelloIndice(t.indice)}
								<div class="flex items-center gap-3 border-t border-neutral-50 px-4 py-1.5 pl-14 text-sm">
									<span class="inline-block rounded-md px-2 py-0.5 text-[11px] font-semibold {livT.badge}">
										{t.indice.toFixed(0)}
									</span>
									<span class="text-neutral-700">km {t.km_idx}</span>
									<span
										class="text-xs text-neutral-400"
										title="attraversamenti {t.n_attraversamenti ?? 0} · semafori {t.n_semafori ?? 0} · autovelox {t.n_autovelox ?? 0} · lampioni {t.n_lampioni ?? 0} · limite {t.maxspeed_med ?? '—'}"
									>
										{t.n_incidenti} incidenti
										{#if t.tot_morti > 0}<span class="font-semibold text-red-700"> · {t.tot_morti} morti</span>{/if}
										{#if t.tot_feriti > 0} · {t.tot_feriti} feriti{/if}
									</span>
									<a
										href={`/analisi?tratta=${t.id}`}
										class="ml-auto text-xs text-blue-700 hover:underline"
									>vedi su mappa →</a>
								</div>
							{/each}
						{/if}
					{/each}
				{/if}
			</div>
		{/each}
	</div>
</div>
```

- [ ] **Step 2: Verifica**

Run: `pnpm check` → 0 errors. Su http://localhost:5173/priorita:
1. Comuni in ordine di pericolosità con badge verbale; espandi → strade → tratte.
2. "vedi su mappa" su una tratta → `/analisi?tratta=N` centrata con scheda aperta.
3. Hover sui dati di una tratta → tooltip con i numeri tecnici (A/S/V/L, limite).

- [ ] **Step 3: Commit**

```bash
git add work/map/web/src/routes/priorita/+page.svelte
git commit -m "ui: /priorita gerarchica Comune → Strada → Tratto con badge verbali"
```

---

### Task 11: Tabella `data.segnalazioni` + seed + mount compose

**Files (relativi al root del repo):**
- Create: `work/map/infra/postgres/04-segnalazioni.sql`
- Modify: `work/map/docker-compose.yml` (volumes del servizio `db`)

- [ ] **Step 1: Creare `work/map/infra/postgres/04-segnalazioni.sql`**

```sql
-- Segnalazioni dei cittadini (sezione /cittadino della dashboard).
-- Scritta dall'API POST /api/segnalazioni; pubblicata da Martin come gli altri layer.

CREATE TABLE IF NOT EXISTS data.segnalazioni (
  id          bigserial PRIMARY KEY,
  tipo        text NOT NULL CHECK (tipo IN ('incidente_lieve', 'strada_danneggiata', 'pericolo')),
  descrizione text NOT NULL DEFAULT '',
  geom        geometry(Point, 4326) NOT NULL,
  created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS segnalazioni_geom_gist ON data.segnalazioni USING gist (geom);

INSERT INTO public.layers
  (slug, title, description, kind, geom_type, source_table, default_center, default_zoom, style, tags)
VALUES (
  'segnalazioni',
  'Segnalazioni dei cittadini',
  'Segnalazioni inviate dalla dashboard cittadino: incidenti lievi, strade danneggiate, situazioni di pericolo.',
  'vector', 'point', 'segnalazioni',
  ST_SetSRID(ST_MakePoint(11.35, 45.65), 4326), 10,
  '{"paint": {"circle-color": "#9c36b5", "circle-radius": 6, "circle-stroke-width": 2, "circle-stroke-color": "#ffffff"}}'::jsonb,
  ARRAY['soluzione', 'cittadino']
)
ON CONFLICT (slug) DO NOTHING;
```

- [ ] **Step 2: Montarlo in `work/map/docker-compose.yml`**

Nel servizio `db`, dopo la riga del seed `03-training.sql`, aggiungere:

```yaml
      - ./infra/postgres/04-segnalazioni.sql:/docker-entrypoint-initdb.d/04-segnalazioni.sql:ro
```

- [ ] **Step 3: Applicare al DB già in esecuzione (il seed vale solo per i boot freschi)**

```bash
cd work/map
docker compose exec -T db psql -U postgres -d geosentinel < infra/postgres/04-segnalazioni.sql
docker compose restart martin
```
Expected: `CREATE TABLE`, `CREATE INDEX`, `INSERT 0 1`.

- [ ] **Step 4: Verifica**

```bash
docker compose exec -T db psql -U postgres -d geosentinel -c "\d data.segnalazioni" | head -5
```
Expected: la tabella esiste con le 5 colonne.

- [ ] **Step 5: Commit**

```bash
git add work/map/infra/postgres/04-segnalazioni.sql work/map/docker-compose.yml
git commit -m "db: tabella data.segnalazioni + layer catalogo (seed 04)"
```

---

### Task 12: API `GET|POST /api/segnalazioni`

**Files:**
- Create: `src/routes/api/segnalazioni/+server.ts`

- [ ] **Step 1: Creare l'endpoint**

```ts
import { json, error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import type { RequestHandler } from './$types';

const TIPI = ['incidente_lieve', 'strada_danneggiata', 'pericolo'];
// bounding box larga della provincia di Vicenza: respinge coordinate palesemente sbagliate
const BBOX = { minLng: 10.8, maxLng: 12.2, minLat: 45.2, maxLat: 46.1 };

// GET /api/segnalazioni → GeoJSON FeatureCollection (per la mappa, aggiornabile live)
export const GET: RequestHandler = async () => {
	const res = await db.query<{
		id: number; tipo: string; descrizione: string; created_at: Date;
		lng: number; lat: number;
	}>(
		`SELECT id, tipo, descrizione, created_at,
		        ST_X(geom) AS lng, ST_Y(geom) AS lat
		 FROM data.segnalazioni ORDER BY created_at DESC LIMIT 500`,
	);
	return json({
		type: 'FeatureCollection',
		features: res.rows.map((r) => ({
			type: 'Feature',
			geometry: { type: 'Point', coordinates: [r.lng, r.lat] },
			properties: {
				id: r.id, tipo: r.tipo, descrizione: r.descrizione,
				created_at: r.created_at.toISOString(),
			},
		})),
	});
};

// POST /api/segnalazioni { tipo, descrizione, lng, lat } → 201 { id }
export const POST: RequestHandler = async ({ request }) => {
	let body: unknown;
	try {
		body = await request.json();
	} catch {
		throw error(400, 'Corpo della richiesta non valido');
	}
	const { tipo, descrizione, lng, lat } = (body ?? {}) as Record<string, unknown>;

	if (typeof tipo !== 'string' || !TIPI.includes(tipo))
		throw error(400, 'Scegli il tipo di segnalazione');
	const desc = typeof descrizione === 'string' ? descrizione.trim() : '';
	if (desc.length > 500) throw error(400, 'La descrizione è troppo lunga (max 500 caratteri)');
	if (
		typeof lng !== 'number' || typeof lat !== 'number' ||
		!Number.isFinite(lng) || !Number.isFinite(lat) ||
		lng < BBOX.minLng || lng > BBOX.maxLng || lat < BBOX.minLat || lat > BBOX.maxLat
	)
		throw error(400, 'Indica un punto sulla mappa (in provincia di Vicenza)');

	const res = await db.query<{ id: number }>(
		`INSERT INTO data.segnalazioni (tipo, descrizione, geom)
		 VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326))
		 RETURNING id`,
		[tipo, desc, lng, lat],
	);
	return json({ id: res.rows[0].id }, { status: 201 });
};
```

- [ ] **Step 2: Verifica con curl**

```bash
curl -s -X POST http://localhost:5173/api/segnalazioni \
  -H 'Content-Type: application/json' \
  -d '{"tipo":"pericolo","descrizione":"prova ghiaia in curva","lng":11.36,"lat":45.72}'
# → {"id":1} con status 201
curl -s http://localhost:5173/api/segnalazioni | python3 -m json.tool | head -15
# → FeatureCollection con la segnalazione appena creata
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:5173/api/segnalazioni \
  -H 'Content-Type: application/json' -d '{"tipo":"x","lng":11.36,"lat":45.72}'
# → 400
```

- [ ] **Step 3: Commit**

```bash
git add work/map/web/src/routes/api/segnalazioni
git commit -m "api: GET/POST /api/segnalazioni — segnalazioni cittadino con validazione"
```

---

### Task 13: Sezione `/cittadino` — mobile-first

**Files:**
- Create: `src/routes/cittadino/+page.server.ts`
- Create: `src/routes/cittadino/+page.svelte`

- [ ] **Step 1: `src/routes/cittadino/+page.server.ts`**

```ts
import { loadLayers } from '$lib/server/layers';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => ({
	layers: await loadLayers(['rischio-storico']),
});
```

- [ ] **Step 2: `src/routes/cittadino/+page.svelte`**

```svelte
<script lang="ts">
	import { onMount } from 'svelte';
	import SectionMap from '$lib/components/SectionMap.svelte';
	import SchedaTratta from '$lib/components/SchedaTratta.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const TIPI = [
		{ value: 'incidente_lieve', label: 'Incidente lieve (constatazione amichevole)' },
		{ value: 'strada_danneggiata', label: 'Strada danneggiata' },
		{ value: 'pericolo', label: 'Situazione di pericolo' },
	];

	const VUOTO: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

	let segnalazioni = $state<GeoJSON.FeatureCollection>(VUOTO);
	let mode = $state<'idle' | 'pick' | 'form'>('idle');
	let pos = $state<{ lng: number; lat: number } | null>(null);
	let tipo = $state('pericolo');
	let descrizione = $state('');
	let invio = $state(false);
	let sendErr = $state('');
	let msg = $state('');
	let selected = $state<number | null>(null);

	async function carica() {
		try {
			segnalazioni = await (await fetch('/api/segnalazioni')).json();
		} catch {
			/* la mappa resta senza segnalazioni: non bloccante */
		}
	}
	onMount(carica);

	const puntoNuovo = $derived.by((): GeoJSON.FeatureCollection => ({
		type: 'FeatureCollection',
		features: pos
			? [{ type: 'Feature', geometry: { type: 'Point', coordinates: [pos.lng, pos.lat] }, properties: {} }]
			: [],
	}));

	function onMapClick(lngLat: { lng: number; lat: number }) {
		if (mode !== 'pick') return;
		pos = lngLat;
		mode = 'form';
	}

	function usaGps() {
		sendErr = '';
		navigator.geolocation.getCurrentPosition(
			(p) => {
				pos = { lng: p.coords.longitude, lat: p.coords.latitude };
				mode = 'form';
			},
			() => { sendErr = 'Posizione GPS non disponibile: tocca la mappa.'; },
		);
	}

	function annulla() {
		mode = 'idle';
		pos = null;
		sendErr = '';
	}

	async function invia() {
		if (!pos) { sendErr = 'Indica il punto sulla mappa.'; return; }
		invio = true;
		sendErr = '';
		try {
			const res = await fetch('/api/segnalazioni', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ tipo, descrizione, lng: pos.lng, lat: pos.lat }),
			});
			if (!res.ok) throw new Error((await res.json())?.message ?? res.statusText);
			msg = 'Grazie! La tua segnalazione è sulla mappa.';
			descrizione = '';
			annulla();
			await carica();
			setTimeout(() => (msg = ''), 4000);
		} catch (e) {
			// i campi restano compilati: l'utente può riprovare
			sendErr = e instanceof Error ? e.message : 'Invio non riuscito, riprova.';
		} finally {
			invio = false;
		}
	}
</script>

<svelte:head>
	<title>Cittadino · SaferRoads Vicenza</title>
</svelte:head>

<div class="h-full">
	<SectionMap
		layers={data.layers}
		visible={new Set(['rischio-storico'])}
		interactive={['rischio-storico']}
		geojsonLayers={[
			{
				id: 'segnalazioni',
				data: segnalazioni,
				paint: {
					'circle-color': ['match', ['get', 'tipo'],
						'incidente_lieve', '#e03131',
						'strada_danneggiata', '#f08c00',
						'#9c36b5'],
					'circle-radius': 7,
					'circle-stroke-width': 2,
					'circle-stroke-color': '#ffffff',
				},
			},
			{
				id: 'nuova-segnalazione',
				data: puntoNuovo,
				paint: {
					'circle-color': '#1971c2', 'circle-radius': 9,
					'circle-stroke-width': 3, 'circle-stroke-color': '#ffffff',
				},
			},
		]}
		onFeatureClick={(slug, props) => {
			if (slug === 'rischio-storico' && mode === 'idle') selected = Number(props.id);
		}}
		{onMapClick}
	>
		<!-- intestazione breve -->
		<div class="absolute left-3 top-3 z-10 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs shadow-lg">
			<span class="font-semibold">La tua strada è sicura?</span>
			<span class="hidden sm:inline text-neutral-500"> Tocca una tratta per scoprirlo.</span>
		</div>

		<!-- conferma invio -->
		{#if msg}
			<div class="absolute left-1/2 top-3 z-30 -translate-x-1/2 rounded-xl bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-lg">
				{msg}
			</div>
		{/if}

		<!-- banner modalità scelta punto -->
		{#if mode === 'pick'}
			<div class="absolute inset-x-3 top-14 z-20 rounded-xl bg-blue-600 px-4 py-2 text-center text-sm text-white shadow-lg sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2">
				Tocca la mappa nel punto da segnalare
				<button onclick={annulla} class="ml-2 underline">annulla</button>
			</div>
		{/if}

		<!-- bottone segnala -->
		{#if mode === 'idle'}
			<button
				onclick={() => { selected = null; mode = 'pick'; }}
				class="absolute bottom-5 right-4 z-20 rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-xl hover:bg-blue-700"
			>
				＋ Segnala un problema
			</button>
		{/if}

		<!-- form segnalazione: bottom sheet -->
		{#if mode === 'form'}
			<div class="absolute inset-x-0 bottom-0 z-20 rounded-t-2xl border border-neutral-200 bg-white p-4 shadow-xl md:inset-x-auto md:bottom-4 md:right-4 md:w-96 md:rounded-2xl">
				<h2 class="font-semibold">Segnala un problema</h2>
				<label class="mt-2 block text-xs text-neutral-500">
					Cosa vuoi segnalare?
					<select
						bind:value={tipo}
						class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-2 text-sm text-neutral-800"
					>
						{#each TIPI as t (t.value)}<option value={t.value}>{t.label}</option>{/each}
					</select>
				</label>
				<label class="mt-2 block text-xs text-neutral-500">
					Descrizione (facoltativa)
					<textarea
						bind:value={descrizione}
						rows="2"
						maxlength="500"
						placeholder="Es. buca profonda sulla corsia nord"
						class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-2 text-sm text-neutral-800"
					></textarea>
				</label>
				<div class="mt-1 flex items-center justify-between text-xs text-neutral-500">
					<span>{pos ? `Punto scelto ✓` : 'Nessun punto scelto'}</span>
					<button onclick={usaGps} class="text-blue-700 hover:underline">usa il GPS</button>
				</div>
				{#if sendErr}<p class="mt-1 text-xs text-red-600">{sendErr}</p>{/if}
				<div class="mt-3 flex gap-2">
					<button
						onclick={invia}
						disabled={invio}
						class="flex-1 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
					>
						{invio ? 'Invio…' : 'Invia segnalazione'}
					</button>
					<button
						onclick={annulla}
						class="rounded-lg border border-neutral-300 px-4 py-2.5 text-sm text-neutral-700 hover:bg-neutral-100"
					>
						Annulla
					</button>
				</div>
			</div>
		{/if}

		<!-- scheda tratta ridotta -->
		{#if selected != null && mode === 'idle'}
			<div class="absolute inset-x-0 bottom-0 z-20 max-h-[55%] md:inset-x-auto md:bottom-3 md:right-3 md:top-3 md:w-96 md:max-h-none">
				<SchedaTratta segmentId={selected} variant="ridotta" onClose={() => (selected = null)} />
			</div>
		{/if}
	</SectionMap>
</div>
```

- [ ] **Step 3: Verifica**

Run: `pnpm check` → 0 errors. Su http://localhost:5173/cittadino, **in viewport mobile (≈390 px)**:
1. Mappa piena, bottone "＋ Segnala un problema" raggiungibile col pollice.
2. Flusso completo: ＋ → banner → tocca mappa → form bottom-sheet → Invia → toast verde → il punto appare colorato per tipo.
3. Tocca una tratta (in modalità idle) → scheda ridotta (senza griglia scenari né dettagli tecnici).
4. La segnalazione `curl` del task 12 è visibile sulla mappa.

- [ ] **Step 4: Commit**

```bash
git add work/map/web/src/routes/cittadino
git commit -m "ui: sezione /cittadino mobile-first — mappa pubblica + segnalazioni"
```

---

### Task 14: Verifica finale e rebuild Docker

- [ ] **Step 1: Type-check completo**

Run: `cd work/map/web && pnpm check`
Expected: 0 errors, 0 warnings nuovi.

- [ ] **Step 2: Rebuild del container web e smoke test su :3030**

```bash
cd work/map && docker compose up -d --build web
```
Su http://localhost:3030 ripetere in breve: home, le 4 sezioni, una segnalazione.

- [ ] **Step 3: Checklist anti-scroll e mobile (criterio esplicito della spec)**

Per OGNUNA di `/analisi`, `/previsione`, `/cittadino`: nessuna scrollbar verticale di pagina, su desktop e su viewport 390 px. Per `/` e `/priorita`: scroll solo interno a `main`. Su mobile la scheda tratta è bottom-sheet e i pannelli non si sovrappongono all'header.

- [ ] **Step 4: Coerenza linguaggio**

Nelle 5 pagine nuove non compaiono i termini: "layer", "modello", "feature", "slug", "training". (I numeri tecnici vivono solo dentro "Dettagli tecnici" e nei tooltip.)

- [ ] **Step 5: Commit finale (se rimasti file fuori)**

```bash
git status --short   # tutto committato? altrimenti:
git add work/map && git commit -m "ui: rifiniture dashboard PA"
```
