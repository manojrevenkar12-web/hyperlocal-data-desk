<script lang="ts">
  import State from "$lib/components/State.svelte";
  import LeadList from "$lib/features/leads/LeadList.svelte";
  import LeadMap from "$lib/features/leads/LeadMap.svelte";
  import { INDICATOR, num, quarter } from "$lib/format";
  import { report } from "$lib/report.svelte";

  let selected = $state<string | null>(null);
  const sc = $derived(report.data?.showcase);
  const desk = $derived(report.data?.designs.find((d) => d.name === "desk"));
  const sheet = $derived(report.data?.designs.find((d) => d.name === "spreadsheet"));
</script>

<svelte:head><title>Recherche · Datendesk</title></svelte:head>

{#if report.status === "loading"}
  <State kind="loading" title="Bericht wird geladen" />
{:else if report.status === "error"}
  <State kind="error" title="Der Bericht konnte nicht geladen werden" detail={`${report.error}. Mit „desk study“ und „desk web-data“ neu erzeugen.`} onretry={() => report.retry()} />
{:else if !sc || !sc.leads.length}
  <State kind="empty" title="Keine Hinweise in diesem Bericht" detail="Das Labor hat für das Schaufenster-Quartal keine Hinweise gefunden." />
{:else}
  <header class="intro">
    <h1>{INDICATOR[sc.indicator]}, {quarter(sc.period)}</h1>
    <p class="lede">
      {sc.leads.length === 1 ? "Ein Ort weicht" : `${sc.leads.length} Orte weichen`} so stark von der eigenen Geschichte ab, dass ein Anruf lohnt. Jede Zahl in den Hinweisen ist gegen
      die Daten geprüft.
      {#if desk && sheet}Über alle simulierten Jahrgänge waren {num(100 * desk.stats.precision.value)} von 100 dieser Hinweise echte Geschichten;
        bei der Tabellen-Routine, die nach Prozenten sortiert, {num(100 * sheet.stats.precision.value)} von 100.{/if}
    </p>
  </header>
  <div class="board">
    <LeadMap values={sc.values} leads={sc.leads.map((l) => l.key)} picks={sc.spreadsheet_leads.map((l) => l.key)} {selected} onselect={(k) => (selected = k)} />
    <section aria-labelledby="leads-h">
      <h2 id="leads-h">Recherchehinweise</h2>
      <LeadList leads={sc.leads} {selected} onselect={(k) => (selected = k)} />
      <details class="contrast">
        <summary>Wohin die Tabellen-Routine geschickt hätte</summary>
        <p class="muted">Die acht größten prozentualen Sprünge zum Vorquartal, ohne Grenzänderungen, geheime Werte als null:</p>
        <ul>{#each sc.spreadsheet_leads as s}<li>{s.name}: {num(s.observed)}</li>{/each}</ul>
      </details>
    </section>
  </div>
{/if}

<style>
  .intro { display: grid; gap: var(--s-3); margin-bottom: var(--s-5); }
  .lede { font-family: var(--font-text); font-size: var(--t-md); line-height: 1.45; max-width: 64ch; }
  .board { display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(320px, 1fr); gap: var(--s-6); align-items: start; }
  section { display: grid; gap: var(--s-3); }
  .contrast { background: var(--sheet-2); border-radius: var(--radius); padding: var(--s-3) var(--s-4); }
  .contrast summary { cursor: pointer; font-weight: 500; }
  .contrast ul { margin: var(--s-2) 0 0; padding-left: 1.2rem; columns: 2; }
  @media (max-width: 980px) { .board { grid-template-columns: 1fr; } }
</style>
