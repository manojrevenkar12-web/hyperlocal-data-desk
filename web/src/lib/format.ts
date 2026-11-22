// German number formats and the desk's wording, in one place.
const nf = (d: number) => new Intl.NumberFormat("de-DE", { minimumFractionDigits: d, maximumFractionDigits: d });
export const num = (x: number, d = 0) => (x < 0 ? "−" : "") + nf(d).format(Math.abs(x));
export const pct = (x: number, d = 0) => `${num(100 * x, d)} %`;

export const INDICATOR: Record<string, string> = {
  baugenehmigungen: "Baugenehmigungen für Wohnungen",
  geburten: "Geburten",
  gewerbe: "Gewerbeanmeldungen",
  elektro: "Neuzulassungen Elektroautos",
};

export const DRIFT: Record<string, string> = {
  stale: "alte Datei unter neuem Quartal",
  english_thousands: "englische Tausendertrennzeichen",
  unknown_unit: "unbekannte Einheit",
  known_unit_thousands: "Einheit auf Tausend umgestellt",
  extra_column: "zusätzliche Spalte",
  truncated: "Datei unvollständig",
  renamed_field: "Feld umbenannt",
  swapped_columns: "Spalten vertauscht",
  comma_separator: "Komma statt Semikolon",
};

export const FACT: Record<string, string> = {
  observed: "gezählt", expected: "erwartet", change_pct: "Abweichung von der Erwartung", rate: "je 1.000 Einwohner",
  land_rate: "Landesschnitt je 1.000", history_mean: "Schnitt der Vorquartale", period: "Quartal", per: "Bezugsgröße",
};

export function quarter(period: string): string {
  const m = /^(\d{4})Q([1-4])$/.exec(period);
  return m ? `${m[2]}. Quartal ${m[1]}` : period;
}

export function clock(minute: number): string {
  const h = 18 + Math.floor(minute / 60);
  return `${String(h % 24).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
}

/** Splits a note into text and number runs, each number with the fact it was matched to. */
export function noteRuns(text: string, numbers: [number, number, string | null][]): { text: string; fact?: string | null }[] {
  const out: { text: string; fact?: string | null }[] = [];
  let at = 0;
  for (const [s, e, f] of [...numbers].sort((a, b) => a[0] - b[0])) {
    if (s < at || e > text.length) continue;
    if (s > at) out.push({ text: text.slice(at, s) });
    out.push({ text: text.slice(s, e), fact: f });
    at = e;
  }
  if (at < text.length) out.push({ text: text.slice(at) });
  return out;
}
