import { db } from '$lib/server/db';
import { loadLayers } from '$lib/server/layers';
import type { PageServerLoad } from './$types';

const FIELDS = ['anno', 'gravita', 'natura'];

export const load: PageServerLoad = async () => {
	const layers = await loadLayers(['incidenti-vicenza-citta']);

	const filterOptions: Record<string, (string | number)[]> = {};
	for (const f of FIELDS) {
		const res = await db.query<{ v: string | number }>(
			`SELECT DISTINCT "${f}" AS v FROM data.incidenti_vicenza_citta
			 WHERE "${f}" IS NOT NULL ORDER BY v`,
		);
		filterOptions[f] = res.rows.map((r) => r.v);
	}

	const tot = await db.query<{ n: string; morti: string; feriti: string }>(
		`SELECT count(*) AS n, COALESCE(sum(morti), 0) AS morti, COALESCE(sum(feriti), 0) AS feriti
		 FROM data.incidenti_vicenza_citta`,
	);

	return {
		layers,
		filterOptions,
		kpi: {
			n: Number(tot.rows[0].n),
			morti: Number(tot.rows[0].morti),
			feriti: Number(tot.rows[0].feriti),
		},
	};
};
