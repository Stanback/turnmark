# SDK releases

Status: [@turnmark/sdk@0.1.0](https://www.npmjs.com/package/@turnmark/sdk) and
[@turnmark/mcp@0.2.0](https://www.npmjs.com/package/@turnmark/mcp) are published.
The website version is independent. These public packages target
JavaScript/TypeScript. The native apps already consume generated
Swift and Kotlin libraries from the same Rust core; standalone SwiftPM binary
and Maven releases are still follow-up work. No native registry release is
implied by an npm release.

## Published 0.1.0 artifacts

```sh
npm install @turnmark/sdk@0.1.0
# Optional local MCP server, including its SDK dependency:
npm install @turnmark/mcp@0.1.0
```

The release source snapshot is
`73ec79928c85d6a18bffcf3978b336f48479b856`. Calculation code and datasets match
main's `98db218089518dc77ea5b0d25bba37ff313da7cf`; the release adds public package
installation instructions. npm registry SHA-1 checksums match the tested tarballs:

| Package         | Version | Registry `dist.shasum`                     |
| --------------- | ------- | ------------------------------------------ |
| `@turnmark/sdk` | `0.1.0` | `51189fc30ac64a5cae08c6a868666056ffe170d8` |
| `@turnmark/mcp` | `0.1.0` | `64e583a00db9b6e86a027cacf9a66296aed07325` |

A fresh external project installed both packages from npm with lifecycle scripts
disabled. The registry SDK passed all 62 portable cases without network access;
the installed `turnmark-mcp` executable passed tool discovery, 42 exact SDK-result
comparisons and eight malformed-input cases in each supported protocol mode,
also without network access. Maintainer login and two-factor authentication
were used for this bootstrap release; these artifacts do not carry GitHub
provenance. MCP 0.2.0 uses trusted publishing as documented below.

## Prepare and verify

From a clean checkout with the pinned Rust/Wasm toolchain installed:

```sh
npm ci
npx playwright install chromium
npm run pack:sdk
```

This builds the SDK, packs it, installs the tarball into a temporary project
without lifecycle scripts, and checks its actual exports in Node and Chromium.
Both Node entry paths run the portable conformance cases; the automatic loader
is checked with network access disabled, a failed initialization and retry,
and concurrent initialization. Declarations resolve outside the monorepo, and
conversion-only bundling is checked. The tested tarball and `SHA256SUMS` are
retained in ignored `release/`. Consumers install that tarball without Rust.

Changes to this API also run `npm run check`, `npm test` and the existing web
checks. No engine formulas or native bindings change for packaging alone.
Before publishing, review package contents (`tar -tzf release/*.tgz`), license,
source attribution, the package changelog and exact release commit. Keep
`packages/sdk/package.json` and the Rust workspace version aligned. Update the
web app's dependency and lockfile when the SDK version changes.

## First publication

The npm owner must have access to the `turnmark` scope and complete npm account
security setup. Do not put an npm token in GitHub or this repository. The first
publish may need an interactive maintainer login before package-level trusted
publisher settings exist. From the reviewed release commit, prepare the tarball
above, run `npm login`, then publish that exact file:

```sh
npm publish ./release/turnmark-sdk-0.1.0.tgz --ignore-scripts --access public --provenance=false
```

The initial local bootstrap cannot carry GitHub provenance. Subsequent CI
releases are designed to use OIDC and provenance once the configuration below
is completed. This document does not authorize publishing an
unreviewed commit or changing the existing GPL-3.0-or-later license.

## Subsequent releases

Before enabling publishing, configure the GitHub `npm-production` environment
for `main` only, with a maintainer reviewer, and configure the package's npm
trusted publisher with exactly:

| Field             | Value                |
| ----------------- | -------------------- |
| GitHub owner      | `Stanback`           |
| Repository        | `turnmark`           |
| Workflow filename | `sdk-release.yml`    |
| Environment       | `npm-production`     |
| Allowed action    | Direct `npm publish` |

Use npm's option to require two-factor authentication and disallow traditional
publishing tokens. Configure trust close to the intended release: an unused
configuration expires after two days. npm's [trusted publishing guide](https://docs.npmjs.com/trusted-publishers/)
documents the setup and CLI requirements. These account/environment settings
are release prerequisites, not settings created by this PR.

Dispatch **Prepare or publish npm package** on `main`, selecting `sdk` or
`mcp` and that package’s committed version. SDK and adapter versions are
independent.
Leaving `publish` false only produces a verified artifact. Enabling it runs the
same checks and sends that run's immutable artifact to a new publishing runner,
behind the environment approval. It verifies the checksum and publishes the
tarball with lifecycle scripts disabled. Only that job receives OIDC permission;
it checks out no repository code and installs no application dependencies.
No PR, tag push or ordinary main push triggers an npm publication. There are no
Cloudflare, signing or store credentials in this workflow.

After a successful publish, check the registry version, install it in an
external consumer, record the release commit and update the changelog/status.
Registry versions are immutable: fixes get a new version instead of replacing
an existing package. During 0.x, breaking public API changes increment the minor
version and compatible fixes increment the patch version. Dataset editions
remain explicit in responses and release notes.

## Published MCP 0.2.0

MCP Apps is included in the adapter's published 0.2.0 package and Worker artifact.
`npm run test:mcp` verifies packed offline consumers, both HTTP protocol modes,
resource metadata and the official browser bridge over stdio and Workers HTTP. A fresh MCP tarball was also
installed against published SDK 0.1.0, with conversion/resource reads verified
without runtime network access. The adapter does not require a new SDK release.
See [MCP Apps review](MCP_APPS_REVIEW.md) for screenshots and host limits.

Release source: `d7b8d9cc54ab58b92a65b1ee154e5af80084ae5e`.
The [release workflow](https://github.com/Stanback/turnmark/actions/runs/39196653276)
tested the exact archive before publishing it with OIDC and GitHub provenance.
The `npm-production` environment accepts only `main` and requires review by
Stanback. Package-level trust permits this repository's `sdk-release.yml` in
that environment; bypass 2FA tokens are disabled for MCP. SDK trust remains a
separate package-level setup.

A fresh external project installed MCP 0.2.0 and registry SDK 0.1.0 with
lifecycle scripts disabled. Both supported protocol modes, with and without
Apps capability, passed discovery, the versioned resource/MIME/CSP checks,
42 exact SDK-result comparisons and eight malformed requests per mode,
source attribution, cancellation and recovery with runtime fetch disabled.
The registry archive's integrity matches the tested same-run artifact.
`npm audit signatures` verified all 18 installed packages' registry signatures
and 10 available attestations.

| Package         | Version | Registry `dist.shasum`                     |
| --------------- | ------- | ------------------------------------------ |
| `@turnmark/mcp` | `0.2.0` | `7eba288d429dc27c4b584ac06302ea232f3bae80` |

Future preparations can retain a verified MCP tarball and `SHA256SUMS` in ignored
`release/` with `npm run pack:mcp`. The preparation job tests both the workspace
SDK and published registry SDK without runtime network access; the publishing
runner has no checkout, application dependencies or stored token. Do not add an
npm publishing token to CI or replace an existing registry version.
