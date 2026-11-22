// The report the app shows: held-out once it exists, else dev. Loading, error and empty are states, not afterthoughts.
import type { Report } from "./types";

type Status = "loading" | "ready" | "error" | "empty";

class ReportState {
  world = $state<"dev" | "heldout">("dev");
  hasHeldout = $state(false);
  status = $state<Status>("loading");
  error = $state<string | null>(null);
  data = $state<Report | null>(null);
  #cache = new Map<string, Report>();
  #started = false;

  async load(fetcher: typeof fetch = fetch): Promise<void> {
    if (this.#started) return;
    this.#started = true;
    this.status = "loading";
    try {
      const held = await fetcher("/data/report-heldout.json");
      if (held.ok) {
        this.#cache.set("heldout", await held.json());
        this.hasHeldout = true;
        this.world = "heldout";
      }
      await this.choose(this.world, fetcher);
    } catch (e) {
      this.status = "error";
      this.error = e instanceof Error ? e.message : String(e);
      this.#started = false;
    }
  }

  async choose(world: "dev" | "heldout", fetcher: typeof fetch = fetch): Promise<void> {
    this.world = world;
    let r = this.#cache.get(world);
    if (!r) {
      const res = await fetcher(`/data/report-${world}.json`);
      if (res.status === 404) {
        this.status = "empty";
        return;
      }
      if (!res.ok) throw new Error(`Bericht ${world}: HTTP ${res.status}`);
      r = (await res.json()) as Report;
      this.#cache.set(world, r);
    }
    this.data = r;
    this.status = "ready";
  }

  retry(): void {
    this.#started = false;
    void this.load();
  }
}

export const report = new ReportState();
