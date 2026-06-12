<script lang="ts">
	import type { PageData } from './$types';

	let { data }: { data: PageData } = $props();

	const CARDS = [
		{
			href: '/analisi', icona: '📊', titolo: 'Analisi storica',
			testo: 'Dove e perché succedono gli incidenti: mappa e fattori, dal 2010 a oggi.',
			kpi: `${data.kpi.incidenti} incidenti analizzati`,
		},
		{
			href: '/previsione', icona: '🌦', titolo: 'Previsione',
			testo: 'Quanto diventa rischiosa ogni tratta quando cambiano meteo e orario.',
			kpi: 'rischio per scenario',
		},
		{
			href: '/priorita', icona: '🛠', titolo: 'Piano manutenzioni',
			testo: 'Dove intervenire prima: comuni, strade e tratte in ordine di priorità.',
			kpi: `${data.kpi.critiche} tratte critiche su ${data.kpi.totale}`,
		},
		{
			href: '/cittadino', icona: '👥', titolo: 'Cittadino',
			testo: 'La mappa pubblica del rischio e le segnalazioni di chi la strada la vive.',
			kpi: `${data.kpi.segnalazioni} segnalazioni ricevute`,
		},
	];
</script>

<svelte:head>
	<title>SaferRoads Vicenza</title>
</svelte:head>

<div class="mx-auto max-w-5xl px-4 sm:px-6 py-8 sm:py-12">
	<h1 class="text-3xl font-bold tracking-tight">Strade più sicure, decisioni più semplici.</h1>
	<p class="mt-2 max-w-2xl text-neutral-600">
		Il rischio di incidente sulle strade provinciali di Vicenza, spiegato in modo che chiunque
		possa capirlo — e usarlo per decidere.
	</p>

	<div class="mt-6 flex flex-wrap gap-3">
		<div class="rounded-xl border border-neutral-200 bg-white px-5 py-3">
			<div class="text-2xl font-bold">{data.kpi.incidenti}</div>
			<div class="text-xs text-neutral-500">incidenti 2010–2023</div>
		</div>
		<div class="rounded-xl border border-neutral-200 bg-white px-5 py-3">
			<div class="text-2xl font-bold">{data.kpi.km} km</div>
			<div class="text-xs text-neutral-500">di strade monitorate</div>
		</div>
		<div class="rounded-xl border border-red-100 bg-red-50 px-5 py-3">
			<div class="text-2xl font-bold text-red-700">{data.kpi.critiche}</div>
			<div class="text-xs text-red-600">tratte a rischio critico</div>
		</div>
	</div>

	<div class="mt-8 grid gap-4 sm:grid-cols-2">
		{#each CARDS as card (card.href)}
			<a
				href={card.href}
				class="group rounded-2xl border border-neutral-200 bg-white p-5 transition hover:border-blue-300 hover:shadow-md"
			>
				<div class="text-2xl">{card.icona}</div>
				<h2 class="mt-2 text-lg font-semibold group-hover:text-blue-800">{card.titolo}</h2>
				<p class="mt-1 text-sm text-neutral-600">{card.testo}</p>
				<div class="mt-3 text-xs font-medium text-blue-700">{card.kpi} →</div>
			</a>
		{/each}
	</div>

	<p class="mt-8 text-xs text-neutral-400">
		Corridoi SP 46 Pasubio · SP 349 Costo · SP 350 Val d'Astico — dati Provincia di Vicenza,
		ARPAV, OpenStreetMap.
	</p>
</div>
