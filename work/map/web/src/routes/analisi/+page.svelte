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

	let sel = $state<Record<string, string>>({});
	let altriOpen = $state(false);
	let selected = $state<number | null>(data.trattaIniziale?.id ?? null);

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
		visible={new Set(['osm-roads', 'rischio-storico', 'incidenti-vicenza'])}
		interactive={['rischio-storico']}
		lineColorBySlug={{ 'osm-roads': '#cbd5e1' }}
		filterBySlug={{ 'osm-roads': ROAD_CTX, 'incidenti-vicenza': accFilter }}
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
