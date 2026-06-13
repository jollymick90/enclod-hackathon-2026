<script lang="ts">
	import SectionMap from '$lib/components/SectionMap.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const SLUG = 'incidenti-vicenza-citta';
	const LABELS: Record<string, string> = { anno: 'Anno', gravita: 'Gravità', natura: 'Natura' };
	const GRAVITA_LABEL: Record<string, string> = {
		mortale: 'Mortale', feriti: 'Con feriti', danni: 'Solo danni',
	};
	const LEGENDA = [
		{ color: '#dc2626', label: 'Mortale' },
		{ color: '#f59e0b', label: 'Con feriti' },
		{ color: '#9ca3af', label: 'Solo danni' },
	];
	const MESI = ['Gen', 'Feb', 'Mar', 'Apr', 'Mag', 'Giu', 'Lug', 'Ago', 'Set', 'Ott', 'Nov', 'Dic'];
	const DOW = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'];

	let sel = $state<Record<string, string>>({});
	let viaSel = $state('');
	let heatmapOn = $state(false);
	let info = $state<Record<string, unknown> | null>(null);

	function opzioni(field: string): { value: string; label: string }[] {
		const vals = data.filterOptions[field] ?? [];
		if (field === 'gravita')
			return vals.map((v) => ({ value: String(v), label: GRAVITA_LABEL[String(v)] ?? String(v) }));
		return vals.map((v) => ({ value: String(v), label: String(v) }));
	}

	const accFilter = $derived.by(() => {
		const conds = Object.entries(sel)
			.filter(([, v]) => v !== '')
			.map(([f, v]) => {
				const typed = (data.filterOptions[f] ?? []).find((o) => String(o) === v) ?? v;
				return ['==', ['get', f], typed];
			});
		if (viaSel) conds.push(['==', ['get', 'via'], viaSel]);
		return conds.length ? ['all', ...conds] : null;
	});

	const heatmapActive = $derived(heatmapOn ? new Set([SLUG]) : new Set<string>());
	const flyTarget = $derived.by(() => {
		const v = data.vie.find((x) => x.via === viaSel);
		return v ? { center: [v.lng, v.lat] as [number, number], zoom: 15 } : null;
	});

	// grafici: dati con etichette + massimo per scalare le barre
	const annoData = $derived(data.perAnno.map((d) => ({ label: String(d.k), n: d.n })));
	const meseData = $derived(data.perMese.map((d) => ({ label: MESI[d.k - 1] ?? String(d.k), n: d.n })));
	const dowData = $derived(data.perDow.map((d) => ({ label: DOW[d.k - 1] ?? String(d.k), n: d.n })));
	const max = (a: { n: number }[]) => Math.max(1, ...a.map((d) => d.n));

	function selezionaVia(via: string) {
		viaSel = viaSel === via ? '' : via;
	}
</script>

<svelte:head>
	<title>Vicenza città · SaferRoads Vicenza</title>
</svelte:head>

