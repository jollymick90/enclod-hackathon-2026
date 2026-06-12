import { loadLayers } from '$lib/server/layers';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => ({
	layers: await loadLayers(['rischio-storico']),
});
