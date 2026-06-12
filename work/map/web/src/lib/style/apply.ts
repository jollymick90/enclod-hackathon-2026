type StyleObject = Record<string, unknown>;

function deepMerge<A extends StyleObject, B extends StyleObject>(base: A, override: B): A & B {
	const out: StyleObject = { ...base };
	for (const [k, v] of Object.entries(override)) {
		const existing = out[k];
		if (
			existing &&
			typeof existing === 'object' &&
			!Array.isArray(existing) &&
			v &&
			typeof v === 'object' &&
			!Array.isArray(v)
		) {
			out[k] = deepMerge(existing as StyleObject, v as StyleObject);
		} else {
			out[k] = v;
		}
	}
	return out as A & B;
}

export function applyStyle(
	override: Record<string, unknown> | null,
	base: Record<string, unknown>,
	sourceLayer: string
): Record<string, unknown> {
	const withSourceLayer = JSON.parse(
		JSON.stringify(base).replaceAll('__SOURCE_LAYER__', sourceLayer)
	) as Record<string, unknown>;

	if (!override) return withSourceLayer;
	return deepMerge(withSourceLayer, override);
}
