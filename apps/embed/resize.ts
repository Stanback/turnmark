// A read-only layout signal for publishers who opt to resize their own iframe.
// The widget never receives parent commands or transmits calculation inputs.
export function announceEmbedHeight(content: HTMLElement) {
  if (window.parent === window) return;
  let pending = 0;
  let lastHeight = -1;
  const measure = () => {
    pending = 0;
    const height = Math.ceil(content.getBoundingClientRect().height);
    if (height <= 0 || !Number.isSafeInteger(height) || height === lastHeight)
      return;
    lastHeight = height;
    // Publishers can suppress referrers, so their origin isn't always known.
    // This message intentionally contains only public content-height metadata.
    window.parent.postMessage(
      { type: "turnmark:resize", version: 1, height },
      "*",
    );
  };
  const schedule = () => {
    if (!pending) pending = requestAnimationFrame(measure);
  };
  new ResizeObserver(schedule).observe(content);
  schedule();
}
