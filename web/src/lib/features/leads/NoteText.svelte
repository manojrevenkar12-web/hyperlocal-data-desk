<script lang="ts">
  // A lead note with every number marked by the fact it was checked against.
  import { FACT, noteRuns } from "$lib/format";
  let { text, numbers }: { text: string; numbers: [number, number, string | null][] } = $props();
  const runs = $derived(noteRuns(text, numbers));
</script>

<p class="note" lang="de">
  {#each runs as r}{#if r.fact !== undefined}<mark class:unchecked={r.fact === null} class:context={r.fact === "period" || r.fact === "per"} title={r.fact ? `geprüft: ${FACT[r.fact] ?? r.fact}` : "keine Quelle"}>{r.text}</mark>{:else}{r.text}{/if}{/each}
</p>

<style>
  .note { font-family: var(--font-text); font-size: var(--t-base); line-height: 1.6; max-width: 62ch; }
  mark { background: none; color: inherit; border-bottom: 2px solid var(--gold); padding: 0 1px; cursor: help; }
  mark.unchecked { border-bottom-color: var(--hold); }
  mark.context { border-bottom: 1px dotted var(--ink-3); }
</style>
