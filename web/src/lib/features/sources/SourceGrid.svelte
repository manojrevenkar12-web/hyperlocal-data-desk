<script lang="ts">
  // Every release of the season by source and quarter: published as it came, published after the office corrected it,
  // or published although the file changed shape, because the desk understood the change.
  import { DRIFT, INDICATOR, quarter } from "$lib/format";
  import type { LogEntry } from "$lib/types";
  let { log }: { log: LogEntry[] } = $props();
  const indicators = $derived([...new Set(log.map((l) => l.indicator))]);
  const periods = $derived([...new Set(log.map((l) => l.period))].sort());
  const at = (i: string, p: string) => log.find((l) => l.indicator === i && l.period === p);
  function kind(e: LogEntry | undefined): "ok" | "held" | "adapted" | "none" {
    if (!e) return "none";
    if (e.quarantined) return "held";
    return e.drift ? "adapted" : "ok";
  }
  const LABEL = { ok: "veröffentlicht", held: "angehalten, nach Korrektur veröffentlicht", adapted: "Format geändert, verstanden", none: "keine Datei" };
</script>

<div class="wrap">
  <table>
    <caption class="sr-only">Veröffentlichungen nach Quelle und Quartal</caption>
    <thead><tr><th scope="col">Quelle</th>{#each periods as p}<th scope="col">{p.replace("Q", " Q")}</th>{/each}</tr></thead>
    <tbody>
      {#each indicators as i}
        <tr>
          <th scope="row">{INDICATOR[i]}</th>
          {#each periods as p}
            {@const e = at(i, p)}
            {@const k = kind(e)}
            <td class={k} title={`${quarter(p)}: ${LABEL[k]}${e?.drift ? ` (${DRIFT[e.drift] ?? e.drift})` : ""}${e?.delay_days ? `, ${e.delay_days} Tage später` : ""}`}>
              <span aria-hidden="true">{k === "ok" ? "" : k === "held" ? "!" : "~"}</span>
              <span class="sr-only">{LABEL[k]}</span>
            </td>
          {/each}
        </tr>
      {/each}
    </tbody>
  </table>
</div>
<ul class="legend">
  <li><i class="ok"></i>veröffentlicht</li>
  <li><i class="adapted">~</i>Format geändert, vom Adapter verstanden</li>
  <li><i class="held">!</i>angehalten, Rückfrage beim Amt, korrigiert veröffentlicht</li>
</ul>

<style>
  .wrap { overflow-x: auto; }
  table { border-collapse: separate; border-spacing: 3px; font-size: var(--t-sm); }
  th { font-weight: 500; text-align: left; color: var(--ink-2); padding: 2px 8px 2px 0; white-space: nowrap; }
  thead th { font-size: var(--t-xs); text-align: center; }
  td { width: 44px; height: 32px; border-radius: 3px; text-align: center; font-weight: 600; }
  td.ok { background: var(--ok-soft); }
  td.adapted { background: var(--gold-soft); color: var(--gold-ink); }
  td.held { background: var(--hold-soft); color: var(--hold); }
  td.none { background: transparent; border: 1px dashed var(--rule); }
  .legend { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: var(--s-5); font-size: var(--t-sm); color: var(--ink-2); }
  .legend i { display: inline-grid; place-items: center; width: 22px; height: 16px; border-radius: 3px; margin-right: 6px; font-style: normal; font-weight: 600; vertical-align: middle; }
  .legend .ok { background: var(--ok-soft); }
  .legend .adapted { background: var(--gold-soft); color: var(--gold-ink); }
  .legend .held { background: var(--hold-soft); color: var(--hold); }
</style>
