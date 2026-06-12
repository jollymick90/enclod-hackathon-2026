import { readFile } from 'node:fs/promises';
import { env } from '$env/dynamic/private';
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
	return {
		layers: await loadLayers(['osm-roads', 'rischio-storico']),
		featureImportance,
	};
};
