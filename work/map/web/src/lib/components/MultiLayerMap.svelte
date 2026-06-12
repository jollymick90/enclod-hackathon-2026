<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import maplibregl from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';

	import type { Layer } from '$lib/types';
	import { martinSource } from '$lib/tiles/martin';
	import { defaults } from '$lib/style/defaults';
	import { applyStyle } from '$lib/style/apply';
	import { riskColor, STORICO_COLOR, SCENARIO_METEO, SCENARIO_FASCE } from '$lib/risk';

	// ── Road sub-types ───────────────────────────────────────────────────────
	type RoadSub = { id: string; label: string; color: string; fclasses: string[] | null; width: number };

	const ROAD_SUBTYPES: RoadSub[] = [
		{ id: 'road-motorway',  label: 'Autostrade',        color: '#e8590c', fclasses: ['motorway','motorway_link'],                                          width: 4   },
		{ id: 'road-trunk',     label: 'Statali / Trunk',   color: '#f08c00', fclasses: ['trunk','trunk_link'],                                                width: 3   },
		{ id: 'road-primary',   label: 'Primarie (SP)',      color: '#f59f00', fclasses: ['primary','primary_link'],                                            width: 2.5 },
		{ id: 'road-secondary', label: 'Secondarie',         color: '#fcc419', fclasses: ['secondary','secondary_link'],                                        width: 2   },
		{ id: 'road-tertiary',  label: 'Terziarie',          color: '#74b816', fclasses: ['tertiary','tertiary_link'],                                          width: 1.5 },
		{ id: 'road-urban',     label: 'Urbane / residenz.', color: '#868e96', fclasses: ['residential','living_street','pedestrian','unclassified'],            width: 1   },
		{ id: 'road-service',   label: 'Servizio / altro',   color: '#adb5bd', fclasses: null /* = tutto il resto */,                                           width: 0.6 },
	];

	const ALL_EXPLICIT_FCLASSES = ROAD_SUBTYPES
		.filter((s) => s.fclasses !== null)
		.flatMap((s) => s.fclasses as string[]);

	function roadFilter(sub: RoadSub): unknown[] | null {
		if (sub.fclasses === null)
			return ['!', ['in', ['get', 'fclass'], ['literal', ALL_EXPLICIT_FCLASSES]]];
		return ['in', ['get', 'fclass'], ['literal', sub.fclasses]];
	}

	// osm-roads viene rimpiazzato dai sotto-layer; escluso dal grouping normale
	const OSM_ROADS_SLUG = 'osm-roads';
	const OSM_TRAFFIC_SLUG = 'osm-traffic';
	const OSM_MAXSPEED_SLUG = 'osm-maxspeed';

	// ── Traffic sub-types (punti: attraversamenti, semafori, incroci…) ──────
	type TrafficSub = {
		id: string; label: string; color: string;
		fclasses: string[] | null; minzoom: number; defaultOn: boolean;
	};

	const TRAFFIC_SUBTYPES: TrafficSub[] = [
		{ id: 'traffic-crossing', label: 'Attraversamenti',    color: '#1971c2', fclasses: ['pedestrian_crossing'],                                                  minzoom: 11, defaultOn: true  },
		{ id: 'traffic-signals',  label: 'Semafori',           color: '#e03131', fclasses: ['traffic_signals'],                                                      minzoom: 10, defaultOn: true  },
		{ id: 'traffic-stop',     label: 'Stop',               color: '#f08c00', fclasses: ['stop'],                                                                 minzoom: 11, defaultOn: true  },
		{ id: 'traffic-junction', label: 'Incroci/rotatorie',  color: '#9c36b5', fclasses: ['mini_roundabout', 'motorway_junction', 'turning_circle', 'railway_crossing'], minzoom: 9,  defaultOn: true  },
		{ id: 'traffic-camera',   label: 'Autovelox',          color: '#212529', fclasses: ['speed_camera'],                                                          minzoom: 8,  defaultOn: true  },
		{ id: 'traffic-lamp',     label: 'Illuminazione',      color: '#ffd43b', fclasses: ['street_lamp'],                                                           minzoom: 12, defaultOn: false },
		{ id: 'traffic-other',    label: 'Altro (parcheggi…)', color: '#adb5bd', fclasses: null,                                                                      minzoom: 12, defaultOn: false },
	];

	const TRAFFIC_EXPLICIT = TRAFFIC_SUBTYPES
		.filter((s) => s.fclasses !== null)
		.flatMap((s) => s.fclasses as string[]);

	function subFilter(fclasses: string[] | null, allExplicit: string[]): unknown[] {
		if (fclasses === null)
			return ['!', ['in', ['get', 'fclass'], ['literal', allExplicit]]];
		return ['in', ['get', 'fclass'], ['literal', fclasses]];
	}

	// ── Props ────────────────────────────────────────────────────────────────
	const DEFAULT_VISIBLE = new Set([
		'incidenti-vicenza', 'training-incidenti', 'osm-roads',
	]);

	let {
		layers,
		defaultVisible = DEFAULT_VISIBLE,
		filterOptions = {},
	}: {
		layers: Layer[];
		defaultVisible?: Set<string>;
		// { [slug]: { [field]: distinctValues[] } } — solo per i layer che ne hanno bisogno
		filterOptions?: Record<string, Record<string, (string | number)[]>>;
	} = $props();

	// Espandi 'osm-roads'/'osm-traffic' nei loro sotto-layer
	function expandVisible(dv: Set<string>): Set<string> {
		const s = new Set(dv);
		if (s.has(OSM_ROADS_SLUG)) {
			s.delete(OSM_ROADS_SLUG);
			for (const sub of ROAD_SUBTYPES) s.add(sub.id);
		}
		if (s.has(OSM_TRAFFIC_SLUG)) {
			s.delete(OSM_TRAFFIC_SLUG);
			for (const sub of TRAFFIC_SUBTYPES) if (sub.defaultOn) s.add(sub.id);
		}
		return s;
	}

	// ── State ────────────────────────────────────────────────────────────────
	const vectorLayers = $derived(
		layers.filter((l) => l.kind === 'vector' && l.sourceTable && l.geomType),
	);
	const groups = $derived(buildGroups(vectorLayers));

	let visible      = $state<Set<string>>(expandVisible(defaultVisible));
	let basemapOn    = $state(true);
	let container: HTMLDivElement | undefined = $state();
	let map: maplibregl.Map | undefined;
	let mapReady     = $state(false);

	// ── Grouping ─────────────────────────────────────────────────────────────
	type SubLike = { id: string; label: string; color: string };
	type SidebarItem =
		| { kind: 'layer'; layer: Layer }
		| { kind: 'road';  sub: SubLike };

	type SidebarGroup = { label: string; items: SidebarItem[] };

	function buildGroups(all: Layer[]): SidebarGroup[] {
		// roads e traffic sono rimpiazzati dai sotto-layer; maxspeed va nel gruppo strade
		const rest = all.filter(
			(l) => l.slug !== OSM_ROADS_SLUG && l.slug !== OSM_TRAFFIC_SLUG && l.slug !== OSM_MAXSPEED_SLUG,
		);
		const roadsLayer    = all.find((l) => l.slug === OSM_ROADS_SLUG);
		const trafficLayer  = all.find((l) => l.slug === OSM_TRAFFIC_SLUG);
		const maxspeedLayer = all.find((l) => l.slug === OSM_MAXSPEED_SLUG);

		const solution  = rest.filter((l) => !l.tags.includes('osm'));
		const osmBase   = rest.filter((l) => l.tags.includes('osm') && (
			l.slug.includes('water') || l.slug.includes('railway') ||
			l.slug.includes('landuse') || l.slug.includes('natural') ||
			l.slug.includes('protected') || l.slug.includes('adminarea')));
		const osmPeople = rest.filter((l) => l.tags.includes('osm') && (
			l.slug.includes('place') || l.slug.includes('poi') ||
			l.slug.includes('pofw') || l.slug.includes('building')));
		const osmMob    = rest.filter((l) => l.tags.includes('osm') && (
			l.slug.includes('traffic') || l.slug.includes('transport')));

		const toItems = (ls: Layer[]): SidebarItem[] => ls.map((l) => ({ kind: 'layer', layer: l }));

		const roadItems: SidebarItem[] = roadsLayer
			? ROAD_SUBTYPES.map((sub) => ({ kind: 'road', sub }) as SidebarItem)
			: [];
		if (maxspeedLayer) roadItems.push({ kind: 'layer', layer: maxspeedLayer });

		const trafficItems: SidebarItem[] = trafficLayer
			? TRAFFIC_SUBTYPES.map((sub) => ({ kind: 'road', sub }) as SidebarItem)
			: [];

		return [
			solution.length ? { label: 'Soluzione', items: toItems(solution) } : null,
			roadItems.length ? { label: 'OSM — Strade', items: roadItems } : null,
			trafficItems.length ? { label: 'OSM — Sicurezza stradale', items: trafficItems } : null,
			osmBase.length ? { label: 'OSM — Territorio', items: toItems(osmBase) } : null,
			osmPeople.length ? { label: 'OSM — Luoghi/edifici', items: toItems(osmPeople) } : null,
			osmMob.length ? { label: 'OSM — Mobilità', items: toItems(osmMob) } : null,
		].filter(Boolean) as SidebarGroup[];
	}

	// ── Scenario predittivo (B1): ricolora i segmenti col risk del modello ──
	const RISK_SLUG = 'rischio-storico';

	const hasRiskLayer = $derived(vectorLayers.some((l) => l.slug === RISK_SLUG));
	let scenarioMeteo = $state('');
	let scenarioFascia = $state('');
	let scenarioMax = $state(0);
	let scenarioError = $state('');

	async function applicaScenario() {
		if (!map || !mapReady || !map.getLayer(mlId(RISK_SLUG))) return;
		scenarioError = '';
		if (!scenarioMeteo || !scenarioFascia) {
			// reset → colore storico
			map.setPaintProperty(mlId(RISK_SLUG), 'line-color', STORICO_COLOR);
			scenarioMax = 0;
			return;
		}
		try {
			const res = await fetch(
				`/api/segment-risk?meteo=${encodeURIComponent(scenarioMeteo)}&fascia=${encodeURIComponent(scenarioFascia)}`
			);
			if (!res.ok) throw new Error((await res.json())?.message ?? res.statusText);
			const risk: Record<string, number> = await res.json();
			const expr: unknown[] = ['match', ['get', 'id']];
			let max = 0;
			for (const [id, r] of Object.entries(risk)) {
				expr.push(Number(id), riskColor(r));
				if (r > max) max = r;
			}
			expr.push('#9ca3af'); // segmenti senza predizione
			scenarioMax = max;
			map.setPaintProperty(mlId(RISK_SLUG), 'line-color', expr);
			if (!visible.has(RISK_SLUG)) toggle(RISK_SLUG);
		} catch (e) {
			scenarioError = e instanceof Error ? e.message : 'Errore caricamento scenario';
		}
	}

	// ── Filter state ─────────────────────────────────────────────────────────
	// { [slug]: { [field]: selectedValue ('' = tutti) } }
	let layerFilters = $state<Record<string, Record<string, string>>>({});

	function setLayerFilter(slug: string, field: string, value: string) {
		layerFilters = { ...layerFilters, [slug]: { ...(layerFilters[slug] ?? {}), [field]: value } };
		if (!map || !mapReady) return;
		const active = Object.entries(layerFilters[slug] ?? {}).filter(([, v]) => v !== '');
		const opts = filterOptions[slug] ?? {};
		const conditions = active.map(([f, v]) => {
			const typed = (opts[f] ?? []).find((o) => String(o) === v) ?? v;
			return ['==', ['get', f], typed];
		});
		const filter = conditions.length ? ['all', ...conditions] : null;
		if (map.getLayer(mlId(slug)))
			map.setFilter(mlId(slug), filter as maplibregl.FilterSpecification | null);
	}

	function fieldLabel(f: string) {
		return f.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
	}

	// ── Toggle helpers ───────────────────────────────────────────────────────
	function mlId(id: string) { return `ml-${id}`; }

	function applyVisibility(id: string, on: boolean) {
		if (map?.getLayer(mlId(id)))
			map.setLayoutProperty(mlId(id), 'visibility', on ? 'visible' : 'none');
	}

	function toggle(id: string) {
		const next = new Set(visible);
		if (next.has(id)) next.delete(id); else next.add(id);
		visible = next;
		applyVisibility(id, next.has(id));
	}

	function toggleBasemap() {
		basemapOn = !basemapOn;
		if (map?.getLayer('osm'))
			map.setLayoutProperty('osm', 'visibility', basemapOn ? 'visible' : 'none');
	}

	function toggleGroup(items: SidebarItem[], on: boolean) {
		for (const item of items) {
			const id = item.kind === 'layer' ? item.layer.slug : item.sub.id;
			const currently = visible.has(id);
			if (on !== currently) toggle(id);
		}
	}

	// ── Popup ────────────────────────────────────────────────────────────────
	function escapeHtml(v: unknown) {
		return String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
	}

	function attachPopup(layerTitle: string, mapLayerId: string) {
		if (!map) return;
		const popup = new maplibregl.Popup({ closeButton: true, maxWidth: '300px' });
		map.on('click', mapLayerId, (e) => {
			const f = e.features?.[0];
			if (!f || !map) return;
			const props = f.properties ?? {};
			const rows = Object.entries(props)
				.filter(([k, v]) => k !== 'id' && v !== null && v !== '')
				.slice(0, 12)
				.map(([k, v]) =>
					`<tr><td class="pr-2 text-neutral-400 align-top text-xs">${escapeHtml(k)}</td>` +
					`<td class="font-medium text-xs">${escapeHtml(v)}</td></tr>`)
				.join('');
			popup.setLngLat(e.lngLat)
				.setHTML(`<div class="font-semibold text-xs mb-1">${escapeHtml(layerTitle)}</div><table><tbody>${rows}</tbody></table>`)
				.addTo(map);
		});
		map.on('mouseenter', mapLayerId, () => { if (map) map.getCanvas().style.cursor = 'pointer'; });
		map.on('mouseleave', mapLayerId, () => { if (map) map.getCanvas().style.cursor = ''; });
	}

	// ── Basemap ──────────────────────────────────────────────────────────────
	const BASEMAP: maplibregl.StyleSpecification = {
		version: 8,
		sources: { osm: { type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'], tileSize: 256, attribution: '© OpenStreetMap contributors' } },
		layers:  [{ id: 'osm', type: 'raster', source: 'osm' }],
	};

	// ── Mount ────────────────────────────────────────────────────────────────
	onMount(() => {
		if (!container) return;
		map = new maplibregl.Map({ container, style: BASEMAP, center: [11.35, 45.65], zoom: 10 });
		map.addControl(new maplibregl.NavigationControl(), 'top-right');

		map.on('load', () => {
			if (!map) return;

			for (const layer of vectorLayers) {
				if (layer.slug === OSM_ROADS_SLUG) {
					// Aggiungi una sorgente e N sotto-layer filtrati per fclass
					map.addSource(`src-${OSM_ROADS_SLUG}`, martinSource(layer.sourceTable!));
					for (const sub of ROAD_SUBTYPES) {
						const filter = roadFilter(sub);
						const spec: Record<string, unknown> = {
							id: mlId(sub.id),
							source: `src-${OSM_ROADS_SLUG}`,
							'source-layer': layer.sourceTable!,
							type: 'line',
							layout: { visibility: visible.has(sub.id) ? 'visible' : 'none' },
							paint: { 'line-color': sub.color, 'line-width': sub.width },
						};
						if (filter) spec['filter'] = filter;
						map.addLayer(spec as maplibregl.LayerSpecification);
						attachPopup(`Strada — ${sub.label}`, mlId(sub.id));
					}
					continue;
				}

				if (layer.slug === OSM_TRAFFIC_SLUG) {
					// Sotto-layer punto per categoria di sicurezza stradale
					map.addSource(`src-${OSM_TRAFFIC_SLUG}`, martinSource(layer.sourceTable!));
					for (const sub of TRAFFIC_SUBTYPES) {
						const spec: Record<string, unknown> = {
							id: mlId(sub.id),
							source: `src-${OSM_TRAFFIC_SLUG}`,
							'source-layer': layer.sourceTable!,
							type: 'circle',
							minzoom: sub.minzoom,
							filter: subFilter(sub.fclasses, TRAFFIC_EXPLICIT),
							layout: { visibility: visible.has(sub.id) ? 'visible' : 'none' },
							paint: {
								'circle-color': sub.color,
								'circle-radius': ['interpolate', ['linear'], ['zoom'], 10, 2, 13, 4, 16, 7],
								'circle-opacity': 0.85,
								'circle-stroke-width': 0.8,
								'circle-stroke-color': '#ffffff',
							},
						};
						map.addLayer(spec as maplibregl.LayerSpecification);
						attachPopup(`Sicurezza — ${sub.label}`, mlId(sub.id));
					}
					continue;
				}

				// Layer normale dal catalogo
				map.addSource(`src-${layer.slug}`, martinSource(layer.sourceTable!));
				const { filters: _f, legend: _l, minzoom: _mz, ...mapStyle } =
					(layer.style ?? {}) as Record<string, unknown>;
				const base   = defaults.vector[layer.geomType!] as Record<string, unknown>;
				const merged = applyStyle(
					Object.keys(mapStyle).length ? mapStyle : null, base, layer.sourceTable!,
				) as Record<string, unknown>;
				const spec: Record<string, unknown> = {
					...merged,
					id: mlId(layer.slug),
					source: `src-${layer.slug}`,
					layout: { ...((merged.layout as Record<string, unknown>) ?? {}), visibility: visible.has(layer.slug) ? 'visible' : 'none' },
				};
				if (typeof _mz === 'number') spec['minzoom'] = _mz;
				map.addLayer(spec as maplibregl.LayerSpecification);
				attachPopup(layer.title, mlId(layer.slug));
			}

			mapReady = true;
		});
	});

	onDestroy(() => map?.remove());
</script>

<div class="flex gap-4 items-start">
	<!-- Sidebar -->
	<aside class="w-52 shrink-0 rounded-xl border border-neutral-200 bg-white text-xs overflow-hidden max-h-[72vh] overflow-y-auto">

		<!-- Scenario predittivo -->
		{#if hasRiskLayer}
			<div class="border-b border-neutral-100">
				<div class="px-3 py-2 bg-blue-50">
					<span class="font-semibold text-blue-800">Scenario predittivo</span>
				</div>
				<div class="px-3 py-2 flex flex-col gap-1.5">
					<div class="flex flex-col gap-0.5">
						<span class="text-[10px] text-neutral-400 leading-none">Meteo</span>
						<select
							bind:value={scenarioMeteo}
							onchange={applicaScenario}
							class="w-full rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[11px] text-neutral-700"
						>
							<option value="">— storico —</option>
							{#each SCENARIO_METEO as m (m)}<option value={m}>{m}</option>{/each}
						</select>
					</div>
					<div class="flex flex-col gap-0.5">
						<span class="text-[10px] text-neutral-400 leading-none">Fascia oraria</span>
						<select
							bind:value={scenarioFascia}
							onchange={applicaScenario}
							class="w-full rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[11px] text-neutral-700"
						>
							<option value="">— storico —</option>
							{#each SCENARIO_FASCE as f (f)}<option value={f}>{f}</option>{/each}
						</select>
					</div>
					{#if scenarioMeteo && scenarioFascia && scenarioMax > 0}
						<p class="text-[10px] leading-snug text-blue-700">
							Colore = rischio predetto dal modello (max scenario: {(scenarioMax * 100).toFixed(0)}%)
						</p>
					{:else}
						<p class="text-[10px] leading-snug text-neutral-400">
							Scegli meteo + fascia per colorare i segmenti col modello; vuoto = indice storico.
						</p>
					{/if}
					{#if scenarioError}
						<p class="text-[10px] leading-snug text-red-600">{scenarioError}</p>
					{/if}
				</div>
			</div>
		{/if}

		<!-- Basemap -->
		<div class="border-b border-neutral-100">
			<div class="px-3 py-2 bg-neutral-50">
				<span class="font-semibold text-neutral-700">Basemap</span>
			</div>
			<label class="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-neutral-50 transition">
				<input type="checkbox" checked={basemapOn} onchange={toggleBasemap} class="accent-blue-600" />
				<span class="text-neutral-700">OpenStreetMap</span>
			</label>
		</div>

		<!-- Layer groups -->
		{#each groups as group (group.label)}
			<div class="border-b border-neutral-100 last:border-0">
				<div class="flex items-center justify-between gap-2 px-3 py-2 bg-neutral-50">
					<span class="font-semibold text-neutral-700">{group.label}</span>
					<div class="flex gap-1">
						<button
							onclick={() => toggleGroup(group.items, true)}
							class="px-1.5 py-0.5 rounded text-neutral-400 hover:text-neutral-700 hover:bg-neutral-200 transition"
							title="Attiva tutti">all</button>
						<button
							onclick={() => toggleGroup(group.items, false)}
							class="px-1.5 py-0.5 rounded text-neutral-400 hover:text-neutral-700 hover:bg-neutral-200 transition"
							title="Disattiva tutti">off</button>
					</div>
				</div>

				{#each group.items as item (item.kind === 'layer' ? item.layer.slug : item.sub.id)}
					{#if item.kind === 'road'}
						<label class="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-neutral-50 transition">
							<input
								type="checkbox"
								checked={visible.has(item.sub.id)}
								onchange={() => toggle(item.sub.id)}
								class="accent-blue-600 shrink-0"
							/>
							<span
								class="inline-block h-2.5 w-2.5 shrink-0 rounded-sm"
								style="background:{item.sub.color}"
							></span>
							<span class="leading-tight text-neutral-700 truncate">{item.sub.label}</span>
						</label>
					{:else}
						<label class="flex items-center gap-2 px-3 py-1.5 cursor-pointer hover:bg-neutral-50 transition">
							<input
								type="checkbox"
								checked={visible.has(item.layer.slug)}
								onchange={() => toggle(item.layer.slug)}
								class="accent-blue-600 shrink-0"
							/>
							<span class="leading-tight text-neutral-700 truncate" title={item.layer.title}>
								{item.layer.title.replace(/^OSM — /, '').replace(/^Dataset di training — /, '')}
							</span>
						</label>
						{#if visible.has(item.layer.slug) && filterOptions[item.layer.slug]}
							<div class="px-3 pb-2 flex flex-col gap-1">
								{#each Object.entries(filterOptions[item.layer.slug]) as [field, opts] (field)}
									<div class="flex flex-col gap-0.5">
										<span class="text-[10px] text-neutral-400 leading-none">{fieldLabel(field)}</span>
										<select
											value={layerFilters[item.layer.slug]?.[field] ?? ''}
											onchange={(e) => setLayerFilter(item.layer.slug, field, e.currentTarget.value)}
											class="w-full rounded border border-neutral-200 bg-white px-1.5 py-0.5 text-[11px] text-neutral-700"
										>
											<option value="">Tutti</option>
											{#each opts as opt (opt)}
												<option value={String(opt)}>{opt}</option>
											{/each}
										</select>
									</div>
								{/each}
							</div>
						{/if}
					{/if}
				{/each}
			</div>
		{/each}
	</aside>

	<!-- Mappa -->
	<div class="flex-1 min-w-0">
		<div bind:this={container} class="w-full h-[72vh] rounded-xl overflow-hidden border border-neutral-200"></div>
	</div>
</div>
