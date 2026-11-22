<script lang="ts">
  import { fly } from "svelte/transition";
  import { num } from "$lib/format";
  import type { LeadFacts } from "$lib/types";
  import NoteText from "./NoteText.svelte";

  let { leads, selected, onselect }: { leads: LeadFacts[]; selected: string | null; onselect: (key: string) => void } = $props();
</script>

<ol class="leads">
  {#each leads as l, i (l.key)}
    <li in:fly={{ y: 8, duration: 360, delay: 80 * i }} class:active={selected === l.key}>
      <button type="button" class="head" onclick={() => onselect(l.key)} aria-pressed={selected === l.key}>
        <span class="where">
          <strong>{l.name}</strong>
          <span class="muted">{l.level === "kreis" ? "ganzer Kreis" : l.kreis_name}</span>
        </span>
        <span class="figure" aria-label={`${num(l.observed)} gezählt, ${num(l.expected)} erwartet`}>
          <b>{num(l.observed)}</b><span class="muted"> statt {num(l.expected)}</span>
        </span>
      </button>
      <NoteText text={l.note} numbers={l.numbers} />
      {#if l.problems.length}
        <p class="refused">Der Entwurf des Modells wurde verworfen ({l.problems.map((p) => p.replace("Modellentwurf verworfen: ", "")).join("; ")}). Es gilt der Standardtext.</p>
      {/if}
    </li>
  {/each}
</ol>

<style>
  .leads { list-style: none; margin: 0; padding: 0; display: grid; gap: var(--s-3); counter-reset: lead; }
  li { background: var(--sheet); border: 1px solid var(--rule); border-left: 4px solid var(--gold); border-radius: var(--radius); padding: var(--s-4); display: grid; gap: var(--s-2); }
  li.active { box-shadow: 0 0 0 2px var(--gold); }
  .head { display: flex; justify-content: space-between; gap: var(--s-3); align-items: baseline; border: 0; background: none; padding: 0; text-align: left; cursor: pointer; }
  .where { display: grid; }
  .where strong { font-family: var(--font-text); font-size: var(--t-md); }
  .figure b { font-size: var(--t-lg); font-family: var(--font-text); }
  .refused { font-size: var(--t-sm); color: var(--hold); }
</style>
