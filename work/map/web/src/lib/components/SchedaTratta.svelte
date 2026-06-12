<script lang="ts">
	import type { TrattaDetail } from '$lib/types';
	import {
		livelloIndice, livelloRisk, frasePosizione, riskColor,
		SCENARIO_METEO, SCENARIO_FASCE,
	} from '$lib/risk';

	let {
		segmentId,
		scenario = null,
		variant = 'full',
		onClose,
	}: {
		segmentId: number;
		scenario?: { meteo: string; fascia: string } | null;
		variant?: 'full' | 'ridotta';
		onClose?: () => void;
	} = $props();

	let detail = $state<TrattaDetail | null>(null);
	let err = $state('');
	let loading = $state(true);

	$effect(() => {
		const id = segmentId;
		loading = true;
		err = '';
		detail = null;
		fetch(`/api/tratte/${id}`)
			.then(async (r) => {
				if (!r.ok) throw new Error((await r.json())?.message ?? r.statusText);
				return r.json();
			})
			.then((d: TrattaDetail) => { detail = d; })
			.catch((e) => { err = e instanceof Error ? e.message : 'Errore di caricamento'; })
			.finally(() => { loading = false; });
	});

	const liv = $derived(detail ? livelloIndice(detail.segment.indice) : null);
	const scenRisk = $derived.by(() => {
		if (!detail || !scenario) return null;
		const row = detail.scenari.find(
			(s) => s.meteo === scenario.meteo && s.fascia_oraria === scenario.fascia,
		);
		return row ? row.risk : null;
	});
	const causeMax = $derived(detail?.cause[0]?.n ?? 1);

	const DOTAZIONI: { key: keyof TrattaDetail['segment']; label: string }[] = [
		{ key: 'n_attraversamenti', label: 'Attraversamenti' },
		{ key: 'n_semafori', label: 'Semafori' },
		{ key: 'n_stop', label: 'Stop' },
		{ key: 'n_incroci', label: 'Incroci/rotatorie' },
		{ key: 'n_autovelox', label: 'Autovelox' },
		{ key: 'n_lampioni', label: 'Lampioni' },
	];

	function riskCell(meteo: string, fascia: string): number | null {
		const row = detail?.scenari.find((s) => s.meteo === meteo && s.fascia_oraria === fascia);
		return row ? row.risk : null;
	}
</script>

