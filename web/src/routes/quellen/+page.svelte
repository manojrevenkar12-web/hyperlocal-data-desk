<script lang="ts">
  import State from "$lib/components/State.svelte";
  import SourceGrid from "$lib/features/sources/SourceGrid.svelte";
  import { num } from "$lib/format";
  import { report } from "$lib/report.svelte";
  const sc = $derived(report.data?.showcase);
  const v = (n: string, k: string) => report.data?.designs.find((d) => d.name === n)?.stats[k]?.value ?? 0;
</script>

<svelte:head><title>Quellen · Datendesk</title></svelte:head>

{#if report.status === "loading"}
  <State kind="loading" title="Bericht wird geladen" />
{:else if report.status === "error"}
  <State kind="error" title="Der Bericht konnte nicht geladen werden" detail={report.error ?? ""} onretry={() => report.retry()} />
{:else if !sc?.log.length}
  <State kind="empty" title="Noch keine Veröffentlichungen" detail="Das Labor hat für diese Welt keine Lieferungen aufgezeichnet." />
{:else}
  <header class="intro">
    <h1>Quellen</h1>
    <p class="lede">Vier Quellen, drei Formate, ein Vertrag: Eine Datei, die der Adapter nicht versteht, geht nicht in die Zeitung, sondern zurück ans Amt.
      Ohne diese Prüfungen hätten im Schnitt {num(v("desk_no_checks", "broken_published"), 1)} kaputte Lieferungen pro Saison Leserinnen und Leser erreicht;
      mit ihnen {num(v("desk", "broken_published"), 1)}.</p>
  </header>
  <SourceGrid log={sc.log} />
  {#if sc.checks.length}
    <section class="checks">
      <h2>Prüfprotokoll der Schaufenster-Lieferung</h2>
      <ul>{#each sc.checks as c}<li class:fail={!c.ok}><strong>{c.name}</strong> {c.detail}</li>{/each}</ul>
    </section>
  {/if}
{/if}

<style>
  .intro { display: grid; gap: var(--s-3); margin-bottom: var(--s-5); }
  .lede { font-family: var(--font-text); font-size: var(--t-md); line-height: 1.45; max-width: 64ch; }
  .checks { margin-top: var(--s-6); display: grid; gap: var(--s-3); }
  .checks ul { list-style: none; padding: 0; display: grid; gap: 2px; }
  .checks li { background: var(--sheet); padding: 6px var(--s-3); font-size: var(--t-sm); }
  .checks li.fail { background: var(--hold-soft); }
  .checks strong { display: inline-block; min-width: 9rem; font-weight: 500; }
</style>
