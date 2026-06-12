<script lang="ts">
	import { livelloIndice } from '$lib/risk';
	import type { PageData } from './$types';
	import type { SegmentRow } from './+page.server';

	let { data }: { data: PageData } = $props();

	type StradaGruppo = { strada: string; max: number; n: number; tratti: SegmentRow[] };
	type ComuneGruppo = { comune: string; max: number; n: number; strade: StradaGruppo[] };

	const gruppi = $derived.by((): ComuneGruppo[] => {
		const byComune = new Map<string, SegmentRow[]>();
		for (const s of data.segments) {
			const key = s.comune ?? 'Comune non assegnato';
			if (!byComune.has(key)) byComune.set(key, []);
			byComune.get(key)!.push(s);
		}
		return [...byComune.entries()]
			.map(([comune, tratti]) => {
				const byStrada = new Map<string, SegmentRow[]>();
				for (const t of tratti) {
					if (!byStrada.has(t.nome_strada)) byStrada.set(t.nome_strada, []);
					byStrada.get(t.nome_strada)!.push(t);
				}
				const strade = [...byStrada.entries()]
					.map(([strada, ts]) => ({
						strada,
						max: Math.max(...ts.map((t) => t.indice)),
						n: ts.length,
						tratti: ts, // già ordinati per indice desc dal server
					}))
					.sort((a, b) => b.max - a.max);
				return {
					comune,
					max: Math.max(...tratti.map((t) => t.indice)),
					n: tratti.length,
					strade,
				};
			})
			.sort((a, b) => b.max - a.max);
	});

	let openComuni = $state<Set<string>>(new Set());
	let openStrade = $state<Set<string>>(new Set());

	function toggled(set: Set<string>, key: string): Set<string> {
		const next = new Set(set);
		if (next.has(key)) next.delete(key);
		else next.add(key);
		return next;
	}
</script>

<svelte:head>
	<title>Piano manutenzioni · SaferRoads Vicenza</title>
</svelte:head>

<div class="mx-auto max-w-4xl px-4 sm:px-6 py-8">
	<h1 class="text-2xl font-bold tracking-tight">Dove intervenire prima</h1>
	<p class="mt-1 text-sm text-neutral-600">
		Comuni, strade e tratte in ordine di pericolosità storica (2010–2023). Apri un comune per
		vedere le sue strade, una strada per vedere le singole tratte.
	</p>

	<div class="mt-6 flex flex-col gap-2">
		{#each gruppi as g (g.comune)}
			{@const livC = livelloIndice(g.max)}
			<div class="rounded-xl border border-neutral-200 bg-white overflow-hidden">
				<button
					onclick={() => (openComuni = toggled(openComuni, g.comune))}
					class="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-neutral-50"
				>
					<span class="inline-block rounded-md px-2 py-0.5 text-xs font-semibold {livC.badge}">
						{livC.label}
					</span>
					<span class="font-medium">{g.comune}</span>
					<span class="ml-auto text-xs text-neutral-400">{g.n} tratte</span>
					<span class="text-neutral-400">{openComuni.has(g.comune) ? '▾' : '▸'}</span>
				</button>

				{#if openComuni.has(g.comune)}
					{#each g.strade as st (g.comune + st.strada)}
						{@const livS = livelloIndice(st.max)}
						{@const stradaKey = g.comune + '|' + st.strada}
						<button
							onclick={() => (openStrade = toggled(openStrade, stradaKey))}
							class="flex w-full items-center gap-3 border-t border-neutral-100 px-4 py-2 pl-8 text-left text-sm hover:bg-neutral-50"
						>
							<span class="inline-block rounded-md px-2 py-0.5 text-[11px] font-semibold {livS.badge}">
								{livS.label}
							</span>
							<span>{st.strada}</span>
							<span class="ml-auto text-xs text-neutral-400">{st.n} tratte</span>
							<span class="text-neutral-400">{openStrade.has(stradaKey) ? '▾' : '▸'}</span>
						</button>

						{#if openStrade.has(stradaKey)}
							{#each st.tratti as t (t.id)}
								{@const livT = livelloIndice(t.indice)}
								<div class="flex items-center gap-3 border-t border-neutral-50 px-4 py-1.5 pl-14 text-sm">
									<span class="inline-block rounded-md px-2 py-0.5 text-[11px] font-semibold {livT.badge}">
										{t.indice.toFixed(0)}
									</span>
									<span class="text-neutral-700">km {t.km_idx}</span>
									<span
										class="text-xs text-neutral-400"
										title="attraversamenti {t.n_attraversamenti ?? 0} · semafori {t.n_semafori ?? 0} · autovelox {t.n_autovelox ?? 0} · lampioni {t.n_lampioni ?? 0} · limite {t.maxspeed_med ?? '—'}"
									>
										{t.n_incidenti} incidenti
										{#if t.tot_morti > 0}<span class="font-semibold text-red-700"> · {t.tot_morti} morti</span>{/if}
										{#if t.tot_feriti > 0} · {t.tot_feriti} feriti{/if}
									</span>
									<a
										href={`/analisi?tratta=${t.id}`}
										class="ml-auto text-xs text-blue-700 hover:underline"
									>vedi su mappa →</a>
								</div>
							{/each}
						{/if}
					{/each}
				{/if}
			</div>
		{/each}
	</div>
</div>
