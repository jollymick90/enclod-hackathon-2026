import { env } from '$env/dynamic/public';

const MARTIN_URL = env.PUBLIC_MARTIN_URL ?? 'http://localhost:3010';

export function martinSource(table: string) {
	return {
		type: 'vector' as const,
		tiles: [`${MARTIN_URL}/${table}/{z}/{x}/{y}`],
		minzoom: 0,
		maxzoom: 20
	};
}
