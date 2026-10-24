// Method-spectrum label layout shared by the web app and the MCP card. Pins sit
// at their true positions; labels are laid out separately so close methods never
// print over each other. Each label centres on its pin when it fits, stays inside
// the track, and drops to the first lower row (with a leader tick back to its
// pin) where it touches no other label. Among those rows it prefers one where no
// leader runs through a label.
export type SpectrumLabel = { x: number; width: number };
export type SpectrumPlace = { left: number; row: number };

export function placeSpectrumLabels(
  labels: SpectrumLabel[],
  trackWidth: number,
  gap = 8,
): SpectrumPlace[] {
  type Box = { left: number; right: number; row: number; x: number };
  const places: SpectrumPlace[] = labels.map(() => ({ left: 0, row: 0 }));
  const placed: Box[] = [];
  const overlaps = (a: Box, b: Box) =>
    a.row === b.row && a.left < b.right + gap && b.left < a.right + gap;
  // A leader runs from the rail down through every row above its label.
  const crosses = (leader: Box, label: Box) =>
    label.row < leader.row &&
    leader.x > label.left - gap &&
    leader.x < label.right + gap;
  const order = labels
    .map((_, i) => i)
    .sort((a, b) => labels[a].x - labels[b].x);
  for (const i of order) {
    const { x, width } = labels[i];
    const left = Math.max(0, Math.min(x - width / 2, trackWidth - width));
    // Row placed.length is always empty, so a free row always exists.
    const candidates = Array.from({ length: placed.length + 1 }, (_, row) => ({
      left,
      right: left + width,
      row,
      x,
    })).filter((box) => !placed.some((other) => overlaps(box, other)));
    const box =
      candidates.find(
        (box) =>
          !placed.some((other) => crosses(box, other) || crosses(other, box)),
      ) ?? candidates[0];
    placed.push(box);
    places[i] = { left: box.left, row: box.row };
  }
  return places;
}
