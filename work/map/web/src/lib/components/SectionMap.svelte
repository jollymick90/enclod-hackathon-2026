<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { Snippet } from 'svelte';
	import maplibregl from 'maplibre-gl';

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

	let container: HTMLDivElement | undefined;
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

		try {
			map = new maplibregl.Map({
				container,
				style: BASEMAP,
				center,
				zoom,
				attributionControl: false
			});
			map.addControl(new maplibregl.NavigationControl(), 'top-right');
			map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right');
		} catch (e) {
			console.error('Failed to initialize MapLibre:', e);
			return;
		}

		map.on('load', () => {
			if (!map) return;

			for (const layer of layers) {
				try {
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
				} catch (e) {
					console.error(`Failed to add layer ${layer.slug}:`, e);
				}
			}

			if (onMapClick) {
				map.on('click', (e) => {
					const ids = interactive.map(mlId).filter((id) => map!.getLayer(id));
					const hit = ids.length ? map!.queryRenderedFeatures(e.point, { layers: ids }) : [];
					if (!hit.length) onMapClick(e.lngLat);
				});
			}

			mapReady = true;
			// Forza il resize per sicurezza in caso di container inizialmente a 0
			map.resize();
		});

		map.on('error', (e) => {
			console.error('MapLibre error:', e);
		});
	});

	// Reattività sulla visibilità dei layer
	$effect(() => {
		if (!map || !mapReady) return;
		for (const layer of layers) {
			const id = mlId(layer.slug);
			if (map.getLayer(id)) {
				const isVisible = visible.has(layer.slug);
				map.setLayoutProperty(id, 'visibility', isVisible ? 'visible' : 'none');
			}
		}
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

	$effect(() => {
		if (!map || !mapReady || flyTarget) return;
		map.setCenter(center);
	});

	$effect(() => {
		if (!map || !mapReady || flyTarget) return;
		map.setZoom(zoom);
	});

	onDestroy(() => map?.remove());
</script>

<div class="relative h-full w-full overflow-hidden bg-neutral-100">
	<div bind:this={container} class="absolute inset-0 bg-neutral-200"></div>
	{@render children?.()}
</div>
