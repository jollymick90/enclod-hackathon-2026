import { db } from '$lib/server/db';
import { loadLayers } from '$lib/server/layers';
import type { PageServerLoad } from './$types';

// Campi filtrabili di data.accidents (identificatori costanti, interpolazione sicura).
const FIELDS = [
	'anno', 'mese', 'giorno_settimana', 'fascia_oraria', 'comune',
	'nome_strada', 'natura', 'fondo', 'meteo', 'gravita',
];

export const load: PageServerLoad = async ({ url }) => {
	const layers = await loadLayers(['osm-roads', 'rischio-storico', 'incidenti-vicenza']);

	const filterOptions: Record<string, (string | number)[]> = {};
	for (const f of FIELDS) {
		const res = await db.query<{ v: string | number }>(
			`SELECT DISTINCT "${f}" AS v FROM data.accidents WHERE "${f}" IS NOT NULL ORDER BY v`,
		);
		filterOptions[f] = res.rows.map((r) => r.v);
	}

	// ?tratta=ID (arrivo da /priorita): centra la mappa e apre la scheda
	let trattaIniziale: { id: number; lng: number; lat: number } | null = null;
	const tratta = Number(url.searchParams.get('tratta'));
	if (Number.isInteger(tratta) && tratta > 0) {
		const r = await db.query<{ id: number; lng: number; lat: number }>(
			`SELECT id, ST_X(ST_Centroid(geom)) AS lng, ST_Y(ST_Centroid(geom)) AS lat
			 FROM data.road_segments WHERE id = $1`,
			[tratta],
		);
		trattaIniziale = r.rows[0] ?? null;
	}

	return { layers, filterOptions, trattaIniziale };
};
