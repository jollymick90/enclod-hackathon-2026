import { json, error } from '@sveltejs/kit';
import { db } from '$lib/server/db';
import type { RequestHandler } from './$types';

const TIPI = ['incidente_lieve', 'strada_danneggiata', 'pericolo'];
// bounding box larga della provincia di Vicenza: respinge coordinate palesemente sbagliate
const BBOX = { minLng: 10.8, maxLng: 12.2, minLat: 45.2, maxLat: 46.1 };

// GET /api/segnalazioni → GeoJSON FeatureCollection (per la mappa, aggiornabile live)
export const GET: RequestHandler = async () => {
	const res = await db.query<{
		id: number; tipo: string; descrizione: string; created_at: Date;
		lng: number; lat: number;
	}>(
		`SELECT id, tipo, descrizione, created_at,
		        ST_X(geom) AS lng, ST_Y(geom) AS lat
		 FROM data.segnalazioni ORDER BY created_at DESC LIMIT 500`,
	);
	return json({
		type: 'FeatureCollection',
		features: res.rows.map((r) => ({
			type: 'Feature',
			geometry: { type: 'Point', coordinates: [r.lng, r.lat] },
			properties: {
				id: r.id, tipo: r.tipo, descrizione: r.descrizione,
				created_at: r.created_at.toISOString(),
			},
		})),
	});
};

// POST /api/segnalazioni { tipo, descrizione, lng, lat } → 201 { id }
export const POST: RequestHandler = async ({ request }) => {
	let body: unknown;
	try {
		body = await request.json();
	} catch {
		throw error(400, 'Corpo della richiesta non valido');
	}
	const { tipo, descrizione, lng, lat } = (body ?? {}) as Record<string, unknown>;

	if (typeof tipo !== 'string' || !TIPI.includes(tipo))
		throw error(400, 'Scegli il tipo di segnalazione');
	const desc = typeof descrizione === 'string' ? descrizione.trim() : '';
	if (desc.length > 500) throw error(400, 'La descrizione è troppo lunga (max 500 caratteri)');
	if (
		typeof lng !== 'number' || typeof lat !== 'number' ||
		!Number.isFinite(lng) || !Number.isFinite(lat) ||
		lng < BBOX.minLng || lng > BBOX.maxLng || lat < BBOX.minLat || lat > BBOX.maxLat
	)
		throw error(400, 'Indica un punto sulla mappa (in provincia di Vicenza)');

	const res = await db.query<{ id: number }>(
		`INSERT INTO data.segnalazioni (tipo, descrizione, geom)
		 VALUES ($1, $2, ST_SetSRID(ST_MakePoint($3, $4), 4326))
		 RETURNING id`,
		[tipo, desc, lng, lat],
	);
	return json({ id: res.rows[0].id }, { status: 201 });
};
