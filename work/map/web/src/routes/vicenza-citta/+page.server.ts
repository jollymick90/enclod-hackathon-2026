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

	// Vie più pericolose: indice = morti*10 + feriti*3 + incidenti (come l'indice grezzo provinciale).
	const vie = await db.query<{
		via: string; n: string; morti: string; feriti: string; indice: string;
		lng: number; lat: number;
	}>(
		`SELECT via,
		        count(*)            AS n,
		        sum(morti)          AS morti,
		        sum(feriti)         AS feriti,
		        sum(morti)*10 + sum(feriti)*3 + count(*) AS indice,
		        ST_X(ST_Centroid(ST_Collect(geom))) AS lng,
		        ST_Y(ST_Centroid(ST_Collect(geom))) AS lat
		 FROM data.incidenti_vicenza_citta
		 WHERE via IS NOT NULL
		 GROUP BY via
		 ORDER BY indice DESC
		 LIMIT 20`,
	);

	// Pattern temporali (conteggi). Il giorno-settimana è ricostruito dalla data
	// con aritmetica su intervallo (niente errori su date anomale).
	const perAnno = await db.query<{ k: number; n: string }>(
		`SELECT anno AS k, count(*) AS n FROM data.incidenti_vicenza_citta GROUP BY anno ORDER BY anno`,
	);
	const perMese = await db.query<{ k: number; n: string }>(
		`SELECT mese AS k, count(*) AS n FROM data.incidenti_vicenza_citta
		 WHERE mese BETWEEN 1 AND 12 GROUP BY mese ORDER BY mese`,
	);
	const perDow = await db.query<{ k: number; n: string }>(
		`SELECT EXTRACT(ISODOW FROM (make_date(anno, mese, 1) + ((giorno - 1) || ' days')::interval))::int AS k,
		        count(*) AS n
		 FROM data.incidenti_vicenza_citta
		 WHERE giorno BETWEEN 1 AND 31 AND mese BETWEEN 1 AND 12
		 GROUP BY k ORDER BY k`,
	);

	const num = (rows: { k: number; n: string }[]) =>
		rows.map((r) => ({ k: Number(r.k), n: Number(r.n) }));

	return {
		layers,
		filterOptions,
		kpi: {
			n: Number(tot.rows[0].n),
			morti: Number(tot.rows[0].morti),
			feriti: Number(tot.rows[0].feriti),
		},
		vie: vie.rows.map((r) => ({
			via: r.via, n: Number(r.n), morti: Number(r.morti), feriti: Number(r.feriti),
			indice: Number(r.indice), lng: r.lng, lat: r.lat,
		})),
		perAnno: num(perAnno.rows),
		perMese: num(perMese.rows),
		perDow: num(perDow.rows),
	};
};
