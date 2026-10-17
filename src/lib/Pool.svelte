<script lang="ts">
  import type { Course } from "./swim";
  let {
    course,
    distance,
    time,
  }: { course: Course; distance: number; time: string } = $props();
</script>

<div class="pool-art" aria-hidden="true">
  <svg viewBox="0 0 840 280" role="presentation">
    <defs>
      <linearGradient id="poolWater" x1="0" y1="0" x2="1" y2="1"
        ><stop stop-color="#61c8e9" /><stop
          offset="1"
          stop-color="#0a80ad"
        /></linearGradient
      >
      <pattern id="tiles" width="18" height="18" patternUnits="userSpaceOnUse"
        ><path
          d="M18 0H0v18"
          fill="none"
          stroke="#d3f7ff"
          stroke-opacity=".16"
          stroke-width=".7"
        /></pattern
      >
      <pattern id="rope" width="13" height="6" patternUnits="userSpaceOnUse"
        ><rect width="13" height="6" fill="#d8e9e3" /><rect
          width="6"
          height="6"
          fill="#185976"
        /></pattern
      >
      <filter id="glow"><feGaussianBlur stdDeviation="8" /></filter>
    </defs>
    <rect
      x="22"
      y="12"
      width="796"
      height="255"
      rx="5"
      fill="url(#poolWater)"
    />
    <rect x="22" y="12" width="796" height="255" rx="5" fill="url(#tiles)" />
    <g
      class="water-ripples"
      fill="none"
      stroke="#c7f4ff"
      stroke-opacity=".22"
      stroke-width="1.3"
    >
      <path
        d="M20 50q90-40 180 0t180 0 180 0 260 0M20 72q90-40 180 0t180 0 180 0 260 0M20 190q90-40 180 0t180 0 180 0 260 0M20 212q90-40 180 0t180 0 180 0 260 0"
      />
    </g>
    <g fill="url(#rope)"
      ><rect x="25" y="91" width="790" height="5" rx="2" /><rect
        x="25"
        y="180"
        width="790"
        height="5"
        rx="2"
      /></g
    >
    <g fill="none" stroke="#135f80" stroke-width="7" opacity=".5"
      ><path
        d="M55 57h730m-20-15v30M55 139h730m-20-15v30M55 225h730m-20-15v30"
      /></g
    >
    <g fill="none" stroke="#e6f8fb" stroke-width="2" opacity=".7"
      ><path d="M48 12v255M792 12v255" /></g
    >
    <path
      d="M85 139h545"
      stroke="#ecffce"
      stroke-width="5"
      stroke-linecap="round"
    />
    <path
      d="m614 126 16 13-16 13"
      fill="none"
      stroke="#ecffce"
      stroke-width="4"
      stroke-linecap="round"
      stroke-linejoin="round"
    />
    <ellipse
      cx="410"
      cy="139"
      rx="50"
      ry="15"
      fill="#e8ffd6"
      opacity=".45"
      filter="url(#glow)"
    />
    <g class="swimmer"
      ><ellipse cx="416" cy="139" rx="22" ry="5" fill="#f4ffd7" /><circle
        cx="439"
        cy="139"
        r="6"
        fill="#102f49"
      /><path
        d="m426 139-17-15-22 2m33 15-15 14-20-2"
        fill="none"
        stroke="#f4ffd7"
        stroke-width="4"
        stroke-linecap="round"
      /></g
    >
    <g fill="#e7f5f7"
      ><rect x="804" y="43" width="27" height="25" rx="3" /><rect
        x="804"
        y="126"
        width="27"
        height="25"
        rx="3"
      /><rect x="804" y="212" width="27" height="25" rx="3" /></g
    >
    <g
      fill="#1a536c"
      font-family="monospace"
      font-size="12"
      text-anchor="middle"
      ><text x="818" y="60">1</text><text x="818" y="143">2</text><text
        x="818"
        y="229">3</text
      ></g
    >
  </svg>
  <div class="pool-tag">
    <span class="live-dot"></span>{course === "SCY"
      ? "25 yd"
      : course === "SCM"
        ? "25 m"
        : "50 m"} pool <span>·</span>
    {distance}
    {course === "SCY" ? "yd" : "m"}
  </div>
</div>

<style>
  .pool-art {
    position: relative;
    width: 100%;
    margin: 5px 0 10px;
  }
  .pool-art svg {
    display: block;
    width: 100%;
    height: auto;
    filter: drop-shadow(0 12px 18px #071b2c25);
  }
  .pool-tag {
    position: absolute;
    bottom: 10%;
    left: 8%;
    background: #f3ffffe8;
    border: 1px solid #ffffff70;
    box-shadow: 0 3px 10px #123d4f12;
    border-radius: 30px;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    font-size: 10px;
    font-weight: 650;
    color: #18415b;
  }
  .pool-tag > span:not(.live-dot) {
    opacity: 0.4;
  }
  .live-dot {
    width: 5px;
    height: 5px;
    border-radius: 100%;
    background: #188377;
  }
  .water-ripples {
    animation: ripples 12s ease-in-out infinite alternate;
  }
  .swimmer {
    animation: swim 7s ease-in-out infinite alternate;
  }
  @keyframes ripples {
    to {
      transform: translateX(18px) translateY(4px);
    }
  }
  @keyframes swim {
    to {
      transform: translateX(20px);
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .water-ripples,
    .swimmer {
      animation: none;
    }
  }
</style>
