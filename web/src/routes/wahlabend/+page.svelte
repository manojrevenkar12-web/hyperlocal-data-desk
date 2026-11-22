<script lang="ts">
  import { onMount } from "svelte";
  import State from "$lib/components/State.svelte";
  import NightMap from "$lib/features/election/NightMap.svelte";
  import { clock, num } from "$lib/format";
  import { report } from "$lib/report.svelte";
  import { PARTY } from "$lib/scales";

  let kreise = $state<GeoJSON.FeatureCollection | null>(null);
  let geoError = $state(false);
  let i = $state(0);
  onMount(async () => {
    try { kreise = await (await fetch("/data/kreise.geojson")).json(); } catch { geoError = true; }
  });
  const sc = $derived(report.data?.showcase);
  const desk = $derived(sc?.night.desk ?? []);
  const naive = $derived(sc?.night.counted_half ?? []);
  const last = $derived(Math.max(0, desk.length - 1));
  const n = (name: string, k: string) => report.data?.night.find((d) => d.name === name)?.stats[k]?.value ?? 0;
</script>

<svelte:head><title>Wahlabend · Datendesk</title></svelte:head>

{#if report.status === "loading" || (!kreise && !geoError)}
  <State kind="loading" title="Wahlabend wird geladen" />
{:else if report.status === "error" || geoError}
  <State kind="error" title="Der Wahlabend konnte nicht geladen werden" detail={report.error ?? "Kreisgrenzen fehlen"} onretry={() => report.retry()} />
{:else if !desk.length || !kreise}
  <State kind="empty" title="Kein Wahlabend in diesem Bericht" />
{:else}
  <header class="intro">
    <h1>Wahlabend</h1>
    <p class="lede">Dörfer zählen zuerst, Städte zuletzt. Wer einen Kreis ausruft, sobald die Hälfte seiner Gemeinden gezählt ist, liegt im Schnitt
      in {num(n("counted_half", "wrong_calls"), 1)} Kreisen pro Wahlabend falsch. Der Datendesk rechnet aus dem Wechsel in den ausgezählten
      Gemeinden hoch und ruft erst aus, wenn das Intervall eindeutig ist: {num(n("desk", "wrong_calls"), 1)} falsche Kreise, im Median
      {num(n("wait_for_all", "median_call_minute") - n("desk", "median_call_minute"))} Minuten vor dem Ende der Auszählung.</p>
  </header>
  <div class="controls">
    <label for="t">Uhrzeit <output>{clock(desk[i]?.minute ?? 0)} Uhr</output></label>
    <input id="t" type="range" min="0" max={last} step="1" bind:value={i} aria-valuetext={`${clock(desk[i]?.minute ?? 0)} Uhr`} />
    <span class="muted">{desk[i]?.reported ?? 0} von {report.data?.municipalities ?? 0} Gemeinden gemeldet</span>
  </div>
  <div class="maps">
    <NightMap {kreise} frame={desk[i]} winners={sc!.kreis_winner} final={i === last} title="Datendesk" />
    <NightMap {kreise} frame={naive[i]} winners={sc!.kreis_winner} final={i === last} title="Ausrufen bei der Hälfte" />
  </div>
  <ul class="legend">
    {#each Object.entries(PARTY) as [p, c]}<li><i style:background={c}></i>{p}</li>{/each}
    <li><i class="hatch"></i>schraffiert: vorn, aber offen</li>
    <li><i class="x">✕</i>falsch ausgerufen (am Ende sichtbar)</li>
  </ul>
{/if}

<style>
  .intro { display: grid; gap: var(--s-3); margin-bottom: var(--s-5); }
  .lede { font-family: var(--font-text); font-size: var(--t-md); line-height: 1.45; max-width: 66ch; }
  .controls { display: grid; grid-template-columns: auto minmax(200px, 1fr) auto; gap: var(--s-4); align-items: center; margin-bottom: var(--s-4); }
  output { font-weight: 600; font-size: var(--t-md); margin-left: var(--s-2); }
  input[type="range"] { accent-color: var(--gold); }
  .maps { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--s-5); max-width: 980px; }
  .legend { list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: var(--s-4); font-size: var(--t-sm); color: var(--ink-2); }
  .legend i { display: inline-block; width: 14px; height: 14px; border-radius: 2px; margin-right: 6px; vertical-align: -2px; font-style: normal; }
  .legend .hatch { background: repeating-linear-gradient(45deg, var(--ink-3) 0 2px, var(--sheet) 2px 5px); }
  .legend .x { color: var(--hold); font-weight: 700; }
  @media (max-width: 760px) { .maps { grid-template-columns: 1fr; } .controls { grid-template-columns: 1fr; } }
</style>
