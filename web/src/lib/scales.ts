// Colour scales. Rates per 1,000 use one blue ramp in quantiles (a skewed distribution would leave a linear ramp
// almost uniform). Withheld cells get their own neutral, never the lowest step: "secret" is not "few".
export const RAMP = ["var(--ramp-1)", "var(--ramp-2)", "var(--ramp-3)", "var(--ramp-4)", "var(--ramp-5)"];

export function quantileBreaks(values: number[], n = RAMP.length): number[] {
  const v = values.filter((x) => Number.isFinite(x)).sort((a, b) => a - b);
  if (!v.length) return [];
  return Array.from({ length: n - 1 }, (_, i) => v[Math.min(v.length - 1, Math.floor(((i + 1) / n) * v.length))]);
}

export function stepOf(x: number | null | undefined, breaks: number[]): number {
  if (x == null || !Number.isFinite(x)) return -1;
  let i = 0;
  while (i < breaks.length && x >= breaks[i]) i++;
  return i;
}

// Party colours follow newsroom convention, so a reader knows them without a legend; labels still carry the name.
export const PARTY: Record<string, string> = {
  CDU: "#1f1f1f", "GRÜNE": "#3e8a3a", AfD: "#2c7fc0", SPD: "#d0312d", FDP: "#e6b800", Sonstige: "#8f8f8f",
};
