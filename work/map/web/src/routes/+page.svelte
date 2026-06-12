<script lang="ts">
	import LayerCard from '$lib/components/LayerCard.svelte';
	import type { PageData } from './$types';
	let { data }: { data: PageData } = $props();
</script>

<section>
	<h1 class="text-2xl font-bold tracking-tight">Catalog</h1>
	<p class="mt-1 text-sm text-neutral-600">Published GIS artifacts.</p>

	<div class="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
		{#each data.layers as layer (layer.id)}
			<LayerCard {layer} />
		{/each}
	</div>

	{#if data.layers.length === 0}
		<p class="mt-6 text-neutral-500">No layers yet.</p>
	{/if}
</section>
