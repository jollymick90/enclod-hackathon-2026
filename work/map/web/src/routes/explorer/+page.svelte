<script lang="ts">
	import MultiLayerMap from '$lib/components/MultiLayerMap.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>Explorer · Road Condition Intelligence</title>
</svelte:head>

<section>
	<div class="flex items-baseline justify-between">
		<div>
			<h1 class="text-2xl font-bold tracking-tight">Explorer multi-layer</h1>
			<p class="mt-1 text-sm text-neutral-500">
				Attiva e disattiva i layer con i toggle a sinistra. I layer OSM sono disattivati di default.
			</p>
		</div>
		<a href="/catalog" class="text-sm text-neutral-500 hover:text-neutral-800">← catalog</a>
	</div>

	<div class="mt-5">
		<MultiLayerMap layers={data.layers} />
	</div>
</section>
