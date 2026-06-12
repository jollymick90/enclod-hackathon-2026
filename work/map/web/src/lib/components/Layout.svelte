<script lang="ts">
	let { children } = $props();
</script>

<div class="min-h-screen bg-neutral-50 text-neutral-900">
	<header class="border-b border-neutral-200 bg-white">
		<div class="mx-auto max-w-6xl px-6 py-4 flex items-center justify-between">
			<a href="/" class="font-semibold tracking-tight text-lg">geo-sentinel</a>
			<span class="text-sm text-neutral-500">personal GIS artifacts</span>
		</div>
	</header>

	<main class="mx-auto max-w-6xl px-6 py-8">
		{@render children()}
	</main>

	<footer class="mt-16 border-t border-neutral-200 py-6 text-center text-xs text-neutral-500">
		self-hosted · vector via Martin · raster via TiTiler
	</footer>
</div>
