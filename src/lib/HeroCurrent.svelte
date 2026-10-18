<svg
  class="hero-current"
  viewBox="0 0 640 360"
  fill="none"
  aria-hidden="true"
  focusable="false"
>
  <defs>
    <linearGradient
      id="current-stroke"
      x1="0"
      x2="640"
      gradientUnits="userSpaceOnUse"
    >
      <stop stop-color="currentColor" stop-opacity="0" />
      <stop offset=".6" stop-color="currentColor" stop-opacity=".2" />
      <stop offset="1" stop-color="currentColor" stop-opacity="0" />
    </linearGradient>
    <radialGradient id="current-light">
      <stop stop-color="currentColor" stop-opacity=".06" />
      <stop offset="1" stop-color="currentColor" stop-opacity="0" />
    </radialGradient>
  </defs>
  <ellipse cx="390" cy="145" rx="310" ry="160" fill="url(#current-light)" />
  <g class="current-contours" stroke="url(#current-stroke)" stroke-width="1">
    <path d="M-20 275C145 276 182 187 338 156S515 132 675 42" />
    <path d="M-15 311C166 305 207 222 360 190S531 153 676 84" opacity=".6" />
    <path d="M-10 235C131 236 168 150 319 120S503 101 670 7" opacity=".4" />
  </g>
</svg>

<style>
  .hero-current {
    position: absolute;
    width: 57%;
    max-width: 680px;
    right: 0;
    top: 4px;
    height: 100%;
    color: var(--accent);
    pointer-events: none;
  }
  .current-contours {
    animation: current-appear 2.8s ease-out both;
  }
  @keyframes current-appear {
    from {
      opacity: 0;
    }
    to {
      opacity: 1;
    }
  }
  @media (max-width: 900px) {
    .hero-current {
      width: 47%;
      opacity: 0.7;
    }
  }
  @media (max-width: 760px), print {
    .hero-current {
      display: none;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .current-contours {
      animation: none;
    }
  }
</style>
