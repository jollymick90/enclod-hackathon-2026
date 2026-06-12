import { env } from '$env/dynamic/public';

const TITILER_URL = env.PUBLIC_TITILER_URL ?? 'http://localhost:8000';

/**
 * Build a MapLibre raster source pointing at a TiTiler-served COG.
 * Pass any TiTiler query params (rescale, colormap_name, bidx, expression, ...) via `params`.
 * The caller is responsible for picking sensible defaults — this function is a dumb URL builder.
 */
export function titilerSource(cogPath: string, params: Record<string, string> = {}) {
	// `url` always points at the COG file mounted into the TiTiler container.
	const allParams: Record<string, string> = {
		url: `file:///data/${cogPath}`,
		...params
	};

	const qs = Object.entries(allParams)
		.map(([k, v]) => `${k}=${encodeURIComponent(v)}`)
		.join('&');

	return {
		type: 'raster' as const,
		// TiTiler 2.x requires a tileMatrixSetId path segment;
		// WebMercatorQuad = standard Google Maps-style XYZ.
		tiles: [`${TITILER_URL}/cog/tiles/WebMercatorQuad/{z}/{x}/{y}.png?${qs}`],
		tileSize: 256,
		minzoom: 0,
		maxzoom: 20
	};
}
