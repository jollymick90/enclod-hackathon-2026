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
