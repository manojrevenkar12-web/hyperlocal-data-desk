<script lang="ts">
  // The 1,101 municipalities shaded by rate per 1,000 inhabitants; the desk's leads ringed in gold, the spreadsheet's
  // picks dashed. No basemap tiles: the outlines are the map, so it loads offline and quickly.
  import "maplibre-gl/dist/maplibre-gl.css";
  import { onDestroy, onMount } from "svelte";
  import { num } from "$lib/format";
  import { quantileBreaks, RAMP, stepOf } from "$lib/scales";

  let { values, leads, picks, selected, onselect }: {
    values: Record<string, number | null>; leads: string[]; picks: string[]; selected: string | null; onselect: (k: string) => void;
  } = $props();

  let el: HTMLDivElement;
  let map: import("maplibre-gl").Map | null = null;
  let status = $state<"loading" | "ready" | "error">("loading");
  let hover = $state<{ name: string; value: number | null } | null>(null);
  const breaks = $derived(quantileBreaks(Object.values(values).filter((v): v is number => v != null)));

  function css(name: string): string {
    return getComputedStyle(document.documentElement).getPropertyValue(name.slice(4, -1)).trim() || "#999";
  }

  onMount(async () => {
    try {
      const [{ default: maplibre }, geo] = await Promise.all([import("maplibre-gl"), fetch("/data/gemeinden.geojson").then((r) => r.json())]);
      for (const f of geo.features) {
        const a = f.properties.ags as string;
        f.properties.step = stepOf(values[a], breaks);
        f.properties.lead = leads.includes(a) || leads.includes(a.slice(0, 5)) ? 1 : 0;
        f.properties.pick = picks.includes(a) ? 1 : 0;
        f.properties.value = values[a];
      }
      map = new maplibre.Map({
        container: el,
        style: { version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": css("var(--sheet)") } }] },
        bounds: [[7.45, 47.5], [10.55, 49.82]],
        attributionControl: false,
        dragRotate: false,
        fadeDuration: 0,
        renderWorldCopies: false,
      });
      map.on("load", () => {
        if (!map) return;
        map.resize();
        map.fitBounds([[7.45, 47.5], [10.55, 49.82]], { padding: 12, duration: 0 });
        map.addSource("g", { type: "geojson", data: geo, promoteId: "ags", maxzoom: 9, buffer: 64 });
        const fill: unknown[] = ["match", ["get", "step"], -1, css("var(--nodata)")];
        RAMP.forEach((c, i) => fill.push(i, css(c)));
        fill.push(css("var(--nodata)"));
        map.addLayer({ id: "fill", type: "fill", source: "g", paint: { "fill-color": fill as never } });
        map.addLayer({ id: "edge", type: "line", source: "g", paint: { "line-color": css("var(--sheet)"), "line-width": 0.4 } });
        map.addLayer({ id: "pick", type: "line", source: "g", filter: ["==", ["get", "pick"], 1], paint: { "line-color": css("var(--ink)"), "line-width": 1.6, "line-dasharray": [2, 1.5] } });
        map.addLayer({ id: "lead", type: "line", source: "g", filter: ["==", ["get", "lead"], 1], paint: { "line-color": css("var(--gold)"), "line-width": 3 } });
        map.on("mousemove", "fill", (e) => {
          const p = e.features?.[0]?.properties;
          hover = p ? { name: String(p.name), value: p.value == null || p.value === "null" ? null : Number(p.value) } : null;
        });
        map.on("mouseleave", "fill", () => (hover = null));
        map.on("click", "fill", (e) => {
          const a = e.features?.[0]?.properties?.ags as string | undefined;
          if (a && (leads.includes(a) || leads.includes(a.slice(0, 5)))) onselect(leads.includes(a) ? a : a.slice(0, 5));
        });
        map.once("idle", () => (status = "ready")); // every tile drawn, not just the style loaded  // every tile drawn, not just the style loaded
      });
    } catch {
      status = "error";
    }
  });
  onDestroy(() => map?.remove());
</script>

<figure class="map" data-status={status}>
  <div class="canvas" bind:this={el} role="img" aria-label="Karte der Gemeinden nach Wert je 1.000 Einwohner, Recherchehinweise gold umrandet"></div>
  {#if status === "loading"}<div class="overlay" aria-hidden="true">Karte wird geladen …</div>{/if}
  {#if status === "error"}<div class="overlay" role="alert">Die Karte konnte nicht geladen werden. Die Liste rechts enthält alle Hinweise.</div>{/if}
  <figcaption>
    <span class="legend" aria-label="Legende">
      {#each RAMP as c, i}<i style:background={c} title={i === 0 ? `unter ${num(breaks[0] ?? 0, 1)}` : `ab ${num(breaks[i - 1] ?? 0, 1)}`}></i>{/each}
      <span>je 1.000 Einwohner, niedrig bis hoch (Fünftel)</span>
      <i class="nodata"></i><span>geheim</span>
      <i class="ring"></i><span>Recherchehinweis</span>
      <i class="dash"></i><span>Tabellen-Routine</span>
    </span>
    <span class="hover" aria-live="polite">{hover ? `${hover.name}: ${hover.value == null ? "Wert geheim" : num(hover.value, 2) + " je 1.000"}` : "Auf eine Gemeinde zeigen"}</span>
  </figcaption>
</figure>

<style>
  .map { margin: 0; position: relative; display: grid; gap: var(--s-2); }
  .canvas { height: min(68vh, 640px); border: 1px solid var(--rule); border-radius: var(--radius); background: var(--sheet); }
  .overlay { position: absolute; inset: 0 0 48px 0; display: grid; place-items: center; color: var(--ink-2); background: color-mix(in srgb, var(--sheet) 80%, transparent); }
  figcaption { display: flex; flex-wrap: wrap; justify-content: space-between; gap: var(--s-3); font-size: var(--t-sm); color: var(--ink-2); }
  .legend { display: inline-flex; align-items: center; gap: 4px; flex-wrap: wrap; }
  .legend i { width: 18px; height: 12px; display: inline-block; border-radius: 2px; }
  .legend span { margin-right: var(--s-3); margin-left: 4px; }
  .legend .nodata { background: var(--nodata); }
  .legend .ring { background: transparent; border: 3px solid var(--gold); }
  .legend .dash { background: transparent; border: 1.6px dashed var(--ink); }
</style>
