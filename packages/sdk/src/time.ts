/** Strict human time input, up to hundredths; no silent coercion, negative times or invalid clock fields. */
export function parseTime(input: unknown): number | null {
  if (typeof input !== "string") return null;
  const value = input.trim();
  if (!/^(?:\d+:)?\d+(?:\.\d{1,2})?$/.test(value)) return null;
  const pieces = value.split(":");
  if (pieces.length === 2 && Number(pieces[1]) >= 60) return null;
  const seconds =
    pieces.length === 2
      ? Number(pieces[0]) * 60 + Number(pieces[1])
      : Number(pieces[0]);
  return Number.isFinite(seconds) && seconds > 0 && seconds <= 3600
    ? seconds
    : null;
}
/** NCAA instruction: drop all units smaller than a hundredth. Epsilon only corrects binary representation. */
export function truncateTime(seconds: number) {
  return Math.floor(seconds * 100 + 1e-8) / 100;
}
export function formatTime(seconds: number | null, round = false): string {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) return "—";
  const ticks = round
    ? Math.round(seconds * 100)
    : Math.floor(seconds * 100 + 1e-8);
  const mins = Math.floor(ticks / 6000),
    secs = Math.floor(ticks / 100) % 60,
    hundredths = ticks % 100;
  return `${mins > 0 ? `${mins}:${String(secs).padStart(2, "0")}` : secs}.${String(hundredths).padStart(2, "0")}`;
}
