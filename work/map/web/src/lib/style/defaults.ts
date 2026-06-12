import type { GeomType } from '$lib/types';

const BLUE = '#3b82f6';

type LayerSpec = {
	id: string;
	source: string;
	'source-layer': string;
	type: 'circle' | 'line' | 'fill';
	paint: Record<string, unknown>;
};

export const defaults: {
	vector: Record<GeomType, LayerSpec>;
	raster: Record<string, string>;
} = {
	vector: {
		point: {
			id: 'layer-data',
			source: 'layer-data',
			'source-layer': '__SOURCE_LAYER__',
			type: 'circle',
			paint: { 'circle-color': BLUE, 'circle-radius': 5, 'circle-opacity': 0.7 }
		},
		line: {
			id: 'layer-data',
			source: 'layer-data',
			'source-layer': '__SOURCE_LAYER__',
			type: 'line',
			paint: { 'line-color': BLUE, 'line-width': 1.5 }
		},
		polygon: {
			id: 'layer-data',
			source: 'layer-data',
			'source-layer': '__SOURCE_LAYER__',
			type: 'fill',
			paint: { 'fill-color': BLUE, 'fill-opacity': 0.3, 'fill-outline-color': BLUE }
		}
	},
	// TiTiler query params applied to every raster layer unless `layer.style`
	// in the catalog overrides them per-layer (the jsonb column wins).
	raster: {
		rescale: '0,2500',
		colormap_name: 'terrain'
	}
};
