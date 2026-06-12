<script lang="ts">
	import { onMount } from 'svelte';
	import SectionMap from '$lib/components/SectionMap.svelte';
	import SchedaTratta from '$lib/components/SchedaTratta.svelte';
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const TIPI = [
		{ value: 'incidente_lieve', label: 'Incidente lieve (constatazione amichevole)' },
		{ value: 'strada_danneggiata', label: 'Strada danneggiata' },
		{ value: 'pericolo', label: 'Situazione di pericolo' },
	];

	const VUOTO: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

	let segnalazioni = $state<GeoJSON.FeatureCollection>(VUOTO);
	let mode = $state<'idle' | 'pick' | 'form'>('idle');
	let pos = $state<{ lng: number; lat: number } | null>(null);
	let tipo = $state('pericolo');
	let descrizione = $state('');
	let invio = $state(false);
	let sendErr = $state('');
	let msg = $state('');
	let selected = $state<number | null>(null);

	async function carica() {
		try {
			segnalazioni = await (await fetch('/api/segnalazioni')).json();
		} catch {
			/* la mappa resta senza segnalazioni: non bloccante */
		}
	}
	onMount(carica);

	const puntoNuovo = $derived.by((): GeoJSON.FeatureCollection => ({
		type: 'FeatureCollection',
		features: pos
			? [{ type: 'Feature', geometry: { type: 'Point', coordinates: [pos.lng, pos.lat] }, properties: {} }]
			: [],
	}));

	function onMapClick(lngLat: { lng: number; lat: number }) {
		if (mode !== 'pick') return;
		pos = lngLat;
		mode = 'form';
	}

	function usaGps() {
		sendErr = '';
		navigator.geolocation.getCurrentPosition(
			(p) => {
				pos = { lng: p.coords.longitude, lat: p.coords.latitude };
				mode = 'form';
			},
			() => { sendErr = 'Posizione GPS non disponibile: tocca la mappa.'; },
		);
	}

	function annulla() {
		mode = 'idle';
		pos = null;
		sendErr = '';
	}

	async function invia() {
		if (!pos) { sendErr = 'Indica il punto sulla mappa.'; return; }
		invio = true;
		sendErr = '';
		try {
			const res = await fetch('/api/segnalazioni', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ tipo, descrizione, lng: pos.lng, lat: pos.lat }),
			});
			if (!res.ok) throw new Error((await res.json())?.message ?? res.statusText);
			msg = 'Grazie! La tua segnalazione è sulla mappa.';
			descrizione = '';
			annulla();
			await carica();
			setTimeout(() => (msg = ''), 4000);
		} catch (e) {
			// i campi restano compilati: l'utente può riprovare
			sendErr = e instanceof Error ? e.message : 'Invio non riuscito, riprova.';
		} finally {
			invio = false;
		}
	}
</script>

<svelte:head>
	<title>Cittadino · SaferRoads Vicenza</title>
</svelte:head>

