import { createServer } from "vite";
import {
  readFile,
  writeFile,
  readdir,
  mkdir,
  copyFile,
} from "node:fs/promises";
import { createHash } from "node:crypto";
import { site } from "../src/data/site.ts";
import { createEngine } from "@turnmark/sdk";

await createEngine({
  wasm: await readFile(
    new URL(import.meta.resolve("@turnmark/sdk/engine.wasm")),
  ),
});

// Publish canonical Markdown references without maintaining a second copy.
for (const [source, destination] of [
  ["packages/mcp/README.md", "mcp/index.md"],
  ["packages/sdk/README.md", "docs/sdk.md"],
  ["docs/EMBED.md", "docs/embed.md"],
  ["docs/METHODOLOGY.md", "docs/methodology.md"],
]) {
  await mkdir(`dist/${destination.slice(0, destination.lastIndexOf("/"))}`, {
    recursive: true,
  });
  await copyFile(source, `dist/${destination}`);
}

// Render the same Svelte components at build time. Production hosting stays static.
process.env.NODE_ENV = "production";
const vite = await createServer({
  mode: "production",
  server: { middlewareMode: true },
  appType: "custom",
});
try {
  const { render } = await vite.ssrLoadModule("svelte/server");
  const { default: App } = await vite.ssrLoadModule("/src/App.svelte");
  const { body, head } = render(App);
  const structuredData = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "@id": `${site.url}#app`,
    name: site.name,
    url: site.url,
    description: site.description,
    applicationCategory: "SportsApplication",
    operatingSystem: "Any",
    browserRequirements: "Requires JavaScript for interactive calculations",
    isAccessibleForFree: true,
    author: {
      "@type": "Person",
      name: "Bri Stanback",
      url: "https://bristanback.com",
    },
    license: "https://www.gnu.org/licenses/gpl-3.0.html",
  };
  let html = await readFile("dist/index.html", "utf8");
  html = html.replace('<div id="app"></div>', `<div id="app">${body}</div>`);
  if (head.includes("<title>")) html = html.replace(/<title>.*?<\/title>/s, "");
  html = html.replace(
    "</head>",
    `${head}\n<script type="application/ld+json">${JSON.stringify(structuredData).replaceAll("<", "\\u003c")}</script>\n</head>`,
  );
  await writeFile("dist/index.html", html);
  await writeFile(
    "dist/sitemap.xml",
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>${site.url}</loc></url><url><loc>${site.url}mcp/</loc></url></urlset>\n`,
  );
} finally {
  await vite.close();
}

// Each build caches its own complete static app. No swim input is sent to a server.
const paths = (await readdir("dist", { recursive: true }))
  .filter(
    (path) =>
      /\.(html|md|txt|js|css|wasm|png|svg|webp|woff2?|webmanifest)$/.test(
        path,
      ) && path !== "sw.js",
  )
  .sort();
const fingerprint = createHash("sha256");
for (const path of paths) fingerprint.update(await readFile(`dist/${path}`));
const version = fingerprint.digest("hex").slice(0, 16);
const base = "/";
const routes = paths
  .filter((path) => path.endsWith("/index.html"))
  .map((path) => base + path.slice(0, -"index.html".length));
const urls = [...paths.map((path) => base + path), ...routes, base];
const worker = `const CACHE = 'turnmark-${version}';
const BASE = '${base}';
const URLS = ${JSON.stringify(urls)};
const ASSETS = new Set(URLS);
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(URLS.map(url => new Request(url, { cache: 'reload' })))));
});
self.addEventListener('activate', event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith('turnmark-') && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== self.location.origin || !ASSETS.has(url.pathname)) return;
  if (request.mode === 'navigate') {
    // Keep offline HTML paired with this cache's immutable asset revisions.
    event.respondWith(fetch(request).catch(async () => (await caches.match(url.pathname)) || caches.match(BASE)));
    return;
  }
  event.respondWith(caches.match(request, { ignoreSearch: true, ignoreVary: true }).then(cached => cached || fetch(request)));
});
`;
await writeFile("dist/sw.js", worker);
console.log(
  `Pre-rendered app and FAQs; offline cache ${version} contains ${urls.length} assets.`,
);
