import { db } from '$lib/server/db';
import type { PageServerLoad } from './$types';

export interface SegmentRow {
	id: number;
	nome_strada: string;
	km_idx: number;
	comune: string | null;
	lunghezza_m: number;
	n_incidenti: number;
	tot_morti: number;
	tot_feriti: number;
	indice: number;
	indice_grezzo: number;
	n_attraversamenti: number | null;
	n_semafori: number | null;
	n_autovelox: number | null;
	n_lampioni: number | null;
	maxspeed_med: number | null;
	lng: number;
	lat: number;
}

export const load: PageServerLoad = async () => {
	const result = await db.query<SegmentRow>(`
		SELECT id, nome_strada, km_idx, comune, lunghezza_m,
		       n_incidenti, tot_morti, tot_feriti, indice, indice_grezzo,
		       n_attraversamenti, n_semafori, n_autovelox, n_lampioni, maxspeed_med,
		       ST_X(ST_Centroid(geom)) AS lng, ST_Y(ST_Centroid(geom)) AS lat
		FROM data.road_segments
		ORDER BY indice DESC, indice_grezzo DESC
	`);

	const comuni = [...new Set(result.rows.map((r) => r.comune).filter(Boolean))].sort();
	const strade = [...new Set(result.rows.map((r) => r.nome_strada))].sort();

	return { segments: result.rows, comuni, strade };
};
