import { json, error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import type { RequestHandler } from './$types';

// GET /api/tratte/42 → TrattaDetail (vedi lib/types.ts)
export const GET: RequestHandler = async ({ params }) => {
	const id = Number(params.id);
	if (!Number.isInteger(id) || id <= 0) throw error(400, 'Identificativo tratta non valido');

	const seg = await db.query(
		`SELECT id, nome_strada, km_idx, comune, lunghezza_m,
		        n_incidenti, tot_morti, tot_feriti, n_solo_danni,
		        indice, indice_grezzo,
		        n_attraversamenti, n_semafori, n_stop, n_incroci, n_autovelox, n_lampioni,
		        maxspeed_med,
		        ST_X(ST_Centroid(geom)) AS lng, ST_Y(ST_Centroid(geom)) AS lat
		 FROM data.road_segments WHERE id = $1`,
		[id],
	);
	if (!seg.rowCount) throw error(404, 'Tratta non trovata');

	const [cause, scenari, rank] = await Promise.all([
		// Incidenti il cui segmento più vicino è questo, entro 300 m:
		// stesso criterio di assegnazione di work/src/build_road_segments.py.
		db.query(
			`SELECT a.natura, count(*)::int AS n
			 FROM data.accidents a
			 WHERE a.natura IS NOT NULL
			   AND ST_DWithin(a.geom::geography,
			                  (SELECT geom::geography FROM data.road_segments WHERE id = $1), 300)
			   AND (SELECT rs.id FROM data.road_segments rs
			        ORDER BY rs.geom <-> a.geom LIMIT 1) = $1
			 GROUP BY a.natura ORDER BY n DESC`,
			[id],
		),
		db.query(
			`SELECT meteo, fascia_oraria, risk FROM data.segment_risk WHERE segment_id = $1`,
			[id],
		),
		db.query(
			`SELECT count(*)::int + 1 AS posizione,
			        (SELECT count(*)::int FROM data.road_segments) AS totale
			 FROM data.road_segments
			 WHERE indice > (SELECT indice FROM data.road_segments WHERE id = $1)`,
			[id],
		),
	]);

	return json({
		segment: seg.rows[0],
		cause: cause.rows,
		scenari: scenari.rows,
		posizione: rank.rows[0].posizione,
		totale: rank.rows[0].totale,
	});
};
