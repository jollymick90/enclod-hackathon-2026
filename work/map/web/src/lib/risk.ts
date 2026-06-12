// Livelli verbali, colori e frasi del rischio — fonte unica per tutta la UI.

export const SCENARIO_METEO = ['Sereno', 'Pioggia', 'Nebbia', 'Neve', 'Vento forte', 'Altro'];
export const SCENARIO_FASCE = ['Mattino', 'Pomeriggio', 'Sera', 'Notte'];

export type Livello = {
	label: 'Basso' | 'Moderato' | 'Alto' | 'Critico';
	color: string; // colore pieno per mappa/pallini
	badge: string; // classi tailwind per il badge testuale
};

// Soglie sull'indice storico 0-100 (le stesse dei colori mappa e dei badge attuali).
export function livelloIndice(indice: number): Livello {
	if (indice >= 70) return { label: 'Critico', color: '#c92a2a', badge: 'bg-red-100 text-red-800' };
	if (indice >= 40) return { label: 'Alto', color: '#f76707', badge: 'bg-orange-100 text-orange-800' };
	if (indice >= 15) return { label: 'Moderato', color: '#eab308', badge: 'bg-yellow-100 text-yellow-800' };
	return { label: 'Basso', color: '#2f9e44', badge: 'bg-green-100 text-green-800' };
}

// Il risk del modello (0..1) satura visivamente a RISK_FULL → riportato in scala 0-100.
export const RISK_FULL = 0.5;
export function livelloRisk(risk: number): Livello {
	return livelloIndice(Math.min(risk / RISK_FULL, 1) * 100);
}

// Gradiente continuo per il colore-mappa del risk del modello (0 → verde, RISK_FULL → rosso).
export function riskColor(r: number): string {
	const stops: [number, string][] = [
		[0, '#2f9e44'], [0.15, '#ffd43b'], [0.3, '#f76707'], [0.5, '#c92a2a'],
	];
	const t = Math.min(r, RISK_FULL);
	for (let i = stops.length - 1; i >= 0; i--) if (t >= stops[i][0]) {
		if (i === stops.length - 1) return stops[i][1];
		const [a, ca] = stops[i], [b, cb] = stops[i + 1];
		const k = (t - a) / (b - a);
		const hex = (c: string) => [1, 3, 5].map((j) => parseInt(c.slice(j, j + 2), 16));
		const [r1, g1, b1] = hex(ca), [r2, g2, b2] = hex(cb);
		const mix = (x: number, y: number) => Math.round(x + (y - x) * k);
		return `rgb(${mix(r1, r2)},${mix(g1, g2)},${mix(b1, b2)})`;
	}
	return stops[0][1];
}

// Espressione MapLibre per il colore storico dei segmenti (indice 0-100).
export const STORICO_COLOR = [
	'interpolate', ['linear'], ['get', 'indice'],
	0, '#2f9e44', 15, '#ffd43b', 40, '#f76707', 70, '#c92a2a',
] as unknown[];

// Frase "raccontabile" dal ranking storico — template deterministici, niente testo libero.
export function frasePosizione(posizione: number, totale: number): string {
	if (posizione === 1) return `È la tratta più pericolosa tra le ${totale} monitorate.`;
	if (posizione <= 5) return `È tra le 5 tratte più pericolose delle ${totale} monitorate.`;
	if (posizione <= Math.ceil(totale * 0.1))
		return `È nel 10% di tratte più pericolose (${posizione}ª su ${totale}).`;
	return `È la ${posizione}ª tratta su ${totale} per pericolosità storica.`;
}
