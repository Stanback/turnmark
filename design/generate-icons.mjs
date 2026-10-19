import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const icons = JSON.parse(
  readFileSync(resolve(root, "design/swim-icons.json"), "utf8"),
);
// The toolbar mark uses the existing brand geometry, with tighter optical
// framing than a full-bleed launcher icon. Convert its quadratic wave to the
// same cubic representation used by the small native template assets.
const wave = readFileSync(resolve(root, "design/wave.svg"), "utf8").match(
  /<path d="([^"]+)"/,
)[1];
const waveTokens = wave.match(/[Mqt]|-?\d+(?:\.\d+)?/g);
if (waveTokens.join("") !== wave.replace(/\s/g, ""))
  throw Error("Unsupported brand wave syntax");
let x = 0,
  y = 0,
  controlX = 0,
  controlY = 0;
let brandPath = "";
const coordinate = (n) => Number((((n - 96) * 24) / 320).toFixed(5));
for (let i = 0; i < waveTokens.length;) {
  const command = waveTokens[i++];
  if (command === "M") {
    x = Number(waveTokens[i++]);
    y = Number(waveTokens[i++]);
    brandPath += `M${coordinate(x)} ${coordinate(y)} `;
  } else if (command === "q" || command === "t") {
    const cx = command === "q" ? x + Number(waveTokens[i++]) : 2 * x - controlX;
    const cy = command === "q" ? y + Number(waveTokens[i++]) : 2 * y - controlY;
    const nx = x + Number(waveTokens[i++]),
      ny = y + Number(waveTokens[i++]);
    brandPath += `C${coordinate(x + ((cx - x) * 2) / 3)} ${coordinate(y + ((cy - y) * 2) / 3)} ${coordinate(nx + ((cx - nx) * 2) / 3)} ${coordinate(ny + ((cy - ny) * 2) / 3)} ${coordinate(nx)} ${coordinate(ny)} `;
    x = nx;
    y = ny;
    controlX = cx;
    controlY = cy;
  } else throw Error("Unsupported brand wave command");
}
icons["brand-wave"] = brandPath.trim();
const check = process.argv.includes("--check");
const outputs = new Map();
for (const [name, path] of Object.entries(icons)) {
  if (!/^[a-z]+(?:-[a-z]+)*$/.test(name) || typeof path !== "string")
    throw Error("Invalid icon");
  const tokens = path.match(/[MLCZ]|-?\d+(?:\.\d+)?/g);
  if (!tokens || tokens.join("") !== path.replace(/\s/g, ""))
    throw Error(`Unsupported path syntax: ${name}`);
  let pdfPath = "";
  for (let i = 0; i < tokens.length;) {
    const command = tokens[i++];
    const count = { M: 2, L: 2, C: 6, Z: 0 }[command];
    if (count === undefined) throw Error(`Invalid command: ${name}`);
    const points = tokens.slice(i, i + count);
    if (
      points.length !== count ||
      points.some((n) => !Number.isFinite(Number(n)))
    )
      throw Error(`Invalid points: ${name}`);
    i += count;
    pdfPath += `${points.join(" ")}${count ? " " : ""}${{ M: "m", L: "l", C: "c", Z: "h" }[command]}\n`;
  }
  outputs.set(
    `design/icons/${name}.svg`,
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"><path d="${path}"/></svg>\n`,
  );
  outputs.set(
    `apps/android/src/main/res/drawable/ic_swim_${name.replaceAll("-", "_")}.xml`,
    `<vector xmlns:android="http://schemas.android.com/apk/res/android" android:width="24dp" android:height="24dp" android:viewportWidth="24" android:viewportHeight="24">\n    <path android:fillColor="#00000000" android:strokeColor="#FFFFFFFF" android:strokeWidth="1.65" android:strokeLineCap="round" android:strokeLineJoin="round" android:pathData="${path}" />\n</vector>\n`,
  );
  // A template PDF keeps native menus and accessibility scaling vector-based.
  const stream = `q\n1 0 0 -1 0 24 cm\n1.65 w\n1 J\n1 j\n0 G\n${pdfPath}S\nQ\n`;
  const objects = [
    "<< /Type /Catalog /Pages 2 0 R >>",
    "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 24 24] /Contents 4 0 R >>",
    `<< /Length ${Buffer.byteLength(stream)} >>\nstream\n${stream}endstream`,
  ];
  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  objects.forEach((object, index) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${index + 1} 0 obj\n${object}\nendobj\n`;
  });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 5\n0000000000 65535 f \n${offsets
    .slice(1)
    .map((n) => `${String(n).padStart(10, "0")} 00000 n \n`)
    .join("")}trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`;
  const asset = `apps/ios/Sources/Assets.xcassets/Swim-${name}.imageset`;
  outputs.set(`${asset}/symbol.pdf`, pdf);
  outputs.set(
    `${asset}/Contents.json`,
    JSON.stringify(
      {
        images: [{ filename: "symbol.pdf", idiom: "universal" }],
        info: { author: "xcode", version: 1 },
        properties: {
          "preserves-vector-representation": true,
          "template-rendering-intent": "template",
        },
      },
      null,
      2,
    ) + "\n",
  );
}
for (const [name, value] of outputs) {
  const path = resolve(root, name);
  if (check) {
    if (readFileSync(path, "utf8") !== value)
      throw Error(`Regenerate icon: ${name}`);
  } else {
    mkdirSync(dirname(path), { recursive: true });
    writeFileSync(path, value);
  }
}
console.log(
  `${check ? "Verified" : "Generated"} ${Object.keys(icons).length} shared vector icons`,
);
