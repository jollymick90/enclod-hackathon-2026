import { error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import type { Layer } from '$lib/types';
import type { PageServerLoad } from './$types';

interface Row {
	id: number;
	slug: string;
	title: string;
	description: string | null;
	kind: 'vector' | 'raster';
	geom_type: 'point' | 'line' | 'polygon' | null;
	source_table: string | null;
	cog_path: string | null;
	lng: number;
	lat: number;
	default_zoom: number;
	style: Record<string, unknown> | null;
	tags: string[];
	source_url: string | null;
	published_at: Date;
}

export const load: PageServerLoad = async ({ params }) => {
	const result = await db.query<Row>(
		`
		SELECT
			id, slug, title, description, kind, geom_type,
			source_table, cog_path,
			ST_X(default_center) AS lng,
			ST_Y(default_center) AS lat,
			default_zoom,
			style, tags, source_url, published_at
		FROM public.layers
		WHERE slug = $1
		LIMIT 1
		`,
		[params.slug]
	);

	if (result.rowCount === 0) {
		throw error(404, `Layer not found: ${params.slug}`);
	}

	const r = result.rows[0];
	const layer: Layer = {
		id: r.id,
		slug: r.slug,
		title: r.title,
		description: r.description,
		kind: r.kind,
		geomType: r.geom_type,
		sourceTable: r.source_table,
		cogPath: r.cog_path,
		defaultCenter: [r.lng, r.lat],
		defaultZoom: r.default_zoom,
		style: r.style,
		tags: r.tags,
		sourceUrl: r.source_url,
		publishedAt: r.published_at.toISOString()
	};

	// Optional faceted filters: if the catalog `style` declares a `filters` array,
	// compute the distinct values of each field from the source table so the map
	// page can render <select> controls. Field/table names come from our own
	// catalog (trusted) but are still validated against an identifier allowlist.
	const filterFields = Array.isArray((layer.style as Record<string, unknown>)?.filters)
		? ((layer.style as Record<string, unknown>).filters as unknown[]).filter(
				(f): f is string => typeof f === 'string'
			)
		: [];

	const filterOptions: Record<string, (string | number)[]> = {};
	const IDENT = /^[a-z_][a-z0-9_]*$/;
	if (layer.kind === 'vector' && layer.sourceTable && IDENT.test(layer.sourceTable)) {
		for (const field of filterFields) {
			if (!IDENT.test(field)) continue;
			const res = await db.query<{ v: string | number }>(
				`SELECT DISTINCT "${field}" AS v FROM data."${layer.sourceTable}"
				 WHERE "${field}" IS NOT NULL ORDER BY v`
			);
			filterOptions[field] = res.rows.map((row) => row.v);
		}
	}

	return { layer, filterFields, filterOptions };
};
