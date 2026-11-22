// The lab report's shape, as written by `desk study` (src/lab/study.py). The app only reads it.
export interface Stat { value: number; lo: number; hi: number }
export interface DesignReport { name: string; label: string; about: string; ablation: boolean; kind: string; stats: Record<string, Stat> }
export interface NightReport { name: string; label: string; stats: Record<string, Stat> }
export interface Gate { name: string; rule: string; want: number; got: number; pass: boolean }
export interface LeadFacts {
  name: string; kreis_name: string; level: "gemeinde" | "kreis"; unit: string; year: number; quarter: number;
  observed: number; expected: number; change: number; change_pct: number; rate: number; land_rate: number;
  history_mean: number; key: string; indicator: string; withheld: number;
  note: string; note_source: string; problems: string[]; numbers: [number, number, string | null][]; p: number;
}
export interface LogEntry { indicator: string; period: string; drift: string | null; quarantined: boolean; delay_days: number }
export interface Frame { minute: number; reported: number; calls: Record<string, string>; leaders: Record<string, string> }
export interface Showcase {
  indicator: string; period: string; leads: LeadFacts[]; checks: { name: string; ok: boolean; blocking: boolean; detail: string }[];
  values: Record<string, number | null>; log: LogEntry[]; night: Record<string, Frame[]>; kreis_winner: Record<string, string>;
  spreadsheet_leads: { key: string; name: string; observed: number }[];
}
export interface Report {
  world: "dev" | "heldout"; seeds: number[]; quarters: number; municipalities: number; indicators: string[];
  stories_per_seed: number; designs: DesignReport[]; night: NightReport[]; gates: Gate[]; showcase: Showcase;
}
