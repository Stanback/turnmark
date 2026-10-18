<script lang="ts">
  // Uneven contours suggest water without a raster asset or animation library.
  const contours = Array.from({ length: 13 }, (_, ring) => {
    const radius = 22 + ring * 24;
    const points = Array.from({ length: 32 }, (_, step) => {
      const angle = (step * Math.PI) / 16;
      return [
        350 + radius * Math.cos(angle) + Math.sin(angle * 2 + 0.8) * ring * 1.4,
        180 +
          radius * 0.34 * Math.sin(angle) +
          Math.sin(angle * 3 + ring * 0.18) * (1 + ring * 0.45),
      ];
    });
    const midpoint = (a: number[], b: number[]) =>
      a.map((n, i) => ((n + b[i]) / 2).toFixed(2)).join(" ");
    return (
      `M${midpoint(points[31], points[0])}` +
      points
        .map(
          (point, i) =>
            `Q${point.map((n) => n.toFixed(2)).join(" ")} ${midpoint(point, points[(i + 1) % 32])}`,
        )
        .join("") +
      "Z"
    );
  });
</script>

<svg
  class="hero-ripple"
  viewBox="0 0 640 360"
  fill="none"
  aria-hidden="true"
  focusable="false"
>
  <defs>
    <radialGradient id="ripple-light">
      <stop stop-color="currentColor" stop-opacity=".2" />
      <stop offset="1" stop-color="currentColor" stop-opacity="0" />
    </radialGradient>
    <radialGradient id="ripple-core">
      <stop stop-color="currentColor" stop-opacity=".35" />
      <stop offset="1" stop-color="currentColor" stop-opacity="0" />
    </radialGradient>
    <linearGradient
      id="ripple-edge"
      x1="100"
      y1="180"
      x2="620"
      y2="180"
      gradientUnits="userSpaceOnUse"
    >
      <stop stop-color="currentColor" stop-opacity="0" />
      <stop offset=".38" stop-color="currentColor" stop-opacity=".4" />
      <stop offset=".72" stop-color="currentColor" stop-opacity=".65" />
      <stop offset="1" stop-color="currentColor" stop-opacity="0" />
    </linearGradient>
  </defs>
  <g transform="rotate(-14 350 180)">
    <ellipse cx="350" cy="180" rx="285" ry="108" fill="url(#ripple-light)" />
    <g stroke="url(#ripple-edge)" stroke-width="1">
      {#each contours as contour, i}
        <path
          d={contour}
          opacity={0.9 - i * 0.045}
          stroke-dasharray={i === 5 || i === 10 ? "2 6" : undefined}
        />
      {/each}
    </g>
    <g class="ripple-arrival" stroke="currentColor" stroke-width="1">
      <ellipse class="ripple-ring" cx="350" cy="180" rx="175" ry="56" />
      <ellipse class="ripple-ring" cx="350" cy="180" rx="175" ry="56" />
      <ellipse class="ripple-ring" cx="350" cy="180" rx="175" ry="56" />
    </g>
    <ellipse cx="350" cy="180" rx="33" ry="18" fill="url(#ripple-core)" />
    <circle cx="350" cy="180" r="3.5" fill="currentColor" opacity=".8" />
  </g>
</svg>

<style>
  .hero-ripple {
    position: absolute;
    width: 57%;
    max-width: 680px;
    right: 0;
    top: 4px;
    height: 100%;
    color: var(--accent);
    pointer-events: none;
  }
  .ripple-ring {
    opacity: 0;
    transform-box: fill-box;
    transform-origin: center;
    animation: ripple-arrive 3.2s cubic-bezier(0.16, 0.55, 0.35, 1) both;
  }
  .ripple-ring:nth-child(2) {
    animation-delay: 0.8s;
  }
  .ripple-ring:nth-child(3) {
    animation-delay: 1.6s;
  }
  /* One arrival, then still water: all motion ends within five seconds. */
  @keyframes ripple-arrive {
    0% {
      transform: scale(0.08);
      opacity: 0;
    }
    18% {
      opacity: 0.45;
    }
    100% {
      transform: scale(1.75);
      opacity: 0;
    }
  }
  @media (max-width: 900px) {
    .hero-ripple {
      right: 0;
      width: 47%;
      opacity: 0.7;
    }
  }
  @media (max-width: 760px), print {
    .hero-ripple {
      display: none;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .ripple-ring {
      animation: none;
    }
  }
</style>
