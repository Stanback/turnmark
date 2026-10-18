# Website hosting

The production website is `https://turnmark.app/`, hosted as static assets by
`turnmark-web` in the Brianna Stanback Cloudflare account. `wrangler.jsonc` owns
the configuration: no server-side code, storage bindings or runtime secrets.
The Worker Custom Domain manages DNS and certificates for `turnmark.app`. Do not add competing DNS records in the IaC repo.

Metadata, Vite's base, the PWA manifest, generated service worker and native
share links use the new root URL. Browser storage starts fresh on this origin;
no history transfer is included. Native device storage is unaffected. After
production deployment succeeds, the custom domain serves that tested build.
The short-lived GitHub Pages site and its redirect deployment are retired.

## Credential boundary

- PRs and application builds have read-only GitHub permissions and no Cloudflare
  credentials. There is no `pull_request_target` or `workflow_run` deployment.
- `main` requires a PR and passing `web-ci`/`engine-ci` checks, including for
  administrators. Direct pushes, force pushes and deleting `main` are blocked.
  This single-maintainer project does not require another person's approval.
- The `cloudflare-production` environment permits only the `main` branch.
  Publishing is automatic after its web checks pass. Store
  `TURNMARK_WORKER_DEPLOY_TOKEN` as an **environment secret**, never a repository
  or organization secret.
- Deployment uses a fresh runner, a sparse checkout of only deployment tooling
  and Wrangler configuration, and `website-<commit SHA>` from this same workflow
  run. It never installs app dependencies or runs application build scripts.
- Deployment tools have a separate lockfile and install with `--ignore-scripts`,
  without credentials present. Only version-upload/deploy steps receive the
  token. They invoke pinned Wrangler directly. Actions are pinned to commit
  SHAs; upload's structured output selects the exact version deployed to 100%.
- Use an account-owned token with **Workers Editor scoped only to
  `turnmark-web`**. Exclude product-wide Workers access, zone/DNS, registrar,
  token management, storage, billing and IaC-state permissions. Keep this static
  Worker free of storage bindings and application secrets. CI publishes versions
  without applying routes or domains, so it does not need zone permissions.
- Local OAuth credentials and private IaC tokens never enter public-repo CI.
  Never print tokens, put them in command arguments, commit them or paste them
  into chat. `.env*`, `.dev.vars*` and local Wrangler state are ignored.

Repository/account owners can still change their security settings. A deployment
token can modify this website and must still be treated as a secret.

The separate `turnmark-mcp` Worker uses its own individual-Worker token in
the main-only `cloudflare-mcp-production` environment. It follows the same
credential-free build and isolated artifact deployment boundary; neither token
can deploy the other Worker. See [MCP.md](MCP.md) for its bootstrap, abuse limits
and rotation date. Keep both services on Workers Free unless the owner approves
a plan change.

## Initial setup

Worker creation needs broader access than routine publication. After reviewing
the migration PR, bootstrap once locally with the existing Cloudflare login in
the correct account:

```sh
npm ci
npm ci --prefix deployment --ignore-scripts
npm run build
node deployment/node_modules/wrangler/bin/wrangler.js deploy --config wrangler.jsonc
```

This creates the Worker and binds the custom domain. Keep provisioning
privileges local; CI uses `versions upload` and `versions deploy`, which leave
domain/route configuration alone.

Once the Worker exists, create an account-owned API token with Editor on that
individual Worker. Set an explicit expiry and rotate before expiration. Store
it directly in GitHub Settings → Environments → `cloudflare-production` →
Environment secrets as `TURNMARK_WORKER_DEPLOY_TOKEN`. Do not reuse the private
IaC token or the broad "Edit Cloudflare Workers" template. Confirm its scope in
Cloudflare before enabling CI publication.

The main-only environment, branch protection and read-only Actions defaults were
configured while preparing this migration. A workflow reference does not create
those protections; verify them if the repository is recreated or moved. Merge
after bootstrap and the scoped environment secret are ready.

## Local checks

```sh
npm ci --prefix deployment --ignore-scripts
npm run test:production
node deployment/node_modules/wrangler/bin/wrangler.js versions upload --dry-run --no-bundle --config wrangler.jsonc
actionlint
```

Production tests build the app and use local Wrangler to check root URLs,
metadata, PWA assets, legacy-path redirects, offline Wasm calculations and saved
swims. No Cloudflare token is needed. Native sharing changes also need the
existing iOS and Android UI checks.

## Rotation and rollback

Create a replacement token with the same individual-Worker scope, update the
environment secret directly, verify a deployment, then revoke the old token.
For suspected compromise, revoke immediately. Do not broaden permissions to
work around an authorization error.

Keep a known-good Worker version for Wrangler rollback or deployment through
Cloudflare. There is no application database to migrate or roll back.

References: [Worker permissions](https://developers.cloudflare.com/workers/authorization/workers/),
[version deployment](https://developers.cloudflare.com/workers/versions-and-deployments/deployment-management/),
[custom domains](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/),
and [GitHub environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments).