<div class="h-full">
	<SectionMap
		layers={data.layers}
		visible={new Set(['rischio-storico'])}
		interactive={['rischio-storico']}
		geojsonLayers={[
			{
				id: 'segnalazioni',
				data: segnalazioni,
				paint: {
					'circle-color': ['match', ['get', 'tipo'],
						'incidente_lieve', '#e03131',
						'strada_danneggiata', '#f08c00',
						'#9c36b5'],
					'circle-radius': 7,
					'circle-stroke-width': 2,
					'circle-stroke-color': '#ffffff',
				},
			},
			{
				id: 'nuova-segnalazione',
				data: puntoNuovo,
				paint: {
					'circle-color': '#1971c2', 'circle-radius': 9,
					'circle-stroke-width': 3, 'circle-stroke-color': '#ffffff',
				},
			},
		]}
		onFeatureClick={(slug, props) => {
			if (slug === 'rischio-storico' && mode === 'idle') selected = Number(props.id);
		}}
		{onMapClick}
	>
		<!-- intestazione breve -->
		<div class="absolute left-3 top-3 z-10 rounded-xl border border-neutral-200 bg-white px-3 py-2 text-xs shadow-lg">
			<span class="font-semibold">La tua strada è sicura?</span>
			<span class="hidden sm:inline text-neutral-500"> Tocca una tratta per scoprirlo.</span>
		</div>

		<!-- conferma invio -->
		{#if msg}
			<div class="absolute left-1/2 top-3 z-30 -translate-x-1/2 rounded-xl bg-green-600 px-4 py-2 text-sm font-medium text-white shadow-lg">
				{msg}
			</div>
		{/if}

		<!-- banner modalità scelta punto -->
		{#if mode === 'pick'}
			<div class="absolute inset-x-3 top-14 z-20 rounded-xl bg-blue-600 px-4 py-2 text-center text-sm text-white shadow-lg sm:inset-x-auto sm:left-1/2 sm:-translate-x-1/2">
				Tocca la mappa nel punto da segnalare
				<button onclick={annulla} class="ml-2 underline">annulla</button>
			</div>
		{/if}

		<!-- bottone segnala -->
		{#if mode === 'idle'}
			<button
				onclick={() => { selected = null; mode = 'pick'; }}
				class="absolute bottom-5 right-4 z-20 rounded-full bg-blue-600 px-5 py-3 text-sm font-semibold text-white shadow-xl hover:bg-blue-700"
			>
				＋ Segnala un problema
			</button>
		{/if}

		<!-- form segnalazione: bottom sheet -->
		{#if mode === 'form'}
			<div class="absolute inset-x-0 bottom-0 z-20 rounded-t-2xl border border-neutral-200 bg-white p-4 shadow-xl md:inset-x-auto md:bottom-4 md:right-4 md:w-96 md:rounded-2xl">
				<h2 class="font-semibold">Segnala un problema</h2>
				<label class="mt-2 block text-xs text-neutral-500">
					Cosa vuoi segnalare?
					<select
						bind:value={tipo}
						class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-2 text-sm text-neutral-800"
					>
						{#each TIPI as t (t.value)}<option value={t.value}>{t.label}</option>{/each}
					</select>
				</label>
				<label class="mt-2 block text-xs text-neutral-500">
					Descrizione (facoltativa)
					<textarea
						bind:value={descrizione}
						rows="2"
						maxlength="500"
						placeholder="Es. buca profonda sulla corsia nord"
						class="mt-0.5 w-full rounded-md border border-neutral-300 px-2 py-2 text-sm text-neutral-800"
					></textarea>
				</label>
				<div class="mt-1 flex items-center justify-between text-xs text-neutral-500">
					<span>{pos ? `Punto scelto ✓` : 'Nessun punto scelto'}</span>
					<button onclick={usaGps} class="text-blue-700 hover:underline">usa il GPS</button>
				</div>
				{#if sendErr}<p class="mt-1 text-xs text-red-600">{sendErr}</p>{/if}
				<div class="mt-3 flex gap-2">
					<button
						onclick={invia}
						disabled={invio}
						class="flex-1 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
					>
						{invio ? 'Invio…' : 'Invia segnalazione'}
					</button>
					<button
						onclick={annulla}
						class="rounded-lg border border-neutral-300 px-4 py-2.5 text-sm text-neutral-700 hover:bg-neutral-100"
					>
						Annulla
					</button>
				</div>
			</div>
		{/if}

		<!-- scheda tratta ridotta -->
		{#if selected != null && mode === 'idle'}
			<div class="absolute inset-x-0 bottom-0 z-20 max-h-[55%] md:inset-x-auto md:bottom-3 md:right-3 md:top-3 md:w-96 md:max-h-none">
				<SchedaTratta segmentId={selected} variant="ridotta" onClose={() => (selected = null)} />
			</div>
		{/if}
	</SectionMap>
</div>
