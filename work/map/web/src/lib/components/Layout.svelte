<script lang="ts">
	import { page } from '$app/state';
	let { children } = $props();

	const NAV = [
		{ href: '/analisi', label: 'Analisi' },
		{ href: '/previsione', label: 'Previsione' },
		{ href: '/priorita', label: 'Priorità' },
		{ href: '/cittadino', label: 'Cittadino' },
	];
</script>

<div class="h-dvh flex flex-col bg-neutral-50 text-neutral-900">
	<header class="shrink-0 z-30 border-b border-neutral-200 bg-white">
		<div class="px-3 sm:px-6 h-14 flex items-center justify-between gap-2">
			<a href="/" class="font-semibold tracking-tight text-base sm:text-lg whitespace-nowrap">
				SaferRoads <span class="text-blue-700">Vicenza</span>
			</a>
			<nav class="flex items-center gap-1 sm:gap-3 text-sm overflow-x-auto">
				{#each NAV as item (item.href)}
					<a
						href={item.href}
						class="px-2 py-1 rounded-md whitespace-nowrap transition {page.url.pathname.startsWith(item.href)
							? 'bg-blue-50 text-blue-800 font-medium'
							: 'text-neutral-600 hover:text-neutral-900'}"
					>
						{item.label}
					</a>
				{/each}
			</nav>
		</div>
	</header>

	<main class="flex-1 min-h-0 overflow-y-auto">
		{@render children()}
	</main>
</div>
