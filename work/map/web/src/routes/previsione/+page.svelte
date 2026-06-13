<script lang="ts">
	import SectionMap from '$lib/components/SectionMap.svelte';
	import SchedaTratta from '$lib/components/SchedaTratta.svelte';
	import {
		STORICO_COLOR, riskColor, livelloIndice, livelloRisk, frasePosizione,
		SCENARIO_METEO, SCENARIO_FASCE,
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
	let strada = $state('');
	let trattoId = $state<number | null>(null);
	let lineColor = $state<unknown>(STORICO_COLOR);
	let riskMap = $state<Record<string, number>>({});
	let errore = $state('');
	let selected = $state<number | null>(null);

	const scenarioAttivo = $derived(Boolean(meteo && fascia));

	// "SP 046 Pasubio" → "SP 46 Pasubio" (più naturale per chi legge)
	const nomeBreve = (s: string) => s.replace(/^SP 0+/, 'SP ');

	// strade ordinate per pericolosità storica (la peggiore prima)
	const strade = $derived.by(() => {
		const maxByRoad = new Map<string, number>();
		for (const s of data.segments)
			maxByRoad.set(s.nome_strada, Math.max(maxByRoad.get(s.nome_strada) ?? 0, s.indice));
		return [...maxByRoad.entries()].sort((a, b) => b[1] - a[1]).map(([n]) => n);
	});

	const tratti = $derived(strada ? data.segments.filter((s) => s.nome_strada === strada) : []);
	const trattoSel = $derived(
		trattoId != null ? (data.segments.find((s) => s.id === trattoId) ?? null) : null,
	);

	const totale = $derived(data.segments.length);
	const posizioneStorica = (indice: number) =>
		data.segments.filter((s) => s.indice > indice).length + 1;

	// rischio del tratto selezionato nello scenario corrente (null se senza predizione)
	const scenarioRisk = $derived(
		trattoSel && scenarioAttivo ? (riskMap[String(trattoSel.id)] ?? null) : null,
	);
	const livelloRisposta = $derived.by(() => {
		if (!trattoSel) return null;
		if (scenarioAttivo) return scenarioRisk != null ? livelloRisk(scenarioRisk) : null;
		return livelloIndice(trattoSel.indice);
	});

	// pin sul tratto selezionato
	const pinLayer = $derived.by(() => ({
		id: 'tratto-sel',
		data: {
			type: 'FeatureCollection',
			features: trattoSel
				? [{
						type: 'Feature',
						geometry: { type: 'Point', coordinates: [trattoSel.lng, trattoSel.lat] },
						properties: {},
					}]
				: [],
		} as GeoJSON.FeatureCollection,
		paint: {
			'circle-color': '#1d4ed8', 'circle-radius': 8,
			'circle-stroke-width': 3, 'circle-stroke-color': '#ffffff',
		},
	}));

	// zoom: sul tratto se scelto, altrimenti sul tratto peggiore della strada
	const flyTarget = $derived.by(() => {
		if (trattoSel) return { center: [trattoSel.lng, trattoSel.lat] as [number, number], zoom: 14 };
		if (tratti.length) {
			const worst = tratti.reduce((a, b) => (b.indice > a.indice ? b : a));
			return { center: [worst.lng, worst.lat] as [number, number], zoom: 12 };
		}
		return null;
	});

	async function applicaScenario() {
		errore = '';
		if (!meteo || !fascia) {
			lineColor = STORICO_COLOR;
			riskMap = {};
			return;
		}
		try {
			const res = await fetch(
				`/api/segment-risk?meteo=${encodeURIComponent(meteo)}&fascia=${encodeURIComponent(fascia)}`,
			);
			if (!res.ok) throw new Error((await res.json())?.message ?? res.statusText);
			const risk: Record<string, number> = await res.json();
			riskMap = risk;
			const expr: unknown[] = ['match', ['get', 'id']];
			for (const [id, r] of Object.entries(risk)) expr.push(Number(id), riskColor(r));
			expr.push('#9ca3af'); // tratte senza predizione
			lineColor = expr;
		} catch (e) {
			errore = e instanceof Error ? e.message : 'Previsione non disponibile per questo scenario';
			lineColor = STORICO_COLOR;
			riskMap = {};
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
		geojsonLayers={[pinLayer]}
		{flyTarget}
		onFeatureClick={(slug, props) => {
			const seg = data.segments.find((s) => s.id === Number(props.id));
			if (seg) {
				strada = seg.nome_strada;
				trattoId = seg.id;
			}
		}}
	>
		<!-- pannello scenario -->
		<div class="absolute left-3 top-3 z-10 w-72 max-w-[calc(100vw-1.5rem)] rounded-xl border border-neutral-200 bg-white p-3 shadow-lg">
			<h1 class="text-sm font-semibold">Che rischio c'è…</h1>

			<label class="mt-2 block text-xs text-neutral-500">
				su questa strada
				<select
					bind:value={strada}
					onchange={() => (trattoId = null)}
					class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
				>
					<option value="">— scegli una strada —</option>
					{#each strade as s (s)}<option value={s}>{nomeBreve(s)}</option>{/each}
				</select>
			</label>

			{#if strada}
				<label class="mt-2 block text-xs text-neutral-500">
					al tratto
					<select
						bind:value={trattoId}
						class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
					>
						<option value={null}>— scegli un tratto —</option>
						{#each tratti as t (t.id)}<option value={t.id}>km {t.km_idx}</option>{/each}
					</select>
				</label>
			{/if}

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

			<!-- riquadro risposta -->
			{#if trattoSel}
				<div class="mt-3 border-t border-neutral-100 pt-3">
					{#if scenarioAttivo && scenarioRisk == null}
						<div class="rounded-lg bg-neutral-100 px-3 py-2 text-xs text-neutral-500">
							Previsione non disponibile per questo scenario.
						</div>
					{:else if livelloRisposta}
						<div class="rounded-lg px-3 py-2 {livelloRisposta.badge}">
							<span class="text-lg font-bold">● {livelloRisposta.label}</span>
							{#if scenarioAttivo}
								<span class="text-xs"> con {meteo.toLowerCase()} · {fascia.toLowerCase()}</span>
							{:else}
								<span class="text-xs"> rischio storico · indice {trattoSel.indice.toFixed(0)}/100</span>
							{/if}
						</div>
						<p class="mt-1.5 text-xs text-neutral-700">
							{nomeBreve(strada)} km {trattoSel.km_idx}: {frasePosizione(
								posizioneStorica(trattoSel.indice),
								totale,
							)}
						</p>
						<button
							onclick={() => (selected = trattoId)}
							class="mt-1.5 text-xs font-medium text-blue-700 hover:underline"
						>
							dettagli completi →
						</button>
					{/if}
				</div>
			{:else}
				<p class="mt-2 text-xs leading-snug {errore ? 'text-red-600' : 'text-neutral-500'}">
					{#if errore}{errore}
					{:else if strada}Scegli un tratto (km), oppure clicca una tratta sulla mappa.
					{:else}Scegli una strada per leggere il rischio dei suoi tratti.{/if}
				</p>
			{/if}
		</div>

		<!-- fattori di rischio (A3) — solo se Daghem ha consegnato il contratto 4 -->
		{#if data.featureImportance?.length}
			{@const fiMax = data.featureImportance[0].importance || 1}
			<div class="absolute bottom-16 left-3 z-10 hidden w-64 max-h-[40%] overflow-y-auto rounded-xl border border-neutral-200 bg-white p-3 shadow-lg md:block">
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
