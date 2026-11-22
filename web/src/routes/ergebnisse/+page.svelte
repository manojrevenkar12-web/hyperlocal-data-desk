<script lang="ts">
  import State from "$lib/components/State.svelte";
  import Bars from "$lib/features/results/Bars.svelte";
  import DesignTable from "$lib/features/results/DesignTable.svelte";
  import { clock, num } from "$lib/format";
  import { report } from "$lib/report.svelte";
  const r = $derived(report.data);
  const main = $derived(r?.designs.filter((d) => !d.ablation) ?? []);
  const abl = $derived(r?.designs.filter((d) => d.ablation || d.name === "desk") ?? []);
</script>

<svelte:head><title>Ergebnisse · Datendesk</title></svelte:head>

{#if report.status === "loading"}
  <State kind="loading" title="Ergebnisse werden geladen" />
{:else if report.status === "error"}
  <State kind="error" title="Der Bericht konnte nicht geladen werden" detail={report.error ?? ""} onretry={() => report.retry()} />
{:else if !r}
  <State kind="empty" title="Noch keine Ergebnisse" detail="„desk study --world dev“ erzeugt den ersten Bericht." />
{:else}
  <header class="intro">
    <h1>Ergebnisse, {r.world === "heldout" ? "zurückgehaltene Welt (einmal gelaufen)" : "Entwicklungswelt"}</h1>
    <p class="muted">{r.seeds.length} Jahrgänge zu je {r.quarters} Quartalen, {num(r.municipalities)} Gemeinden, vier Quellen; im Schnitt {num(r.stories_per_seed, 0)} eingepflanzte Geschichten je Jahrgang. Alle Verfahren lesen dieselben Dateien mit denselben Modellfehlern. Kleine Zahlen sind 95-%-Intervalle über die Jahrgänge.</p>
  </header>
  <div class="top">
    <Bars designs={main} metric="budget_found" caption="Geschichten unter den acht Hinweisen je Lieferung" />
    <section class="gates">
      <h2>{r.gates.filter((g) => g.pass).length} von {r.gates.length} Schwellen erfüllt</h2>
      <p class="muted">Vor dem Lauf der zurückgehaltenen Welt festgelegt, in <code>config/gates.json</code>.</p>
      <ul>{#each r.gates as g}<li class:fail={!g.pass}><span aria-hidden="true">{g.pass ? "✓" : "✕"}</span><span class="sr-only">{g.pass ? "erfüllt:" : "verfehlt:"}</span><span>{g.name}</span><span class="muted">{g.rule === "at least" ? "mind." : "höchstens"} {g.want}, erreicht {g.got}</span></li>{/each}</ul>
    </section>
  </div>
  <DesignTable designs={main} caption="Die Verfahren" />
  <DesignTable designs={abl} caption="Der Datendesk, jeweils ohne ein Teil" />
  <div class="wrap">
    <table>
      <caption>Wahlabend</caption>
      <thead><tr><th scope="col">Verfahren</th><th scope="col">falsch ausgerufene Kreise je Abend</th><th scope="col">Ausrufen im Median um</th><th scope="col">Gemeinde-Minuten mit falschen Zahlen</th></tr></thead>
      <tbody>{#each r.night as d}<tr class:desk={d.name === "desk"}><th scope="row">{d.label}</th><td>{num(d.stats.wrong_calls.value, 2)}</td><td>{clock(d.stats.median_call_minute.value)} Uhr</td><td>{num(d.stats.wrong_figures_minutes.value)}</td></tr>{/each}</tbody>
    </table>
  </div>
{/if}

<style>
  :global(main) > * + * { margin-top: var(--s-6); }
  .intro { display: grid; gap: var(--s-3); }
  .top { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: var(--s-6); align-items: start; }
  .gates { display: grid; gap: var(--s-2); }
  .gates ul { list-style: none; padding: 0; margin: 0; display: grid; gap: 2px; }
  .gates li { display: grid; grid-template-columns: 1.4rem 1fr auto; gap: var(--s-3); padding: 8px var(--s-3); background: var(--sheet); font-size: var(--t-sm); }
  .gates li span:first-child { color: var(--ok); font-weight: 700; }
  .gates li.fail { background: var(--hold-soft); }
  .gates li.fail span:first-child { color: var(--hold); }
  .wrap { overflow-x: auto; background: var(--sheet); border: 1px solid var(--rule); border-radius: var(--radius); }
  table { border-collapse: collapse; width: 100%; font-size: var(--t-sm); }
  caption { text-align: left; padding: var(--s-3) var(--s-4); font-family: var(--font-text); font-weight: 600; font-size: var(--t-md); }
  th, td { padding: 8px 12px; border-top: 1px solid var(--rule); text-align: right; }
  th:first-child { text-align: left; font-weight: 500; }
  thead th { color: var(--ink-2); font-weight: 500; }
  tr.desk { background: var(--gold-soft); }
  @media (max-width: 1000px) { .top { grid-template-columns: 1fr; } }
</style>