<div class="h-full flex flex-col rounded-t-2xl md:rounded-xl bg-white shadow-xl border border-neutral-200 overflow-hidden">
	<div class="shrink-0 flex items-start justify-between gap-2 border-b border-neutral-100 px-4 py-3">
		<div>
			{#if detail}
				<h2 class="font-semibold leading-tight">
					{detail.segment.nome_strada} — km {detail.segment.km_idx}
				</h2>
				<p class="text-xs text-neutral-500">{detail.segment.comune ?? 'Comune non assegnato'}</p>
			{:else}
				<h2 class="font-semibold text-neutral-400">Tratta…</h2>
			{/if}
		</div>
		{#if onClose}
			<button
				onclick={onClose}
				class="rounded-md px-2 py-1 text-neutral-400 hover:bg-neutral-100 hover:text-neutral-700"
				aria-label="Chiudi"
			>✕</button>
		{/if}
	</div>

	<div class="flex-1 overflow-y-auto px-4 py-3 text-sm">
		{#if loading}
			<p class="text-neutral-400">Caricamento…</p>
		{:else if err}
			<p class="text-red-600">{err}</p>
		{:else if detail && liv}
			<!-- livello -->
			{#if scenario}
				{#if scenRisk != null}
					<div class="rounded-lg px-3 py-2 {livelloRisk(scenRisk).badge}">
						<span class="text-lg font-bold">● {livelloRisk(scenRisk).label}</span>
						<span class="text-xs"> con {scenario.meteo.toLowerCase()} · {scenario.fascia.toLowerCase()}</span>
					</div>
				{:else}
					<div class="rounded-lg bg-neutral-100 px-3 py-2 text-neutral-500 text-xs">
						Previsione non disponibile per questo scenario.
					</div>
				{/if}
			{:else}
				<div class="rounded-lg px-3 py-2 {liv.badge}">
					<span class="text-lg font-bold">● {liv.label}</span>
					<span class="text-xs"> rischio storico · indice {detail.segment.indice.toFixed(0)}/100</span>
				</div>
			{/if}
			<p class="mt-2 text-neutral-700">{frasePosizione(detail.posizione, detail.totale)}</p>

			<!-- storia -->
			<h3 class="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">
				Cosa è successo qui (2010–2023)
			</h3>
			<div class="mt-1 grid grid-cols-3 gap-2 text-center">
				<div class="rounded-lg bg-neutral-50 py-2">
					<div class="font-bold">{detail.segment.n_incidenti}</div>
					<div class="text-[11px] text-neutral-500">incidenti</div>
				</div>
				<div class="rounded-lg bg-neutral-50 py-2">
					<div class="font-bold {detail.segment.tot_morti > 0 ? 'text-red-700' : ''}">
						{detail.segment.tot_morti}
					</div>
					<div class="text-[11px] text-neutral-500">morti</div>
				</div>
				<div class="rounded-lg bg-neutral-50 py-2">
					<div class="font-bold">{detail.segment.tot_feriti}</div>
					<div class="text-[11px] text-neutral-500">feriti</div>
				</div>
			</div>

			<!-- cause -->
			{#if detail.cause.length}
				<h3 class="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">
					Cause più frequenti
				</h3>
				<div class="mt-1 flex flex-col gap-1">
					{#each detail.cause.slice(0, 5) as c (c.natura)}
						<div class="flex items-center gap-2 text-xs">
							<span class="w-32 shrink-0 truncate text-neutral-600" title={c.natura}>{c.natura}</span>
							<div class="h-2 rounded bg-blue-200" style="width:{(c.n / causeMax) * 100}%"></div>
							<span class="text-neutral-400">{c.n}</span>
						</div>
					{/each}
				</div>
			{/if}

			{#if variant === 'full'}
				<!-- dotazioni -->
				<h3 class="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">
					Sicurezza presente sulla tratta
				</h3>
				<div class="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
					{#each DOTAZIONI as d (d.key)}
						<div class="flex justify-between border-b border-neutral-50 py-0.5">
							<span class="text-neutral-600">{d.label}</span>
							<span class="font-medium">{detail.segment[d.key] ?? '—'}</span>
						</div>
					{/each}
				</div>

				<!-- griglia scenari -->
				{#if detail.scenari.length}
					<h3 class="mt-4 text-xs font-semibold uppercase tracking-wide text-neutral-400">
						Rischio previsto per scenario
					</h3>
					<table class="mt-1 w-full text-[10px]">
						<thead>
							<tr>
								<th class="text-left font-normal text-neutral-400"></th>
								{#each SCENARIO_FASCE as f (f)}
									<th class="font-normal text-neutral-400">{f}</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each SCENARIO_METEO as m (m)}
								<tr>
									<td class="pr-1 text-neutral-500">{m}</td>
									{#each SCENARIO_FASCE as f (f)}
										{@const r = riskCell(m, f)}
										<td class="p-0.5 text-center">
											{#if r != null}
												<div
													class="rounded py-0.5 font-medium text-white"
													style="background:{riskColor(r)}"
													title="{livelloRisk(r).label}"
												>
													{(r * 100).toFixed(0)}%
												</div>
											{:else}
												<div class="rounded bg-neutral-100 py-0.5 text-neutral-400">—</div>
											{/if}
										</td>
									{/each}
								</tr>
							{/each}
						</tbody>
					</table>
				{/if}

				<!-- dettagli tecnici -->
				<details class="mt-4">
					<summary class="cursor-pointer text-xs text-neutral-400 hover:text-neutral-600">
						Dettagli tecnici
					</summary>
					<div class="mt-1 grid grid-cols-2 gap-x-4 gap-y-0.5 text-[11px] text-neutral-500">
						<span>indice: {detail.segment.indice.toFixed(1)}</span>
						<span>indice grezzo: {detail.segment.indice_grezzo.toFixed(3)}</span>
						<span>lunghezza: {detail.segment.lunghezza_m} m</span>
						<span>solo danni: {detail.segment.n_solo_danni}</span>
						<span>limite mediano: {detail.segment.maxspeed_med ?? '—'} km/h</span>
						<span>id segmento: {detail.segment.id}</span>
					</div>
				</details>
			{/if}
		{/if}
	</div>
</div>
