export type LayerKind = 'vector' | 'raster';
export type GeomType = 'point' | 'line' | 'polygon';

export interface Layer {
	id: number;
	slug: string;
	title: string;
	description: string | null;

	kind: LayerKind;
	geomType: GeomType | null;

	sourceTable: string | null;
	cogPath: string | null;

	defaultCenter: [number, number];
	defaultZoom: number;

	style: Record<string, unknown> | null;
	tags: string[];
	sourceUrl: string | null;
	publishedAt: string;
}
