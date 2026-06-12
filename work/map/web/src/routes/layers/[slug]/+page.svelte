<script lang="ts">
	import LayerMap from '$lib/components/LayerMap.svelte';
	import type { PageData } from './$types';
	let { data }: { data: PageData } = $props();
	const layer = $derived(data.layer);
	const filterFields = $derived(data.filterFields);
	const filterOptions = $derived(data.filterOptions);
</script>

<svelte:head>
	<title>{layer.title} · geo-sentinel</title>
</svelte:head>

<section>
	<a href="/catalog" class="text-sm text-neutral-500 hover:text-neutral-800">← catalog</a>

	<header class="mt-3">
		<div class="flex items-start justify-between gap-3">
			<h1 class="text-2xl font-bold tracking-tight">{layer.title}</h1>
			<span
				class="shrink-0 text-xs px-2 py-1 rounded-md font-medium"
				class:bg-blue-100={layer.kind === 'vector'}
				class:text-blue-800={layer.kind === 'vector'}
				class:bg-amber-100={layer.kind === 'raster'}
				class:text-amber-800={layer.kind === 'raster'}
			>
				{layer.kind}
			</span>
		</div>

		{#if layer.description}
			<p class="mt-2 text-neutral-600">{layer.description}</p>
		{/if}

		<div class="mt-3 flex flex-wrap items-center gap-3 text-xs text-neutral-500">
			{#each layer.tags as tag (tag)}
				<span class="px-2 py-0.5 rounded bg-neutral-100">{tag}</span>
			{/each}
			{#if layer.sourceUrl}
				<a
					href={layer.sourceUrl}
					class="underline"
					target="_blank"
					rel="noopener noreferrer">source</a
				>
			{/if}
		</div>
	</header>

	<div class="mt-6">
		<LayerMap {layer} {filterFields} {filterOptions} />
	</div>
</section>
