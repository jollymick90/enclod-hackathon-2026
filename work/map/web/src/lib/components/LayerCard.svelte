<script lang="ts">
	import type { Layer } from '$lib/types';
	let { layer }: { layer: Layer } = $props();
</script>

<a
	href={`/layers/${layer.slug}`}
	class="block rounded-xl border border-neutral-200 bg-white p-5 hover:border-neutral-400 transition"
>
	<div class="flex items-start justify-between gap-3">
		<h2 class="font-semibold text-lg leading-tight">{layer.title}</h2>
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
		<p class="mt-2 text-sm text-neutral-600 line-clamp-3">{layer.description}</p>
	{/if}

	{#if layer.tags.length}
		<div class="mt-4 flex flex-wrap gap-1.5">
			{#each layer.tags as tag (tag)}
				<span class="text-xs px-2 py-0.5 rounded bg-neutral-100 text-neutral-600">{tag}</span>
			{/each}
		</div>
	{/if}
</a>
