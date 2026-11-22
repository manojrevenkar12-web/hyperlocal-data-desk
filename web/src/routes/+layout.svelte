<script lang="ts">
  import "../app.css";
  import { page } from "$app/state";
  import { onMount } from "svelte";
  import { report } from "$lib/report.svelte";

  let { children } = $props();
  onMount(() => void report.load());
  const links = [
    { href: "/", label: "Recherche" },
    { href: "/quellen/", label: "Quellen" },
    { href: "/wahlabend/", label: "Wahlabend" },
    { href: "/ergebnisse/", label: "Ergebnisse" },
  ];
</script>

<svelte:head><title>Datendesk</title></svelte:head>

<header class="bar">
  <a class="brand" href="/" aria-label="Datendesk, Recherche">
    <svg viewBox="0 0 28 28" width="26" height="26" aria-hidden="true"><rect x="2" y="2" width="24" height="24" rx="3" fill="var(--ink)" /><rect x="7" y="15" width="3" height="7" fill="var(--gold)" /><rect x="12.5" y="10" width="3" height="12" fill="var(--sheet)" /><rect x="18" y="6" width="3" height="16" fill="var(--sheet)" /></svg>
    <span>Datendesk</span>
  </a>
  <nav aria-label="Bereiche">
    {#each links as l}
      <a href={l.href} aria-current={page.url.pathname === l.href ? "page" : undefined}>{l.label}</a>
    {/each}
  </nav>
  {#if report.hasHeldout}
    <div class="world" role="group" aria-label="Welche simulierte Welt">
      <button type="button" aria-pressed={report.world === "heldout"} onclick={() => report.choose("heldout")}>Zurückgehaltene Welt</button>
      <button type="button" aria-pressed={report.world === "dev"} onclick={() => report.choose("dev")}>Entwicklungswelt</button>
    </div>
  {/if}
</header>
<main>{@render children()}</main>
<footer class="muted">Simulierte Gemeinden in den echten Kreisgrenzen Baden-Württembergs; keine echten Zahlen. Alle Werte stammen aus <code>reports/</code>, erzeugt vom Labor.</footer>

<style>
  .bar { display: flex; align-items: center; gap: var(--s-6); padding: var(--s-3) var(--s-6); background: var(--sheet); border-bottom: 1px solid var(--rule); flex-wrap: wrap; }
  .brand { display: inline-flex; align-items: center; gap: var(--s-2); text-decoration: none; font-family: var(--font-text); font-weight: 600; font-size: var(--t-md); }
  nav { display: flex; gap: var(--s-5); }
  nav a { text-decoration: none; color: var(--ink-2); padding: 6px 0; border-bottom: 3px solid transparent; font-weight: 500; }
  nav a[aria-current="page"] { color: var(--ink); border-bottom-color: var(--gold); }
  .world { margin-left: auto; display: inline-flex; border: 1px solid var(--rule); border-radius: var(--radius); overflow: hidden; }
  .world button { border: 0; background: transparent; padding: 4px 12px; cursor: pointer; font-size: var(--t-sm); }
  .world button[aria-pressed="true"] { background: var(--ink); color: var(--sheet); }
  main { padding: var(--s-5) var(--s-6) var(--s-7); }
  footer { padding: var(--s-4) var(--s-6); border-top: 1px solid var(--rule); font-size: var(--t-sm); }
  @media (max-width: 720px) { .bar, main, footer { padding-left: var(--s-4); padding-right: var(--s-4); } nav { gap: var(--s-4); } }
</style>
