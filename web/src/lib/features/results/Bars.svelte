<script lang="ts">
  // One measure per chart, one axis from zero, the desk in gold, the 95% interval as a whisker.
  import { DESIGN, num } from "$lib/format";
  import type { DesignReport } from "$lib/types";
  let { designs, metric, caption, digits = 1 }: { designs: DesignReport[]; metric: string; caption: string; digits?: number } = $props();
  const rows = $derived([...designs].sort((a, b) => b.stats[metric].value - a.stats[metric].value));
  const max = $derived(Math.max(...designs.map((d) => d.stats[metric].hi), 1e-9) * 1.1);
  const W = 560, L = 230, R = 70, ROW = 28;
  const x = (v: number) => L + (v / max) * (W - L - R);
  let hover = $state<string | null>(null);
</script>

<figure>
  <figcaption>{caption}</figcaption>
  <svg viewBox={`0 0 ${W} ${rows.length * ROW + 6}`} role="img" aria-label={caption}>
    <line x1={x(0)} x2={x(0)} y1="0" y2={rows.length * ROW} class="axis" />
    {#each rows as d, i}
      {@const s = d.stats[metric]}
      <g class:desk={d.name === "desk"} class:on={hover === d.name} onmouseenter={() => (hover = d.name)} onmouseleave={() => (hover = null)} role="presentation">
        <rect class="hit" x="0" y={i * ROW} width={W} height={ROW} />
        <text x={L - 10} y={i * ROW + 18} text-anchor="end" class="name">{DESIGN[d.name]?.label ?? d.label}</text>
        <rect x={x(0)} y={i * ROW + 6} width={Math.max(1, x(s.value) - x(0))} height="16" rx="3" class="bar" />
        {#if s.lo !== s.hi}<line x1={x(s.lo)} x2={x(s.hi)} y1={i * ROW + 14} y2={i * ROW + 14} class="ci" />{/if}
        <text x={x(Math.max(s.hi, s.value)) + 8} y={i * ROW + 18} class="val">{num(s.value, digits)}</text>
      </g>
    {/each}
  </svg>
  <p class="muted small">{#if hover}{@const s = designs.find((d) => d.name === hover)!.stats[metric]}{DESIGN[hover]?.label ?? hover}: {num(s.value, digits)}, 95-%-Intervall {num(s.lo, digits)} bis {num(s.hi, digits)}{:else}Auf einen Balken zeigen für das Intervall über die Jahrgänge{/if}</p>
</figure>

<style>
  figure { margin: 0; display: grid; gap: var(--s-2); }
  figcaption { font-family: var(--font-text); font-weight: 600; font-size: var(--t-md); }
  svg { width: 100%; height: auto; }
  .axis { stroke: var(--ink-3); }
  .hit { fill: transparent; }
  .on .hit { fill: var(--sheet-2); }
  .name { font-size: 13px; fill: var(--ink-2); font-family: var(--font-ui); }
  .desk .name { fill: var(--ink); font-weight: 600; }
  .bar { fill: var(--ink-3); opacity: 0.5; }
  .desk .bar { fill: var(--gold); opacity: 1; }
  .ci { stroke: var(--ink); stroke-width: 1.5; }
  .val { font-size: 13px; fill: var(--ink); font-family: var(--font-ui); }
  .small { font-size: var(--t-sm); }
</style>