{#snippet barChart(titolo: string, items: { label: string; n: number }[])}
	<div class="rounded-xl border border-neutral-200 bg-white p-4">
		<h3 class="text-sm font-semibold text-neutral-700">{titolo}</h3>
		<div class="mt-3 flex items-end gap-1.5" style="height:120px">
			{#each items as it (it.label)}
				<div class="flex flex-1 flex-col items-center justify-end gap-1">
					<span class="text-[10px] text-neutral-400">{it.n}</span>
					<div
						class="w-full rounded-t bg-blue-400"
						style="height:{(it.n / max(items)) * 92}px"
						title="{it.label}: {it.n}"
					></div>
					<span class="text-[10px] text-neutral-500">{it.label}</span>
				</div>
			{/each}
		</div>
	</div>
{/snippet}

<div class="mx-auto max-w-5xl px-4 sm:px-6 py-6">
	<h1 class="text-2xl font-bold tracking-tight">Incidenti nel Comune di Vicenza</h1>
	<p class="mt-1 text-sm text-neutral-600">
		{data.kpi.n} incidenti urbani geocodificati 2011–2020 · {data.kpi.morti} morti · {data.kpi.feriti} feriti.
		Dato open data del Comune, fuori dal modello dei corridoi provinciali: qui l'analisi è
		storica (dove e quando), non predittiva per scenario meteo.
	</p>

	<!-- controlli -->
	<div class="mt-4 flex flex-wrap items-end gap-3 text-xs text-neutral-500">
		{#each ['anno', 'gravita', 'natura'] as f (f)}
			<label class="flex flex-col gap-1">
				{LABELS[f]}
				<select
					bind:value={sel[f]}
					class="rounded-md border border-neutral-300 px-2 py-1.5 text-sm text-neutral-800"
				>
					<option value="">Tutti</option>
					{#each opzioni(f) as o (o.value)}<option value={o.value}>{o.label}</option>{/each}
				</select>
			</label>
		{/each}
		<label class="flex items-center gap-2 pb-1.5 text-sm text-neutral-700">
			<input type="checkbox" bind:checked={heatmapOn} class="accent-blue-600" />
			Mappa di densità (hotspot)
		</label>
		{#if viaSel}
			<button
				onclick={() => (viaSel = '')}
				class="pb-1.5 text-sm text-blue-700 hover:underline"
			>✕ {viaSel}</button>
		{/if}
	</div>

	<!-- mappa -->
	<div class="relative mt-3 h-[60vh] overflow-hidden rounded-xl border border-neutral-200">
		<SectionMap
			layers={data.layers}
			visible={new Set([SLUG])}
			interactive={[SLUG]}
			filterBySlug={{ [SLUG]: accFilter }}
			heatmapSlugs={[SLUG]}
			{heatmapActive}
			{flyTarget}
			center={[11.546, 45.547]}
			zoom={12}
			onFeatureClick={(slug, props) => { info = props; }}
		>
			<div class="absolute bottom-3 left-3 z-10 flex gap-3 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs shadow-lg">
				{#if heatmapOn}
					<span class="text-neutral-500">Densità incidenti (rosso = più alta)</span>
				{:else}
					{#each LEGENDA as l (l.label)}
						<span class="flex items-center gap-1">
							<span class="h-2.5 w-2.5 rounded-full" style="background:{l.color}"></span>{l.label}
						</span>
					{/each}
				{/if}
			</div>

			{#if info}
				<div class="absolute right-3 top-3 z-20 w-72 max-w-[calc(100%-1.5rem)] rounded-xl border border-neutral-200 bg-white p-3 shadow-xl">
					<div class="flex items-start justify-between gap-2">
						<h2 class="text-sm font-semibold leading-tight">
							{info.via ?? 'Incidente'}{info.via_incrocio ? ` / ${info.via_incrocio}` : ''}
						</h2>
						<button onclick={() => (info = null)} class="rounded-md px-2 py-0.5 text-neutral-400 hover:bg-neutral-100" aria-label="Chiudi">✕</button>
					</div>
					<p class="mt-1 text-xs text-neutral-600">{info.natura ?? '—'}</p>
					<div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-neutral-700">
						<span>Anno: <b>{info.anno}</b></span>
						<span>Veicoli: <b>{info.n_veicoli ?? '—'}</b></span>
						<span class={Number(info.morti) > 0 ? 'text-red-700' : ''}>Morti: <b>{info.morti}</b></span>
						<span>Feriti: <b>{info.feriti}</b></span>
					</div>
				</div>
			{/if}
		</SectionMap>
	</div>

	<!-- vie più pericolose -->
	<h2 class="mt-8 text-lg font-semibold">Vie più pericolose</h2>
	<p class="mt-0.5 text-sm text-neutral-600">
		Indice = morti×10 + feriti×3 + incidenti. Clicca una via per isolarla sulla mappa.
	</p>
	<div class="mt-3 overflow-x-auto rounded-xl border border-neutral-200 bg-white">
		<table class="w-full text-sm">
			<thead>
				<tr class="border-b border-neutral-200 bg-neutral-50 text-left text-xs text-neutral-500">
					<th class="px-3 py-2">#</th>
					<th class="px-3 py-2">Via</th>
					<th class="px-3 py-2 text-right">Indice</th>
					<th class="px-3 py-2 text-right">Incidenti</th>
					<th class="px-3 py-2 text-right">Morti</th>
					<th class="px-3 py-2 text-right">Feriti</th>
				</tr>
			</thead>
			<tbody>
				{#each data.vie as v, i (v.via)}
					<tr
						class="cursor-pointer border-b border-neutral-100 last:border-0 hover:bg-blue-50 {viaSel === v.via ? 'bg-blue-50' : ''}"
						onclick={() => selezionaVia(v.via)}
					>
						<td class="px-3 py-2 text-neutral-400">{i + 1}</td>
						<td class="px-3 py-2 font-medium">{v.via}</td>
						<td class="px-3 py-2 text-right font-semibold">{v.indice}</td>
						<td class="px-3 py-2 text-right">{v.n}</td>
						<td class="px-3 py-2 text-right {v.morti > 0 ? 'font-semibold text-red-700' : ''}">{v.morti}</td>
						<td class="px-3 py-2 text-right">{v.feriti}</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<!-- pattern temporale -->
	<h2 class="mt-8 text-lg font-semibold">Andamento nel tempo</h2>
	<p class="mt-0.5 text-sm text-neutral-600">
		Quando succedono gli incidenti in città. È l'unica lettura "predittiva" che i dati comunali
		permettono (stagionalità e tendenza, non scenario meteo).
	</p>
	<div class="mt-3 grid gap-4 md:grid-cols-3">
		{@render barChart('Per anno', annoData)}
		{@render barChart('Per mese', meseData)}
		{@render barChart('Per giorno della settimana', dowData)}
	</div>
</div>
