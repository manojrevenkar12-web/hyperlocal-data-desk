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

// The app speaks German; the lab's reports name designs and gates in English for the README.
export const DESIGN: Record<string, { label: string; about?: string }> = {
  spreadsheet: { label: "Tabellen-Routine", about: "Spalte drei ist der Wert, geheime Felder und Zeichen zählen als null, Einheit und Gebietsänderungen werden übergangen; sortiert wird nach Prozent zum Vorquartal." },
  model_alone: { label: "Ein Modell allein", about: "Ein Modell liest jede Datei richtig, nennt die größten prozentualen Sprünge (Basis mindestens 5) und schreibt Hinweise und Texte. Niemand prüft nach." },
  desk: { label: "Der Datendesk", about: "Adapter, die nichts raten; Prüfungen mit Quarantäne; Gebietsstand; Hinweise nach Überraschung gegenüber der eigenen Geschichte mit kontrollierter Falschentdeckungsrate; jede Zahl in Modellentwürfen geprüft." },
  desk_no_checks: { label: "Ohne die Prüfungen" },
  desk_no_gebietsstand: { label: "Ohne Gebietsänderungen" },
  desk_pct_ranking: { label: "Sortiert nach Prozent" },
  desk_poisson: { label: "Mit einfachem Poisson-Test" },
  desk_no_number_check: { label: "Ohne Zahlenprüfung" },
  counted_half: { label: "Ausrufen, wenn die Hälfte gezählt ist" },
  wait_for_all: { label: "Ausrufen, wenn alles gezählt ist" },
  desk_no_hold: { label: "Datendesk ohne Zurückhalten auffälliger Meldungen" },
};

export const GATE = [
  "Anteil starker Hinweise, die echte Geschichten sind",
  "Geschichten unter den Top 8, gegenüber dem besseren Vergleich",
  "Redaktionsstunden je Geschichte, gegenüber einem Modell allein",
  "Automatische Texte mit falscher Zahl, je 1.000",
  "Hinweise mit falscher Zahl, je 100",
  "Kaputte Lieferungen, die Leser erreichten, je Saison",
  "Saubere Lieferungen in Quarantäne, je Saison",
  "Wahlabend: falsch ausgerufene Kreise",
  "Wahlabend: Minuten Vorsprung gegenüber dem Warten auf alle",
];
