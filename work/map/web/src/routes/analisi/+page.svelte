<script lang="ts">
	import SectionMap from '$lib/components/SectionMap.svelte';
	import SchedaTratta from '$lib/components/SchedaTratta.svelte';
	import { livelloIndice } from '$lib/risk';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const MESI = [
		'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
		'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre',
	];
	const GIORNI = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica'];

	const PRINCIPALI = ['anno', 'meteo', 'gravita'];
	const SECONDARI = ['mese', 'giorno_settimana', 'fascia_oraria', 'comune', 'nome_strada', 'natura', 'fondo'];

	const LABELS: Record<string, string> = {
		anno: 'Anno', meteo: 'Meteo', gravita: 'Gravità', mese: 'Mese',
		giorno_settimana: 'Giorno', fascia_oraria: 'Fascia oraria',
		comune: 'Comune', nome_strada: 'Strada', natura: 'Natura', fondo: 'Fondo',
	};

	const ROAD_CTX = ['in', ['get', 'fclass'], ['literal', [
		'motorway', 'motorway_link', 'trunk', 'trunk_link',
		'primary', 'primary_link', 'secondary', 'secondary_link',
	]]];

	// elementi di sicurezza (data.osm_traffic) — categorie come il layer "Sicurezza stradale"
	const SAFETY = [
		{ id: 'crossing', label: 'Attraversamenti', color: '#1971c2', fclasses: ['pedestrian_crossing'] },
		{ id: 'signals', label: 'Semafori', color: '#e03131', fclasses: ['traffic_signals'] },
		{ id: 'stop', label: 'Stop', color: '#f08c00', fclasses: ['stop'] },
		{ id: 'junction', label: 'Incroci/rotatorie', color: '#9c36b5', fclasses: ['mini_roundabout', 'motorway_junction', 'turning_circle', 'railway_crossing'] },
		{ id: 'camera', label: 'Autovelox', color: '#212529', fclasses: ['speed_camera'] },
		{ id: 'lamp', label: 'Lampioni', color: '#ffd43b', fclasses: ['street_lamp'] },
	];

	// strade principali e provinciali (no autostrade, no minori) — colore per categoria
	const ROAD_MAIN_COLORS = ['match', ['get', 'fclass'],
		'trunk', '#f08c00', 'trunk_link', '#f08c00',
		'primary', '#f59f00', 'primary_link', '#f59f00',
		'secondary', '#fcc419', 'secondary_link', '#fcc419',
		'#cbd5e1'];
	const ROAD_MAIN = ['trunk', 'trunk_link', 'primary', 'primary_link', 'secondary', 'secondary_link'];

	let sel = $state<Record<string, string>>({});
	let altriOpen = $state(false);
	let sicurezzaOpen = $state(false);
	let safety = $state<Set<string>>(new Set());
	let stradeOn = $state(false);
	let basemapOpacity = $state(1);
	let selected = $state<number | null>(data.trattaIniziale?.id ?? null);

	const roadsColor = $derived(stradeOn ? ROAD_MAIN_COLORS : '#cbd5e1');
	const roadsFilter = $derived(
		stradeOn ? ['in', ['get', 'fclass'], ['literal', ROAD_MAIN]] : ROAD_CTX,
	);

	function toggleSafety(id: string) {
		const next = new Set(safety);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		safety = next;
	}

	// fclass delle categorie attive; lista vuota = layer nascosto (nessun match)
	const trafficFilter = $derived([
		'in', ['get', 'fclass'],
		['literal', SAFETY.filter((s) => safety.has(s.id)).flatMap((s) => s.fclasses)],
	]);

	// etichette user-friendly (requisito C3): mesi a nome, giorni in ordine, anni decrescenti
	function opzioni(field: string): { value: string; label: string }[] {
		const vals = data.filterOptions[field] ?? [];
		if (field === 'mese')
			return vals.map((v) => ({ value: String(v), label: MESI[Number(v) - 1] ?? String(v) }));
		if (field === 'giorno_settimana')
			return [...vals]
				.sort((a, b) => GIORNI.indexOf(String(a)) - GIORNI.indexOf(String(b)))
				.map((v) => ({ value: String(v), label: String(v) }));
		if (field === 'anno')
			return [...vals]
				.sort((a, b) => Number(b) - Number(a))
				.map((v) => ({ value: String(v), label: String(v) }));
		return vals.map((v) => ({ value: String(v), label: String(v) }));
	}

	const accFilter = $derived.by(() => {
		const conds = Object.entries(sel)
			.filter(([, v]) => v !== '')
			.map(([f, v]) => {
				const typed = (data.filterOptions[f] ?? []).find((o) => String(o) === v) ?? v;
				return ['==', ['get', f], typed];
			});
		return conds.length ? ['all', ...conds] : null;
	});

	const nAttivi = $derived(Object.values(sel).filter((v) => v !== '').length);
	const LIVELLI = [livelloIndice(0), livelloIndice(20), livelloIndice(50), livelloIndice(80)];
