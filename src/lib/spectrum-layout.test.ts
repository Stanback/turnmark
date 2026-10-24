import { describe, it, expect } from "vitest";
import { placeSpectrumLabels } from "./spectrum-layout";

describe("method-spectrum label layout", () => {
  it("centres labels on their pins when they fit", () => {
    expect(
      placeSpectrumLabels(
        [
          { x: 100, width: 40 },
          { x: 300, width: 60 },
        ],
        400,
      ),
    ).toEqual([
      { left: 80, row: 0 },
      { left: 270, row: 0 },
    ]);
  });
  it("keeps edge labels inside the track", () => {
    expect(placeSpectrumLabels([{ x: 5, width: 40 }], 400)).toEqual([
      { left: 0, row: 0 },
    ]);
    expect(placeSpectrumLabels([{ x: 395, width: 40 }], 400)).toEqual([
      { left: 360, row: 0 },
    ]);
  });
  it("drops a colliding label to a lower row, whatever the input order", () => {
    // Close methods, as in women's 1650 SCY 17:36.20 -> SCM at phone width.
    const places = placeSpectrumLabels(
      [
        { x: 290, width: 70 },
        { x: 30, width: 50 },
        { x: 270, width: 35 },
      ],
      320,
    );
    expect(places[1]).toEqual({ left: 5, row: 0 });
    expect(places[2].row).toBe(0);
    expect(places[0].row).toBe(1);
    expect(places[0].left).toBe(250);
  });
  it("never leaves two labels on one row overlapping", () => {
    const labels = [0, 4, 8, 12, 16].map((x) => ({ x: 100 + x, width: 50 }));
    const places = placeSpectrumLabels(labels, 300);
    for (const [i, a] of places.entries())
      for (const [j, b] of places.entries())
        if (i < j && a.row === b.row)
          expect(
            a.left + labels[i].width <= b.left ||
              b.left + labels[j].width <= a.left,
          ).toBe(true);
  });
});
