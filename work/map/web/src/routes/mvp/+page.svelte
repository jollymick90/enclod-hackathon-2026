<script lang="ts">
	import MultiLayerMap from '$lib/components/MultiLayerMap.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();
</script>

<svelte:head>
	<title>MVP · Road Condition Intelligence</title>
</svelte:head>

<div class="mx-auto max-w-6xl px-6 py-8">
	<section>
		<a href="/" class="text-sm text-neutral-500 hover:text-neutral-800">← home</a>

		<header class="mt-3">
			<h1 class="text-2xl font-bold tracking-tight">Road Condition Intelligence — MVP</h1>
			<p class="mt-1 text-neutral-600">
				Modello predittivo del rischio incidentalità sui corridoi SP 46 · SP 349 · SP 350 della
				provincia di Vicenza.
			</p>

			<div class="mt-4 flex flex-wrap gap-4 text-sm">
				<div class="rounded-lg bg-red-50 border border-red-100 px-4 py-3">
					<div class="text-xl font-bold text-red-700">738</div>
					<div class="text-xs text-red-600 mt-0.5">incidenti reali 2010–2023</div>
				</div>
	<div class="rounded-lg bg-blue-50 border border-blue-100 px-4 py-3">
					<div class="text-xl font-bold text-blue-700">3 corridoi SP</div>
					<div class="text-xs text-blue-600 mt-0.5">SP 46 · SP 349 · SP 350</div>
				</div>
			</div>
		</header>

		<div class="mt-6">
			<MultiLayerMap
				layers={data.layers.filter((l) => l.slug !== 'training-incidenti')}
				defaultVisible={new Set(['rischio-storico', 'osm-roads', 'osm-traffic'])}
				filterOptions={data.filterOptions}
			/>
		</div>
	</section>
</div>
