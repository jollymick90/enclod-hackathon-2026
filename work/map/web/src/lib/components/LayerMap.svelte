<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import maplibregl from 'maplibre-gl';
	import 'maplibre-gl/dist/maplibre-gl.css';

	import type { Layer } from '$lib/types';
	import { martinSource } from '$lib/tiles/martin';
	import { titilerSource } from '$lib/tiles/titiler';
	import { defaults } from '$lib/style/defaults';
	import { applyStyle } from '$lib/style/apply';

	// OpenStreetMap raster basemap (demotiles is near-empty at city zoom).
	const BASEMAP_STYLE: maplibregl.StyleSpecification = {
		version: 8,
		sources: {
			osm: {
				type: 'raster',
				tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
				tileSize: 256,
				attribution: '© OpenStreetMap contributors'
			}
		},
		layers: [{ id: 'osm', type: 'raster', source: 'osm' }]
	};

	type LegendItem = { label: string; color: string };

	let {
		layer,
		filterFields = [],
		filterOptions = {}
	}: {
		layer: Layer;
		filterFields?: string[];
		filterOptions?: Record<string, (string | number)[]>;
	} = $props();

	// Meta keys that live in the catalog `style` jsonb but are NOT MapLibre spec.
	// They drive the legend / filter UI and must be stripped before addLayer().
	const legend = $derived(((layer.style?.legend as LegendItem[]) ?? []) as LegendItem[]);

	let container: HTMLDivElement | undefined = $state();
	let map: maplibregl.Map | undefined;
	let mapReady = $state(false);

	// Selected filter value per field ('' = all). Reactive: an $effect re-applies
	// the MapLibre filter whenever any selection changes.
	let selected = $state<Record<string, string>>({});

	function escapeHtml(v: unknown): string {
		return String(v)
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;');
	}

	// Build a MapLibre filter expression from the current selections, coercing each
	// value back to the type of its source option (years are numbers in the tiles).
	function buildFilter(): unknown[] | null {
		const conditions: unknown[][] = [];
		for (const field of filterFields) {
			const raw = selected[field];
			if (!raw) continue;
			const opts = filterOptions[field] ?? [];
			const typed = opts.find((o) => String(o) === raw) ?? raw;
			conditions.push(['==', ['get', field], typed]);
		}
		return conditions.length ? ['all', ...conditions] : null;
	}

	// Applied directly from the <select> onchange handler (not via $effect) so the
	// behavior is explicit and deterministic regardless of binding timing.
	function applyFilters() {
		if (!map || !mapReady || !map.getLayer('layer-data')) return;
		map.setFilter('layer-data', buildFilter() as maplibregl.FilterSpecification | null);
	}

	function fieldLabel(field: string): string {
		return field.replace(/_/g, ' ').replace(/^\w/, (c) => c.toUpperCase());
	}

	onMount(() => {
		if (!container) return;

		map = new maplibregl.Map({
			container,
			style: BASEMAP_STYLE,
			center: layer.defaultCenter,
			zoom: layer.defaultZoom
		});

		map.on('load', () => {
			if (!map) return;

			if (layer.kind === 'vector' && layer.sourceTable && layer.geomType) {
				map.addSource('layer-data', martinSource(layer.sourceTable));

				// Strip meta keys so only real MapLibre paint/layout reach addLayer.
				const { filters: _f, legend: _l, ...mapStyle } = (layer.style ?? {}) as Record<
					string,
					unknown
				>;
				const styleSpec = applyStyle(
					Object.keys(mapStyle).length ? mapStyle : null,
					defaults.vector[layer.geomType] as unknown as Record<string, unknown>,
					layer.sourceTable
				);
				map.addLayer(styleSpec as unknown as maplibregl.LayerSpecification);

				// Popup with all feature attributes on click.
				const popup = new maplibregl.Popup({ closeButton: true, maxWidth: '320px' });
				map.on('click', 'layer-data', (e) => {
					const f = e.features?.[0];
					if (!f || !map) return;
					const props = f.properties ?? {};
					const rows = Object.entries(props)
						.filter(([k, v]) => k !== 'id' && v !== null && v !== '')
						.map(
							([k, v]) =>
								`<tr><td class="pr-2 text-neutral-500 align-top">${escapeHtml(
									fieldLabel(k)
								)}</td><td class="font-medium">${escapeHtml(v)}</td></tr>`
						)
						.join('');
					popup
						.setLngLat(e.lngLat)
						.setHTML(`<table class="text-xs leading-5"><tbody>${rows}</tbody></table>`)
						.addTo(map);
				});
				map.on('mouseenter', 'layer-data', () => {
					if (map) map.getCanvas().style.cursor = 'pointer';
				});
				map.on('mouseleave', 'layer-data', () => {
					if (map) map.getCanvas().style.cursor = '';
				});

				mapReady = true;
			} else if (layer.kind === 'raster' && layer.cogPath) {
				// Raster TiTiler params: defaults from style/defaults.ts, then per-layer
				// overrides from the catalog's `style` jsonb column. Anything in `layer.style`
				// wins (e.g. {"rescale":"0,3000","colormap_name":"viridis"}).
				const rasterParams: Record<string, string> = {
					...defaults.raster,
					...Object.fromEntries(
						Object.entries(layer.style ?? {}).map(([k, v]) => [k, String(v)])
					)
				};
				map.addSource('layer-data', titilerSource(layer.cogPath, rasterParams));
				map.addLayer({
					id: 'layer-data',
					source: 'layer-data',
					type: 'raster',
					paint: { 'raster-opacity': 0.85 }
				});
			}
		});
	});

	onDestroy(() => {
		map?.remove();
	});
</script>

{#if filterFields.length}
	<div class="mb-3 flex flex-wrap items-end gap-3">
		{#each filterFields as field (field)}
			<label class="flex flex-col gap-1 text-xs text-neutral-500">
				{fieldLabel(field)}
				<select
					value={selected[field] ?? ''}
					onchange={(e) => {
						selected[field] = e.currentTarget.value;
						applyFilters();
					}}
					class="rounded-md border border-neutral-300 px-2 py-1 text-sm text-neutral-800"
				>
					<option value="">Tutti</option>
					{#each filterOptions[field] ?? [] as opt (opt)}
						<option value={String(opt)}>{opt}</option>
					{/each}
				</select>
			</label>
		{/each}
	</div>
{/if}

<div class="relative">
	<div
		bind:this={container}
		class="w-full h-[70vh] rounded-xl overflow-hidden border border-neutral-200"
	></div>

	{#if legend.length}
		<div
			class="absolute bottom-3 left-3 rounded-lg bg-white/90 px-3 py-2 text-xs shadow-sm backdrop-blur"
		>
			{#each legend as item (item.label)}
				<div class="flex items-center gap-2">
					<span
						class="inline-block h-3 w-3 rounded-full border border-white"
						style="background:{item.color}"
					></span>
					<span class="text-neutral-700">{item.label}</span>
				</div>
			{/each}
		</div>
	{/if}
</div>
