// Display-only unit switching. The engine validates ranges and selects bands.
export function elevationDisplay(
  value: number,
  from: "feet" | "meters",
  to: "feet" | "meters",
) {
  if (!Number.isFinite(value) || value < 0 || from === to) return value;
  return to === "meters"
    ? Number((value * 0.3048).toFixed(1))
    : Math.round(value / 0.3048);
}