</script>

<svelte:head>
	<title>Analisi storica · SaferRoads Vicenza</title>
</svelte:head>

<div class="h-full">
	<SectionMap
		layers={data.layers}
		visible={new Set(['osm-roads', 'rischio-storico', 'incidenti-vicenza', 'osm-traffic'])}
		interactive={['rischio-storico']}
		{basemapOpacity}
		lineColorBySlug={{ 'osm-roads': roadsColor }}
		filterBySlug={{ 'osm-roads': roadsFilter, 'incidenti-vicenza': accFilter, 'osm-traffic': trafficFilter }}
		flyTarget={data.trattaIniziale
			? { center: [data.trattaIniziale.lng, data.trattaIniziale.lat], zoom: 13 }
			: null}
		onFeatureClick={(slug, props) => { selected = Number(props.id); }}
	>
		<!-- pannello filtri -->
		<div class="absolute left-3 top-3 z-10 w-64 max-h-[calc(100%-1.5rem)] overflow-y-auto rounded-xl border border-neutral-200 bg-white p-3 shadow-lg">
			<h1 class="text-sm font-semibold">Gli incidenti, anno per anno</h1>
			<div class="mt-2 flex flex-col gap-2">
				{#each PRINCIPALI as f (f)}
					<label class="block text-xs text-neutral-500">
						{LABELS[f]}
						<select
							bind:value={sel[f]}
							class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
						>
							<option value="">Tutti</option>
							{#each opzioni(f) as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
						</select>
					</label>
				{/each}

				<button
					onclick={() => (altriOpen = !altriOpen)}
					class="mt-1 text-left text-xs font-medium text-blue-700 hover:underline"
				>
					{altriOpen ? '− Meno filtri' : `+ Altri filtri${nAttivi > 0 ? ` (${nAttivi} attivi)` : ''}`}
				</button>

				{#if altriOpen}
					{#each SECONDARI as f (f)}
						<label class="block text-xs text-neutral-500">
							{LABELS[f]}
							<select
								bind:value={sel[f]}
								class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
							>
								<option value="">Tutti</option>
								{#each opzioni(f) as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
							</select>
						</label>
					{/each}
				{/if}
			</div>

			<!-- elementi di sicurezza (OSM) -->
			<div class="mt-3 border-t border-neutral-100 pt-2">
				<button
					onclick={() => (sicurezzaOpen = !sicurezzaOpen)}
					class="text-left text-xs font-medium text-blue-700 hover:underline"
				>
					{sicurezzaOpen ? '−' : '+'} Elementi di sicurezza{safety.size > 0 ? ` (${safety.size})` : ''}
				</button>
				{#if sicurezzaOpen}
					<div class="mt-1 flex flex-col gap-1">
						{#each SAFETY as s (s.id)}
							<label class="flex items-center gap-2 text-xs text-neutral-700">
								<input
									type="checkbox"
									checked={safety.has(s.id)}
									onchange={() => toggleSafety(s.id)}
									class="accent-blue-600"
								/>
								<span class="h-2.5 w-2.5 shrink-0 rounded-full" style="background:{s.color}"></span>
								{s.label}
							</label>
						{/each}
						<p class="mt-0.5 text-[10px] leading-snug text-neutral-400">
							Compaiono ingrandendo la mappa su una strada.
						</p>
					</div>
				{/if}
			</div>

			<!-- opzioni mappa -->
			<div class="mt-3 border-t border-neutral-100 pt-2 flex flex-col gap-2">
				<label class="flex items-center gap-2 text-xs text-neutral-700">
					<input type="checkbox" bind:checked={stradeOn} class="accent-blue-600" />
					Strade principali e provinciali
				</label>
				<label class="block text-xs text-neutral-500">
					Sfondo mappa: {Math.round(basemapOpacity * 100)}%
					<input
						type="range"
						min="0" max="1" step="0.05"
						bind:value={basemapOpacity}
						class="mt-0.5 w-full accent-blue-600"
					/>
				</label>
			</div>
		</div>

		<!-- legenda -->
		<div class="absolute bottom-3 left-3 z-10 flex gap-3 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs shadow-lg">
			{#each LIVELLI as l (l.label)}
				<span class="flex items-center gap-1">
					<span class="h-2.5 w-2.5 rounded-full" style="background:{l.color}"></span>{l.label}
				</span>
			{/each}
			<span class="flex items-center gap-1 border-l border-neutral-200 pl-3">
				<span class="h-2.5 w-2.5 rounded-full bg-neutral-700"></span>incidente
			</span>
		</div>

		{#if selected != null}
			<div class="absolute inset-x-0 bottom-0 z-20 max-h-[60%] md:inset-x-auto md:bottom-3 md:right-3 md:top-3 md:w-96 md:max-h-none">
				<SchedaTratta segmentId={selected} onClose={() => (selected = null)} />
			</div>
		{/if}
	</SectionMap>
</div>
