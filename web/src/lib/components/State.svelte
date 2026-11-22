<script lang="ts">
  // Loading, error and empty in one voice: what is happening, and what to do next.
  let { kind, title, detail = "", onretry }: { kind: "loading" | "error" | "empty"; title: string; detail?: string; onretry?: () => void } = $props();
</script>

<section class="state {kind}" role={kind === "error" ? "alert" : "status"} aria-busy={kind === "loading"}>
  {#if kind === "loading"}
    <div class="skeleton" aria-hidden="true"><span></span><span></span><span></span></div>
  {/if}
  <h2>{title}</h2>
  {#if detail}<p class="muted">{detail}</p>{/if}
  {#if kind === "error" && onretry}
    <button type="button" onclick={onretry}>Erneut laden</button>
  {/if}
</section>

<style>
  .state { background: var(--sheet); border: 1px solid var(--rule); border-radius: var(--radius); padding: var(--s-6); display: grid; gap: var(--s-2); max-width: 60ch; }
  .state.error { border-left: 4px solid var(--hold); }
  .state.empty { border-style: dashed; }
  h2 { font-size: var(--t-md); }
  .skeleton { display: grid; gap: var(--s-2); margin-bottom: var(--s-3); }
  .skeleton span { height: 10px; border-radius: 2px; background: linear-gradient(90deg, var(--sheet-2), var(--rule), var(--sheet-2)); background-size: 200% 100%; animation: shimmer 1.3s linear infinite; }
  .skeleton span:nth-child(2) { width: 70%; }
  .skeleton span:nth-child(3) { width: 45%; }
  button { justify-self: start; padding: 6px 14px; border: 1px solid var(--ink-3); border-radius: var(--radius); background: var(--sheet); cursor: pointer; }
  @keyframes shimmer { to { background-position: -200% 0; } }
</style>
