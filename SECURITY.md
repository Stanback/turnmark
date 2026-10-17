# Security policy

## Supported versions

Security fixes target the latest code on `main` and the current
[hosted app](https://stanback.github.io/turnmark/). Older releases, cached offline
builds, and forks do not receive separate maintenance. Reconnect and reload to
receive updates; a waiting service worker activates after existing app tabs close.

## Reporting a vulnerability

Please use GitHub's private
[Report a vulnerability](https://github.com/Stanback/turnmark/security/advisories/new)
form. You can also find it under the repository's **Security → Advisories** tab.
Do not disclose exploit details in public issues or pull requests.

Include:

- The affected URL, commit or build, browser, and operating system.
- Reproduction steps and a minimal proof of concept using sample data.
- The expected security boundary and the impact of crossing it.
- Any suggested mitigation, if known.

Do not include credentials, private swimmer information, or other people's
browser-storage contents. If the form is unavailable, use the maintainer's
[contact form](https://bristanback.com/contact/) to request a private reporting
channel before sending exploit details.

Reports are reviewed by the maintainer, who will coordinate investigation,
fixes, and disclosure through the private report. This is a volunteer-maintained
project; response and fix times are not guaranteed.

## Scope

Turnmark is a static, browser-only app with no accounts or backend. Relevant
issues include script injection, unsafe handling of shared URL fragments or
stored data, unintended disclosure of local swim data, and compromised
dependencies or build/deployment behavior. Local storage is not encrypted and
is accessible to people or extensions with access to that browser profile.

Ordinary calculation discrepancies, outdated standards, and UI bugs belong in
the [public issue tracker](https://github.com/Stanback/turnmark/issues/new/choose),
unless they also create a security vulnerability. Issues in source organizations'
websites or GitHub itself should be reported to those services.
