<script lang="ts">
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	let comune = $state('');
	let strada = $state('');
	let limit = $state(30);

	const filtered = $derived(
		data.segments.filter(
			(s) =>
				(!comune || s.comune === comune) &&
				(!strada || s.nome_strada === strada)
		)
	);
	const shown = $derived(filtered.slice(0, limit));

	function badge(indice: number): string {
		if (indice >= 70) return 'bg-red-100 text-red-800';
		if (indice >= 40) return 'bg-orange-100 text-orange-800';
		if (indice >= 15) return 'bg-yellow-100 text-yellow-800';
		return 'bg-green-100 text-green-800';
	}
</script>

<svelte:head>
	<title>Priorità manutenzione · Road Condition Intelligence</title>
</svelte:head>

<section>
	<h1 class="text-2xl font-bold tracking-tight">Priorità di manutenzione</h1>
	<p class="mt-1 text-sm text-neutral-600">
		Segmenti chilometrici dei corridoi SP ordinati per indice di pericolosità storica
		(2010-2023). Filtra per comune o strada per il piano interventi locale.
	</p>

	<div class="mt-5 flex flex-wrap items-end gap-3 text-xs text-neutral-500">
		<label class="flex flex-col gap-1">
			Comune
			<select bind:value={comune} class="rounded-md border border-neutral-300 px-2 py-1 text-sm text-neutral-800">
				<option value="">Tutti</option>
				{#each data.comuni as c (c)}<option value={c}>{c}</option>{/each}
			</select>
		</label>
		<label class="flex flex-col gap-1">
			Strada
			<select bind:value={strada} class="rounded-md border border-neutral-300 px-2 py-1 text-sm text-neutral-800">
				<option value="">Tutte</option>
				{#each data.strade as s (s)}<option value={s}>{s}</option>{/each}
			</select>
		</label>
		<span class="pb-1.5">{filtered.length} segmenti</span>
	</div>

	<div class="mt-4 overflow-x-auto rounded-xl border border-neutral-200 bg-white">
		<table class="w-full text-sm">
			<thead>
				<tr class="border-b border-neutral-200 bg-neutral-50 text-left text-xs text-neutral-500">
					<th class="px-3 py-2">#</th>
					<th class="px-3 py-2">Indice</th>
					<th class="px-3 py-2">Strada</th>
					<th class="px-3 py-2">km</th>
					<th class="px-3 py-2">Comune</th>
					<th class="px-3 py-2 text-right">Incidenti</th>
					<th class="px-3 py-2 text-right">Morti</th>
					<th class="px-3 py-2 text-right">Feriti</th>
					<th class="px-3 py-2 text-right" title="attraversamenti / semafori / autovelox / lampioni entro 50 m">Sicurezza (A/S/V/L)</th>
					<th class="px-3 py-2 text-right">Limite</th>
					<th class="px-3 py-2"></th>
				</tr>
			</thead>
			<tbody>
				{#each shown as s, i (s.id)}
					<tr class="border-b border-neutral-100 last:border-0 hover:bg-neutral-50">
						<td class="px-3 py-2 text-neutral-400">{i + 1}</td>
						<td class="px-3 py-2">
							<span class="inline-block rounded-md px-2 py-0.5 text-xs font-semibold {badge(s.indice)}">
								{s.indice.toFixed(0)}
							</span>
						</td>
						<td class="px-3 py-2 font-medium">{s.nome_strada}</td>
						<td class="px-3 py-2 text-neutral-500">{s.km_idx}</td>
						<td class="px-3 py-2 text-neutral-600">{s.comune ?? '—'}</td>
						<td class="px-3 py-2 text-right">{s.n_incidenti}</td>
						<td class="px-3 py-2 text-right {s.tot_morti > 0 ? 'font-semibold text-red-700' : ''}">{s.tot_morti}</td>
						<td class="px-3 py-2 text-right">{s.tot_feriti}</td>
						<td class="px-3 py-2 text-right text-neutral-500">
							{s.n_attraversamenti ?? 0}/{s.n_semafori ?? 0}/{s.n_autovelox ?? 0}/{s.n_lampioni ?? 0}
						</td>
						<td class="px-3 py-2 text-right text-neutral-500">{s.maxspeed_med ?? '—'}</td>
						<td class="px-3 py-2">
							<a
								class="text-xs text-blue-600 hover:underline"
								href={`/layers/rischio-storico#${s.lng.toFixed(5)},${s.lat.toFixed(5)}`}
							>mappa →</a>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	{#if filtered.length > limit}
		<button
			onclick={() => (limit += 50)}
			class="mt-4 rounded-md border border-neutral-300 px-3 py-1.5 text-sm text-neutral-700 hover:bg-neutral-100"
		>
			Mostra altri ({filtered.length - limit})
		</button>
	{/if}
</section>
