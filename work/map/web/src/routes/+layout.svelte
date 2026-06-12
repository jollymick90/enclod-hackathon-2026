<script lang="ts">
	import '../app.css';
	import favicon from '$lib/assets/favicon.svg';
	import Layout from '$lib/components/Layout.svelte';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<title>geo-sentinel</title>
</svelte:head>

<Layout>{@render children()}</Layout>
