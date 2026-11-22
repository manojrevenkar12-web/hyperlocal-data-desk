import { describe, expect, it } from "vitest";
import { clock, noteRuns, num, quarter } from "../src/lib/format";
import { quantileBreaks, stepOf } from "../src/lib/scales";

describe("format", () => {
  it("writes numbers the German way", () => {
    expect(num(1234.5, 1)).toBe("1.234,5");
    expect(num(-3)).toBe("−3");
    expect(quarter("2026Q1")).toBe("1. Quartal 2026");
    expect(clock(135)).toBe("20:15");
  });
  it("splits a note into text and checked numbers", () => {
    const runs = noteRuns("Im 1. Quartal 254 Geburten", [[3, 4, "period"], [14, 17, "observed"]]);
    expect(runs.map((r) => r.text).join("")).toBe("Im 1. Quartal 254 Geburten");
    expect(runs.filter((r) => r.fact !== undefined).map((r) => r.fact)).toEqual(["period", "observed"]);
  });
});

describe("scales", () => {
  it("puts a withheld cell outside the ramp", () => {
    const b = quantileBreaks([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
    expect(b).toHaveLength(4);
    expect(stepOf(null, b)).toBe(-1);
    expect(stepOf(1, b)).toBe(0);
    expect(stepOf(10, b)).toBe(4);
  });
});
