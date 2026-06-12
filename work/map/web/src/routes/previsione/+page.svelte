<script lang="ts">
	import SectionMap from '$lib/components/SectionMap.svelte';
	import SchedaTratta from '$lib/components/SchedaTratta.svelte';
	import {
		STORICO_COLOR, riskColor, livelloIndice, SCENARIO_METEO, SCENARIO_FASCE,
	} from '$lib/risk';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	// strade di contesto: solo viabilità principale, in grigio
	const ROAD_CTX = ['in', ['get', 'fclass'], ['literal', [
		'motorway', 'motorway_link', 'trunk', 'trunk_link',
		'primary', 'primary_link', 'secondary', 'secondary_link',
	]]];

	let meteo = $state('');
	let fascia = $state('');
	let lineColor = $state<unknown>(STORICO_COLOR);
	let errore = $state('');
	let selected = $state<number | null>(null);

	const scenarioAttivo = $derived(Boolean(meteo && fascia));

	async function applicaScenario() {
		errore = '';
		if (!meteo || !fascia) {
			lineColor = STORICO_COLOR;
			return;
		}
		try {
			const res = await fetch(
				`/api/segment-risk?meteo=${encodeURIComponent(meteo)}&fascia=${encodeURIComponent(fascia)}`,
			);
			if (!res.ok) throw new Error((await res.json())?.message ?? res.statusText);
			const risk: Record<string, number> = await res.json();
			const expr: unknown[] = ['match', ['get', 'id']];
			for (const [id, r] of Object.entries(risk)) expr.push(Number(id), riskColor(r));
			expr.push('#9ca3af'); // tratte senza predizione
			lineColor = expr;
		} catch (e) {
			errore = e instanceof Error ? e.message : 'Previsione non disponibile per questo scenario';
			lineColor = STORICO_COLOR;
		}
	}

	const LIVELLI = [livelloIndice(0), livelloIndice(20), livelloIndice(50), livelloIndice(80)];
</script>

<svelte:head>
	<title>Previsione · SaferRoads Vicenza</title>
</svelte:head>

<div class="h-full">
	<SectionMap
		layers={data.layers}
		visible={new Set(['osm-roads', 'rischio-storico'])}
		interactive={['rischio-storico']}
		lineColorBySlug={{ 'rischio-storico': lineColor, 'osm-roads': '#cbd5e1' }}
		filterBySlug={{ 'osm-roads': ROAD_CTX }}
		onFeatureClick={(slug, props) => { selected = Number(props.id); }}
	>
		<!-- pannello scenario -->
		<div class="absolute left-3 top-3 z-10 w-64 rounded-xl border border-neutral-200 bg-white p-3 shadow-lg">
			<h1 class="text-sm font-semibold">Che rischio c'è…</h1>
			<label class="mt-2 block text-xs text-neutral-500">
				con questo meteo
				<select
					bind:value={meteo}
					onchange={applicaScenario}
					class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
				>
					<option value="">— storico —</option>
					{#each SCENARIO_METEO as m (m)}<option value={m}>{m}</option>{/each}
				</select>
			</label>
			<label class="mt-2 block text-xs text-neutral-500">
				in questa fascia oraria
				<select
					bind:value={fascia}
					onchange={applicaScenario}
					class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
				>
					<option value="">— storico —</option>
					{#each SCENARIO_FASCE as f (f)}<option value={f}>{f}</option>{/each}
				</select>
			</label>
			<p class="mt-2 text-xs leading-snug {errore ? 'text-red-600' : 'text-neutral-500'}">
				{#if errore}{errore}
				{:else if scenarioAttivo}
					Le tratte sono colorate col rischio previsto. Clicca una tratta per i dettagli.
				{:else}
					Scegli meteo e fascia oraria, oppure clicca una tratta per il rischio storico.
				{/if}
			</p>
		</div>

		<!-- fattori di rischio (A3) — solo se Daghem ha consegnato il contratto 4 -->
		{#if data.featureImportance?.length}
			{@const fiMax = data.featureImportance[0].importance || 1}
			<div class="absolute left-3 top-[15.5rem] z-10 hidden w-64 rounded-xl border border-neutral-200 bg-white p-3 shadow-lg md:block">
				<h2 class="text-xs font-semibold uppercase tracking-wide text-neutral-400">
					Cosa pesa di più sul rischio
				</h2>
				<div class="mt-1.5 flex flex-col gap-1">
					{#each data.featureImportance.slice(0, 6) as fi (fi.feature)}
						<div class="flex items-center gap-2 text-xs">
							<span class="w-24 shrink-0 truncate text-neutral-600" title={fi.feature}>{fi.feature}</span>
							<div class="h-2 rounded bg-blue-300" style="width:{(fi.importance / fiMax) * 100}%"></div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- legenda -->
		<div class="absolute bottom-3 left-3 z-10 flex gap-3 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs shadow-lg">
			{#each LIVELLI as l (l.label)}
				<span class="flex items-center gap-1">
					<span class="h-2.5 w-2.5 rounded-full" style="background:{l.color}"></span>{l.label}
				</span>
			{/each}
		</div>

		<!-- scheda tratta: bottom-sheet su mobile, pannello dx su desktop -->
		{#if selected != null}
			<div class="absolute inset-x-0 bottom-0 z-20 max-h-[60%] md:inset-x-auto md:bottom-3 md:right-3 md:top-3 md:w-96 md:max-h-none">
				<SchedaTratta
					segmentId={selected}
					scenario={scenarioAttivo ? { meteo, fascia } : null}
					onClose={() => (selected = null)}
				/>
			</div>
		{/if}
	</SectionMap>
</div>
