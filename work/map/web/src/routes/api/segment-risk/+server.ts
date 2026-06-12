import { json, error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import type { RequestHandler } from './$types';

const METEO = ['Sereno', 'Pioggia', 'Nebbia', 'Neve', 'Vento forte', 'Altro'];
const FASCE = ['Mattino', 'Notte', 'Pomeriggio', 'Sera'];

// GET /api/segment-risk?meteo=Pioggia&fascia=Sera
// → { "<segment_id>": risk, ... } per lo scenario richiesto.
export const GET: RequestHandler = async ({ url }) => {
	const meteo = url.searchParams.get('meteo') ?? '';
	const fascia = url.searchParams.get('fascia') ?? '';
	if (!METEO.includes(meteo) || !FASCE.includes(fascia)) {
		throw error(400, `Parametri non validi: meteo ∈ ${METEO.join('|')}, fascia ∈ ${FASCE.join('|')}`);
	}

	const result = await db.query<{ segment_id: number; risk: number }>(
		`SELECT segment_id, risk FROM data.segment_risk
		 WHERE meteo = $1 AND fascia_oraria = $2`,
		[meteo, fascia]
	);

	if (result.rowCount === 0) {
		throw error(404, 'Nessuna predizione per questo scenario (data.segment_risk vuota?)');
	}

	const out: Record<string, number> = {};
	for (const r of result.rows) out[String(r.segment_id)] = r.risk;
	return json(out);
};
