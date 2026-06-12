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

export const load: PageServerLoad = async () => {
	const result = await db.query<Row>(`
		SELECT
			id, slug, title, description, kind, geom_type,
			source_table, cog_path,
			ST_X(default_center) AS lng,
			ST_Y(default_center) AS lat,
			default_zoom,
			style, tags, source_url, published_at
		FROM public.layers
		ORDER BY published_at DESC
	`);

	const layers: Layer[] = result.rows.map((r) => ({
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
	}));

	return { layers };
};
