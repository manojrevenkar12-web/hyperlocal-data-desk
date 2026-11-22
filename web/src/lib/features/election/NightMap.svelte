<script lang="ts">
  // The 44 districts at one minute of election night: a called district in its party's colour, an open one hatched
  // in the colour of whoever leads the count so far. A wrong call is crossed out once the night is over.
  import { geoMercator, geoPath } from "d3";
  import { PARTY } from "$lib/scales";
  import type { Frame } from "$lib/types";

  let { kreise, frame, winners, final, title }: {
    kreise: GeoJSON.FeatureCollection; frame: Frame | undefined; winners: Record<string, string>; final: boolean; title: string;
  } = $props();
  const W = 420, H = 460;
  const path = $derived(geoPath(geoMercator().fitSize([W, H], kreise)));
  const wrong = $derived(final && frame ? Object.entries(frame.calls).filter(([k, p]) => winners[k] !== p).length : 0);
  const called = $derived(frame ? Object.keys(frame.calls).length : 0);
</script>

<figure>
  <figcaption><strong>{title}</strong><span class="muted">{called} von 44 Kreisen ausgerufen{#if final}, davon {wrong} falsch{/if}</span></figcaption>
  <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`${title}: ${called} Kreise ausgerufen`}>
    <defs>
      {#each Object.entries(PARTY) as [p, c]}
        <pattern id={`h-${title.length}-${p}`} width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="6" height="6" fill="var(--sheet)" /><line x1="0" y1="0" x2="0" y2="6" stroke={c} stroke-width="2.4" />
        </pattern>
      {/each}
    </defs>
    {#each kreise.features as f}
      {@const k = (f.properties as { ags: string }).ags}
      {@const call = frame?.calls[k]}
      {@const lead = frame?.leaders[k]}
      <path d={path(f) ?? ""} fill={call ? PARTY[call] : lead ? `url(#h-${title.length}-${lead})` : "var(--nodata)"} stroke="var(--sheet)" stroke-width="1">
        <title>{(f.properties as { name: string }).name}: {call ? `ausgerufen für ${call}` : lead ? `${lead} vorn, offen` : "noch keine Ergebnisse"}{final && call && call !== winners[k] ? ` (Ergebnis: ${winners[k]})` : ""}</title>
      </path>
      {#if final && call && call !== winners[k]}
        {@const c = path.centroid(f)}
        <text x={c[0]} y={c[1] + 5} text-anchor="middle" class="x">✕</text>
      {/if}
    {/each}
  </svg>
</figure>

<style>
  figure { margin: 0; display: grid; gap: var(--s-2); }
  figcaption { display: flex; justify-content: space-between; gap: var(--s-3); flex-wrap: wrap; }
  svg { width: 100%; height: auto; background: var(--sheet); border: 1px solid var(--rule); border-radius: var(--radius); }
  path { transition: fill 280ms var(--ease); }
  .x { fill: #fff; stroke: var(--hold); stroke-width: 3; paint-order: stroke; font-size: 18px; font-weight: 700; }
</style>
