import pg from 'pg';
import { env } from '$env/dynamic/private';

const { Pool } = pg;

export const db = new Pool({
	connectionString:
		env.DATABASE_URL ?? 'postgres://postgres:postgres@localhost:5433/geosentinel'
});
