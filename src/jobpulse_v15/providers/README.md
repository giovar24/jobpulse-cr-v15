# providers

> Blueprint index for the `jobpulse_v15.providers` namespace.

## Purpose

`providers/` groups the integration code that reaches **external job portals on
the user's behalf** — the sites that publish postings but expose neither a
public API nor a machine-readable feed. Code here is about *establishing an
authenticated browser session* and *sweeping cookie/Cloudflare-guarded pages*;
it is not about parsing, persisting, classifying, or scoring postings (those
live in `scraper.py`, `repository.py`, `analysis_flow.py`, and `matching.py`).

This directory carries **no source files of its own**. It exists only to group
its children, and it is not a regular package (no `__init__.py`).

## Layout

| Path | Kind | Responsibility |
|---|---|---|
| `login/` | Component package | Session establishment and sweeps of login-/Cloudflare-protected portals. |

## Structure and data flow

```
caller (scraper layer)
  └── opens Brave with CDP, passes `port`
        └── providers/login/browser_sites.py  →  LoginSitesProvider.fetch()
              ├── mode "dom"        → CSS-selector card extraction
              ├── mode "page_fetch" → in-page fetch of the SPA's internal API
              └── unresolved login/Cloudflare wall
                    → registrar_requerimiento() (pending-login registry) + skip
providers/login/auto_login.py
  └── optional pre-step: fill the portal's login form with a stored credential
```

## Boundaries

- **Owns:** acquiring an authenticated browser context, and converting
  login-/Cloudflare-guarded pages into raw offer dictionaries.
- **Does not own:** launching or closing the browser (the caller owns the CDP
  endpoint), persisting jobs, classifying areas, or evaluating matches.
- **Consumed by:** the scraper layer, which passes the CDP `port` and receives
  offer dictionaries. **⚠ No production caller today**: neither
  `jobpulse_v15.providers.login.browser_sites` nor
  `jobpulse_v15.providers.login.auto_login` is imported anywhere under `src/`;
  `scraper.FETCHERS` has no entry for them, and `LoginSitesProvider.fetch`,
  `intentar_login` and `hay_login_configurable` have **zero** call sites. The
  modules are scaffolding for a portal integration that is not wired yet.

## Invariants

- Neither `providers/` nor `providers/login/` declares an `__init__.py`: both are
  PEP 420 namespace packages, imported by dotted module path (for example
  `jobpulse_v15.providers.login.auto_login`).
- Provider code **never starts a browser process**; it connects to one that is
  already running.
- Missing or ambiguous input degrades to *skip and continue* — with one
  exception: the constructor raises `ValueError` for `timeout <= 0` or a
  `request_delay` outside `[0, 10]`, and `fetch()` raises `ValueError` when
  `pages` is not an `int` or falls outside `1..50`
  (`providers/login/browser_sites.py:94-97,115-118`).

## Verification

- `python -m pytest tests/ -q`

  pytest runs on the **system** interpreter; the project `.venv` does not ship
  pytest. To run a single file:
  `python -m pytest tests/<name>.py -q`.
- Per project convention, every fetcher carries a companion test at
  `tests/test_<name>.py`. **⚠ Not met here**: neither
  `tests/test_browser_sites.py` nor `tests/test_auto_login.py` exists; the only
  trace of `browser_sites` in `tests/` is a prose mention in a docstring
  (`tests/test_fetcher_async.py:10,69`).

## Children

- [`login/`](login/README.md) — component package contract.
