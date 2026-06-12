import { db } from '$lib/server/db';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async () => {
	const [acc, seg, segn] = await Promise.all([
		db.query<{ n: string; morti: string; feriti: string }>(
			`SELECT count(*) AS n, COALESCE(sum(tot_morti), 0) AS morti,
			        COALESCE(sum(tot_feriti), 0) AS feriti
			 FROM data.accidents`,
		),
		db.query<{ km: string; critiche: string; totale: string }>(
			`SELECT round(sum(lunghezza_m) / 1000.0) AS km,
			        count(*) FILTER (WHERE indice >= 70) AS critiche,
			        count(*) AS totale
			 FROM data.road_segments`,
		),
		// la tabella nasce nel task 11: prima di allora il fallback è 0
		db
			.query<{ n: string }>(`SELECT count(*) AS n FROM data.segnalazioni`)
			.catch(() => ({ rows: [{ n: '0' }] })),
	]);

	return {
		kpi: {
			incidenti: Number(acc.rows[0].n),
			morti: Number(acc.rows[0].morti),
			feriti: Number(acc.rows[0].feriti),
			km: Number(seg.rows[0].km),
			critiche: Number(seg.rows[0].critiche),
			totale: Number(seg.rows[0].totale),
			segnalazioni: Number(segn.rows[0].n),
		},
	};
};
