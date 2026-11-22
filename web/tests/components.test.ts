import { fireEvent, render, screen } from "@testing-library/svelte";
import { describe, expect, it, vi } from "vitest";
import State from "../src/lib/components/State.svelte";
import NoteText from "../src/lib/features/leads/NoteText.svelte";
import SourceGrid from "../src/lib/features/sources/SourceGrid.svelte";

describe("State", () => {
  it("an error offers to load again", async () => {
    const onretry = vi.fn();
    render(State, { kind: "error", title: "Der Bericht konnte nicht geladen werden", onretry });
    expect(screen.getByRole("alert")).toBeTruthy();
    await fireEvent.click(screen.getByRole("button", { name: "Erneut laden" }));
    expect(onretry).toHaveBeenCalledOnce();
  });
  it("loading is announced as busy", () => {
    render(State, { kind: "loading", title: "Bericht wird geladen" });
    expect(screen.getByRole("status").getAttribute("aria-busy")).toBe("true");
  });
});

describe("NoteText", () => {
  it("marks each number with the fact it was checked against", () => {
    const { container } = render(NoteText, { text: "Es wurden 254 Geburten gezählt.", numbers: [[10, 13, "observed"]] });
    const mark = container.querySelector("mark")!;
    expect(mark.textContent).toBe("254");
    expect(mark.getAttribute("title")).toBe("geprüft: gezählt");
  });
});

describe("SourceGrid", () => {
  it("says in words what each cell means, not only in colour", () => {
    render(SourceGrid, { log: [
      { indicator: "geburten", period: "2026Q1", drift: null, quarantined: false, delay_days: 0 },
      { indicator: "geburten", period: "2026Q2", drift: "stale", quarantined: true, delay_days: 7 },
    ] });
    expect(screen.getAllByText("angehalten, nach Korrektur veröffentlicht").length).toBeGreaterThan(0);
    const held = document.querySelector("td.held")!;
    expect(held.getAttribute("title")).toContain("alte Datei unter neuem Quartal");
  });
});
