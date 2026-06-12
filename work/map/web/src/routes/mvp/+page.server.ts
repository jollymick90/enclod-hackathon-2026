import { db } from '$lib/server/db';
import type { Layer } from '$lib/types';
import type { PageServerLoad } from './$types';

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

const IDENT = /^[a-z_][a-z0-9_]*$/;

export const load: PageServerLoad = async () => {
	const result = await db.query<Row>(`
		SELECT id, slug, title, description, kind, geom_type,
		       source_table, cog_path,
		       ST_X(default_center) AS lng, ST_Y(default_center) AS lat,
		       default_zoom, style, tags, source_url, published_at
		FROM public.layers ORDER BY published_at DESC
	`);
	const layers = result.rows.map(toLayer);

	// Calcola le opzioni dei filtri solo per layer non-OSM con filtri dichiarati.
	// I layer OSM (taglio fclass) non ne hanno bisogno nell'MVP.
	const filterOptions: Record<string, Record<string, (string | number)[]>> = {};

	for (const layer of layers) {
		if (layer.kind !== 'vector' || !layer.sourceTable || !layer.style) continue;
		if (layer.tags.includes('osm')) continue;
		if (!IDENT.test(layer.sourceTable)) continue;

		const fields = Array.isArray(layer.style['filters'])
			? (layer.style['filters'] as unknown[]).filter((f): f is string => typeof f === 'string')
			: [];
		if (!fields.length) continue;

		filterOptions[layer.slug] = {};
		for (const field of fields) {
			if (!IDENT.test(field)) continue;
			const res = await db.query<{ v: string | number }>(
				`SELECT DISTINCT "${field}" AS v FROM data."${layer.sourceTable}"
				 WHERE "${field}" IS NOT NULL ORDER BY v`,
			);
			filterOptions[layer.slug][field] = res.rows.map((r) => r.v);
		}
	}

	return { layers, filterOptions };
};
