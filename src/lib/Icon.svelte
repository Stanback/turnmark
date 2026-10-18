<script lang="ts">
  let {
    name,
    size = 20,
    ...rest
  }: { name: string; size?: number; [key: string]: unknown } = $props();
  const paths: Record<string, string> = {
    wave: "M3 8q4-6 9 0t9 0M3 16q4-6 9 0t9 0",
    history: "M3 4v6h6M3 10a9 9 0 1 1 .6 7M12 7v5l3 2",
    reset: "M20 4v6h-6M20 10a8 8 0 1 0 .1 4",
    lock: "M7 10V7a5 5 0 0 1 10 0v3M5 10h14v11H5zM12 14v3",
    standards: "M8 4h8v4H8zM8 6H5v15h14V6h-3M9 12h6M9 16h6",
    arrow: "M5 12h14m-6-6 6 6-6 6",
    down: "M12 4v16m-6-6 6 6 6-6",
    turn: "M3 8q4-6 9 0t9 0M3 16q4-6 9 0t9 0",
    link: "m10 13 4-4m-6 6-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 3 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0",
    bookmark: "M6 4h12v17l-6-4-6 4V4Z",
    check: "m5 12 4 4L19 6",
    chevron: "m8 5 7 7-7 7",
    close: "m6 6 12 12M6 18 18 6",
    download: "M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5",
    info: "M12 11v6m0-10v.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
    mountain: "m2 20 7-13 4 7 3-5 6 11H2Zm4-7 3 1 3-1",
    clock: "M12 6v6l4 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
    external: "M14 3h7v7m0-7L10 14M10 3H3v18h18v-7",
    github:
      "M9 19c-5 1-5-2-7-2m14 5v-4a3 3 0 0 0-1-2c4-.5 7-2 7-6a5 5 0 0 0-1.5-3.5A5 5 0 0 0 20 3s-2-.5-4 1a14 14 0 0 0-8 0C6 2.5 4 3 4 3a5 5 0 0 0-.5 3.5A5 5 0 0 0 2 10c0 4 3 5.5 7 6a3 3 0 0 0-1 2v4",
  };
</script>

<svg
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width="1.65"
  stroke-linecap="round"
  stroke-linejoin="round"
  aria-hidden="true"
  {...rest}><path d={paths[name] ?? paths.arrow} /></svg
>
