import { readFile } from 'node:fs/promises';
import { env } from '$env/dynamic/private';
import { db } from '$lib/server/db';
import { loadLayers } from '$lib/server/layers';
import type { PageServerLoad } from './$types';

// Contratto 4 (Daghem): se il file non esiste il riquadro A3 non si renderizza.
// In dev il cwd è work/map/web → il file sta in work/output/.
// In prod si monta work/output e si punta via env FEATURE_IMPORTANCE_PATH.
const FI_PATH = env.FEATURE_IMPORTANCE_PATH ?? '../../output/feature_importance.json';

export const load: PageServerLoad = async () => {
	let featureImportance: { feature: string; importance: number }[] | null = null;
	try {
		const parsed = JSON.parse(await readFile(FI_PATH, 'utf8'));
		if (Array.isArray(parsed)) featureImportance = parsed;
	} catch {
		featureImportance = null; // file assente: nessun errore (da spec)
	}

	// Elenco tratti per i selettori strada → km (id int, non bigint→string).
	const seg = await db.query<{
		id: number; nome_strada: string; km_idx: number; indice: number;
		lng: number; lat: number;
	}>(
		`SELECT id::int AS id, nome_strada, km_idx, indice,
		        ST_X(ST_Centroid(geom)) AS lng, ST_Y(ST_Centroid(geom)) AS lat
		 FROM data.road_segments
		 ORDER BY nome_strada, km_idx`,
	);

	return {
		layers: await loadLayers(['osm-roads', 'rischio-storico']),
		featureImportance,
		segments: seg.rows,
	};
};
