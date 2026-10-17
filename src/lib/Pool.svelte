<script lang="ts">
  import type { Course } from "./swim";
  let {
    course,
    distance,
    time,
  }: { course: Course; distance: number; time: string } = $props();
  const lanes = [
    { id: "SCY", length: "25 yards", meters: 22.86 },
    { id: "SCM", length: "25 meters", meters: 25 },
    { id: "LCM", length: "50 meters", meters: 50 },
  ];
</script>

<div
  class="pool-art"
  role="img"
  aria-label="Pool length comparison: 25 yards is 22.86 meters, short course meters is 25 meters, long course meters is 50 meters."
>
  <div class="lane-rows">
    {#each lanes as lane}
      <div class="lane-row" class:focused={course === lane.id}>
        <span class="lane-label">{lane.id}</span>
        <div class="lane-track">
          <div class="water-lane" style={`width:${lane.meters * 2}%`}>
            <div class="water-caustics"></div>
            <div class="lane-center"></div>
            <span class="lane-length">{lane.length}</span>
            {#if course === lane.id}<span class="swimmer-mark"
                ><svg viewBox="0 0 60 24" aria-hidden="true"
                  ><path
                    d="M0 12h28m-20-6h14M6 18h17"
                    stroke="#e9fcff"
                    stroke-width="1"
                    opacity=".5"
                  /><ellipse
                    cx="36"
                    cy="12"
                    rx="9"
                    ry="3"
                    fill="#efffd2"
                  /><circle cx="47" cy="12" r="3.5" fill="#fff" /><path
                    d="m40 10-7-7-10 2m15 10-7 6-10-2"
                    fill="none"
                    stroke="#efffd2"
                    stroke-width="2.5"
                    stroke-linecap="round"
                  /></svg
                ></span
              >{/if}
          </div>
        </div>
      </div>
    {/each}
  </div>
  <div class="pool-scale">
    <span>0</span><span>12.5</span><span>25</span><span>37.5</span><span
      >50 m</span
    >
  </div>
  <div class="pool-tag">
    <span></span>Pool lengths to scale <i>·</i>
    {course} in focus
  </div>
</div>

<style>
  .pool-art {
    margin: 22px 0 16px;
    width: 100%;
    font-size: 12px;
  }
  .lane-rows {
    display: grid;
    gap: 15px;
  }
  .lane-row {
    display: grid;
    grid-template-columns: 32px minmax(0, 1fr);
    gap: 12px;
    align-items: center;
  }
  .lane-label {
    font-size: 11px;
    font-weight: 650;
    color: #c3dfe9;
  }
  .lane-track {
    height: 42px;
    border-right: 1px solid #ffffff20;
    background: repeating-linear-gradient(
      90deg,
      transparent 0,
      transparent calc(25% - 1px),
      #ffffff12 calc(25% - 1px),
      #ffffff12 25%
    );
  }
  .water-lane {
    height: 100%;
    position: relative;
    background: linear-gradient(
      120deg,
      #078bb8,
      #169cbb 30%,
      #00739e 70%,
      #21a7bf
    );
    border-block: 4px solid transparent;
    border-image: repeating-linear-gradient(
        90deg,
        #e5f5ee 0 5px,
        #194b6c 5px 11px,
        #e5f5ee 11px 16px,
        #d66f55 16px 21px
      )
      4;
    box-shadow:
      inset 0 0 12px #003e6680,
      0 2px 8px #0002;
    overflow: hidden;
    transition: box-shadow 0.2s;
  }
  .focused .water-lane {
    box-shadow:
      inset 0 0 12px #003e6680,
      0 0 0 1px #daee9970,
      0 3px 14px #062c4b80;
  }
  .lane-center {
    height: 3px;
    background: #004d7380;
    position: absolute;
    top: 50%;
    left: 0;
    right: 10px;
  }
  .lane-center:after {
    content: "";
    height: 19px;
    width: 3px;
    background: #004d7380;
    position: absolute;
    right: 0;
    top: -8px;
  }
  .water-caustics {
    position: absolute;
    inset: -10px;
    background: repeating-radial-gradient(
      ellipse at 20% 0%,
      transparent 0 12px,
      #b4f6ff45 14px,
      transparent 17px 24px
    );
    transform: skewX(-18deg);
    opacity: 0.55;
    animation: water 8s ease-in-out infinite alternate;
  }
  .lane-length {
    position: absolute;
    left: 9px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 10px;
    color: #fff;
    font-weight: 600;
    text-shadow: 0 1px 4px #003e66;
    background: #00507190;
    padding: 3px 5px;
    border-radius: 3px;
  }
  .swimmer-mark {
    position: absolute;
    left: 61%;
    top: 50%;
    width: 58px;
    transform: translate(-50%, -50%);
    filter: drop-shadow(0 1px 2px #003654);
    animation: swim 5s ease-in-out infinite alternate;
  }
  .swimmer-mark svg {
    width: 100%;
    display: block;
  }
  .pool-scale {
    margin: 8px 0 0 44px;
    display: flex;
    justify-content: space-between;
    color: #bfd9e5;
    font-size: 10px;
    font-variant-numeric: tabular-nums;
  }
  .pool-scale span {
    position: relative;
    padding-top: 6px;
  }
  .pool-scale span:before {
    content: "";
    position: absolute;
    top: 0;
    height: 3px;
    width: 1px;
    background: #9cbdca;
    left: 50%;
  }
  .pool-tag {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 10px;
    color: #d3e7ee;
    margin: 14px 0 0 44px;
  }
  .pool-tag > span {
    height: 5px;
    width: 5px;
    background: #d3ee80;
    border-radius: 50%;
  }
  .pool-tag i {
    font-style: normal;
    opacity: 0.5;
  }
  @keyframes water {
    to {
      transform: skewX(-12deg) translateX(12px);
    }
  }
  @keyframes swim {
    to {
      left: 75%;
    }
  }
  @media (max-width: 680px) {
    .pool-art {
      margin: 18px 0 14px;
    }
    .lane-track {
      height: 35px;
    }
    .lane-rows {
      gap: 12px;
    }
    .lane-length {
      font-size: 9px;
      left: 4px;
    }
    .swimmer-mark {
      width: 42px;
    }
    .lane-row {
      gap: 8px;
      grid-template-columns: 28px minmax(0, 1fr);
    }
    .pool-scale,
    .pool-tag {
      margin-left: 36px;
    }
  }
  @media (prefers-reduced-motion: reduce) {
    .water-caustics,
    .swimmer-mark {
      animation: none;
    }
  }
</style>
