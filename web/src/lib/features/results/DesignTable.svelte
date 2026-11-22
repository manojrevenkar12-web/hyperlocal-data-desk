<script lang="ts">
  import { num } from "$lib/format";
  import type { DesignReport, Stat } from "$lib/types";
  let { designs, caption }: { designs: DesignReport[]; caption: string } = $props();
  const COLS: { k: string; label: string; d: number; scale?: number }[] = [
    { k: "budget_found", label: "Geschichten unter den Top 8", d: 1 },
    { k: "stories_found", label: "Geschichten aus starken Hinweisen", d: 1 },
    { k: "precision", label: "Anteil echter starker Hinweise", d: 0, scale: 100 },
    { k: "hours_per_story", label: "Stunden je Geschichte", d: 1 },
    { k: "wrong_texts_per_1000", label: "Texte mit falscher Zahl je 1.000", d: 1 },
    { k: "wrong_notes_per_100", label: "Hinweise mit falscher Zahl je 100", d: 1 },
    { k: "broken_published", label: "Kaputte Lieferungen veröffentlicht", d: 1 },
  ];
  const f = (s: Stat, c: (typeof COLS)[number]) => num(s.value * (c.scale ?? 1), c.d) + (c.scale ? " %" : "");
  const ci = (s: Stat, c: (typeof COLS)[number]) => (s.lo === s.hi ? "" : `${num(s.lo * (c.scale ?? 1), c.d)} bis ${num(s.hi * (c.scale ?? 1), c.d)}`);
</script>

<div class="wrap">
  <table>
    <caption>{caption}</caption>
    <thead><tr><th scope="col">Verfahren</th>{#each COLS as c}<th scope="col">{c.label}</th>{/each}</tr></thead>
    <tbody>
      {#each designs as d}
        <tr class:desk={d.name === "desk"}>
          <th scope="row"><span>{d.label}</span>{#if d.about}<small>{d.about}</small>{/if}</th>
          {#each COLS as c}<td>{f(d.stats[c.k], c)}{#if ci(d.stats[c.k], c)}<small>{ci(d.stats[c.k], c)}</small>{/if}</td>{/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>

<style>
  .wrap { overflow-x: auto; background: var(--sheet); border: 1px solid var(--rule); border-radius: var(--radius); }
  table { border-collapse: collapse; width: 100%; font-size: var(--t-sm); }
  caption { text-align: left; padding: var(--s-3) var(--s-4); font-family: var(--font-text); font-weight: 600; font-size: var(--t-md); }
  th, td { padding: 8px 12px; border-top: 1px solid var(--rule); vertical-align: top; }
  thead th { font-weight: 500; color: var(--ink-2); text-align: right; vertical-align: bottom; max-width: 9rem; }
  thead th:first-child, tbody th { text-align: left; }
  tbody th { font-weight: 500; min-width: 15rem; }
  tbody th small { display: block; font-weight: 400; color: var(--ink-3); max-width: 46ch; }
  td { text-align: right; white-space: nowrap; }
  td small { display: block; color: var(--ink-3); }
  tr.desk { background: var(--gold-soft); }
</style>
