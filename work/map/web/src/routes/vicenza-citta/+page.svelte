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

	let sel = $state<Record<string, string>>({});
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
		return conds.length ? ['all', ...conds] : null;
	});
</script>

<svelte:head>
	<title>Vicenza città · SaferRoads Vicenza</title>
</svelte:head>

<div class="h-full">
	<SectionMap
		layers={data.layers}
		visible={new Set([SLUG])}
		interactive={[SLUG]}
		filterBySlug={{ [SLUG]: accFilter }}
		center={[11.546, 45.547]}
		zoom={12}
		onFeatureClick={(slug, props) => { info = props; }}
	>
		<!-- pannello filtri -->
		<div class="absolute left-3 top-3 z-10 w-64 max-w-[calc(100vw-1.5rem)] rounded-xl border border-neutral-200 bg-white p-3 shadow-lg">
			<h1 class="text-sm font-semibold">Incidenti nel Comune di Vicenza</h1>
			<p class="mt-0.5 text-[11px] leading-snug text-neutral-500">
				{data.kpi.n} incidenti urbani 2011–2020 · {data.kpi.morti} morti · {data.kpi.feriti} feriti.
				Dato open data del Comune, fuori dal modello dei corridoi provinciali.
			</p>
			<div class="mt-2 flex flex-col gap-2">
				{#each ['anno', 'gravita', 'natura'] as f (f)}
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
			</div>
		</div>

		<!-- legenda -->
		<div class="absolute bottom-3 left-3 z-10 flex gap-3 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs shadow-lg">
			{#each LEGENDA as l (l.label)}
				<span class="flex items-center gap-1">
					<span class="h-2.5 w-2.5 rounded-full" style="background:{l.color}"></span>{l.label}
				</span>
			{/each}
		</div>

		<!-- info incidente al clic -->
		{#if info}
			<div class="absolute right-3 top-3 z-20 w-72 max-w-[calc(100vw-1.5rem)] rounded-xl border border-neutral-200 bg-white p-3 shadow-xl">
				<div class="flex items-start justify-between gap-2">
					<h2 class="text-sm font-semibold leading-tight">
						{info.via ?? 'Incidente'}{info.via_incrocio ? ` / ${info.via_incrocio}` : ''}
					</h2>
					<button
						onclick={() => (info = null)}
						class="rounded-md px-2 py-0.5 text-neutral-400 hover:bg-neutral-100"
						aria-label="Chiudi"
					>✕</button>
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
