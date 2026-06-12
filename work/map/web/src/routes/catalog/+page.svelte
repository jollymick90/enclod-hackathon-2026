<script lang="ts">
	import LayerCard from '$lib/components/LayerCard.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>Catalog · Road Condition Intelligence</title>
</svelte:head>

<div class="mx-auto max-w-6xl px-6 py-8">
	<section>
		<div class="flex items-baseline justify-between">
			<div>
				<h1 class="text-2xl font-bold tracking-tight">Catalog</h1>
				<p class="mt-1 text-sm text-neutral-500">{data.layers.length} layer pubblicati.</p>
			</div>
			<a href="/explorer" class="text-sm text-violet-600 hover:underline">Explorer multi-layer →</a>
		</div>

		<div class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each data.layers as layer (layer.id)}
				<LayerCard {layer} />
			{/each}
		</div>

		{#if data.layers.length === 0}
			<p class="mt-6 text-neutral-500">Nessun layer ancora.</p>
		{/if}
	</section>
</div>
