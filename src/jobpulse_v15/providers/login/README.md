# providers/login

> Component package contract for `jobpulse_v15.providers.login`.

## Purpose

`providers/login/` handles the two obstacles that block automated collection
from corporate portals: **credential walls** and **bot interstitials**. It runs
entirely against a browser the user already owns (Brave, reached over CDP), so
the real session — cookies, SSO state, Cloudflare clearance — is reused instead
of recreated.

The package is a PEP 420 namespace package: there is no `__init__.py`. Import by
full module path (`jobpulse_v15.providers.login.auto_login`).

## Modules

| Module | Public surface |
|---|---|
| `auto_login.py` | `hay_login_configurable`, `intentar_login` |
| `browser_sites.py` | `LoginSitesProvider`, `LoginSitesOffers`, `LoginSitesFetchError` |

---

## Interface — `auto_login.py`

Opt-in automatic login with a manual fallback. A single attempt is made only
when a credential is stored **and** the site opted in; otherwise behavior is
unchanged (the user logs in manually through the "Sesiones" tab).

### `hay_login_configurable(empresa: str, site: dict | None = None) -> bool`

Gate used by callers before attempting a login. Returns `True` only if a stored
credential exists for `empresa` and the matching record has `auto_login`
enabled. When `site` is provided, the method additionally
requires that the site's `login` block carries a `login_url`.

**⚠ Exact semantics (`auto_login.py:195-202`):** the flag is read from the
merged `lista_sitios_login()` output (which combines `login_requerido.json`,
`login_sites.json` and `pending_login.json`), and the records written by
`agregar_sitio_login` into `login_sites.json` carry **no** `auto_login` key —
that flag lives in `login_requerido.json` / `credenciales.json`. Moreover,
when **no** record matches `empresa`, the loop falls through and the function
returns `True` **without any `auto_login` opt-in**.

### `intentar_login(page, empresa: str, cfg: dict) -> dict`

Fills and submits the portal's login form on the supplied Playwright `page`.

Return contract — always a dict, never an exception for expected failures:

| Key | Type | Meaning |
|---|---|---|
| `ok` | `bool` | `True` only when the login form is gone / the success selector appeared. |
| `motivo` | `str` | Empty on success; a human-readable failure reason otherwise. |
| `titulo` | `str` | Page title observed at the decision point (empty when unknown). |

Failure reasons emitted: `"sin credencial guardada"`,
`"sitio sin login_url configurado"`, `"no encontre el campo usuario (<sel>)"`,
`"no encontre el boton de envio"`, `"el sitio seguia en login: <marker>"`,
`"el formulario sigue ahi (credencial rechazada o paso extra/2FA)"`,
`"no aparecio <ok_sel>"`, and `"error: <exception>"` for any unexpected fault.

**⚠ The list is not exhaustive** — the SSO path emits at least five more
reasons (`auto_login.py:74,139-142,145-149,172-174`):
`"<proveedor> pide la password de la cuenta (sesion vencida); se usa el login manual"`,
`"llegue a <proveedor> pero no encontre la cuenta <email> en el selector; se usa el login manual"`,
`"la sesion no se completo (seguia en <url>)"`,
`"no encontre el boton SSO (<sel>): <e>"` and
`"seguia en Google (<url>)"`.

`cfg` keys (all optional except `login_url`):

| Key | Purpose |
|---|---|
| `login_url` | Login page URL. **Required** — without it no attempt is made. |
| `user_sel` / `pass_sel` / `submit_sel` | Field and button selectors. Sensible defaults apply. |
| `ok_sel` | Selector that must exist for success to be declared. |
| `ok_negativos` | Substrings that, if present in the title, mean the login did not take. |
| `espera` | Milliseconds to wait after submit (default `4000`; `5000` in the SSO path). |
| `sso` | External identity provider (for example `"google"`). |
| `sso_sel`, `sso_iframe`, `sso_inner_sel` | SSO button locators. |

**SSO path.** When the stored credential has no `password` but declares `sso`
(either on the credential or in `cfg`), `intentar_login` delegates to the
internal `_login_sso`, which clicks "Continue with Google" and picks the user's
account from the browser's existing Gmail session. If Google asks for a password
(expired session), CAPTCHA/2FA intervenes, or the account cannot be selected,
the attempt fails **without touching the run** and the caller falls back to
manual login. The Google button is mounted inside its own iframe, so the click
targets `sso_iframe` (or the built-in Indeed / Google-Identity-Services
selectors) via `frame_locator`.

**Two-step logins.** If the password field is not present on the first screen
(the site shows email first), the module re-checks for it after the first submit
and completes the flow, targeting portals such as Indeed.

---

## Interface — `browser_sites.py`

Sweep of portals that require a session and/or sit behind Cloudflare. Both
supported modes reuse the user's Brave profile over CDP.

### `LoginSitesProvider(*, timeout: float = 30.0, request_delay: float = 0.5)`

| Argument | Rule |
|---|---|
| `timeout` | Seconds; must be `> 0`, otherwise `ValueError`. Applied to navigations and API requests. |
| `request_delay` | Seconds between requests; must be `0 ≤ x ≤ 10`, otherwise `ValueError`. `0` disables the pause. |

### `.fetch(site, *, pages: int = 1, search_text: str | None = None, skip_source_job_ids: set[str] | None = None, port: int) -> LoginSitesOffers`

Runs the sweep and returns the offers. `port` is the CDP port of the
caller-managed Brave instance and is **mandatory**.

- `pages` must be an `int` (not `bool`) in `1..50`, otherwise `ValueError`.
- `skip_source_job_ids` marks postings already known, so they are omitted and
  counted rather than re-emitted.
- `search_text` is accepted for call-site symmetry but is **not used** by this
  implementation.

`site` keys read: `site_id`, `company_name`, `country` (default `"CR"`), `urls`
(falling back to `site_config.url`), and `site_config`.

`site_config` keys:

| Key | Purpose |
|---|---|
| `mode` | `"dom"` (default) or `"page_fetch"`. |
| `card_sel` | **Required** for `dom` mode; without it the sweep returns empty. |
| `title_sel`, `company_sel`, `loc_sel`, `url_sel`, `date_sel` | Per-field CSS selectors for card extraction. |
| `next_sel` | "Next page" control; its presence enables pagination. |
| `login` | Login block (`login_url`, `user_sel`, `pass_sel`) reused for wall detection. |
| `api.url`, `api.list_path`, `api.item` | `page_fetch` mode: internal API URL, list selector (default `$.data`), and per-field key names. |

`dom` mode navigates each URL, extracts cards by selector, sanitizes
`source_job_id` from the link (falling back to the title) by **replacing** every
disallowed character with `_` (`re.sub(r"[^a-zA-Z0-9_-]", "_", …)` — it
*substitutes*, it does not filter, and enforces no minimum length of 1),
deduplicates within the run, and paginates by `?page=N` and/or the `next_sel`
control. **⚠ Pagination caveat:** without `next_sel` the DOM loop `break`s after
page 1, so the `?page=N` URL is never requested; with `next_sel` present the
code clicks "next" **and** navigates to `?page=N` on the next iteration, so the
listing advances twice per round.

`page_fetch` mode issues
`page.context.request.get` calls from inside the page so that the SPA's
same-origin cookies (including Cloudflare clearance) are attached, then maps
the JSON list with a minimal `$.a.b[0]` traversal. **⚠ Traversal caveat:** a
path segment is treated as an index only when it **starts** with `[` (e.g.
`$.a.[0]`); `$.a.b[0]` is looked up as the literal key `"b[0]"` and yields an
empty list. In `page_fetch` mode the `source_job_id` is **not sanitized at
all** (raw `str(item.get(...))`).

Each emitted offer is:

```python
{
  "source_job_id": str, "source_url": str, "source_updated_at": str | None,
  "job": {"job_id": f"ls-{site_id}-{source_job_id}", "title": str, ...},
  "raw_payload": dict,
}
```

The nested `job` carries `company`, `location_raw`, `country`, `work_mode`
(`"unknown"`), `employment_type` (`None`), `date_published`, `expires_at`
(`None`), `posting_language`, `posting_language_origin`, `description_raw`,
`requirements_raw`, and `salary_raw`.

### `LoginSitesOffers(offers, *, jobs_skipped: int = 0)`

A `list[dict]` subclass returned by `fetch`. Beyond the offer list it exposes
`jobs_skipped`, the count of postings skipped as duplicates or as pre-known IDs.

### `LoginSitesFetchError`

A `RuntimeError` subclass declared for this package. It is **not raised by the
current implementation** — `fetch` degrades to empty/skipped results instead.

---

## Interstitial handling

Before extraction, each page is screened by `_es_interstitial_o_login`:

- the **title** contains `"un momento"`, `"just a moment"`, or
  `"checking your browser"`; or
- a **login form** is present (only when a `login` block with `login_url` is
  configured); or
- the first 2000 characters of the body contain `"inicia sesion"`,
  `"iniciar sesion"`, `"sign in"`, `"log in"`, or `"acceder"`.

`_manejar_interstitial` then tries to clear a Cloudflare Turnstile by clicking
its checkbox inside `challenges.cloudflare.com` / `turnstile` iframes. If that
succeeds, extraction continues; otherwise it returns a reason string
(`"login-wall detectado (se necesita sesion manual)"` when a `login_url` is
configured, else `"interstitial Cloudflare no resuelto automaticamente"`).
The sweep registers that reason in the pending-login registry and **skips the
URL**, keeping the run alive. Note that `browser_sites` deliberately does not
perform the login itself — that is `auto_login`'s job. **⚠ But `auto_login`
has no caller anywhere in the codebase**: the only scraper that documents an
auto-login step (`IndeedFetcher._auto_login`) explicitly logs
`"auto-login SSO Google NO implementado aún en v1.5"` and returns `False`
without calling `intentar_login` (`src/jobpulse_v15/indeed.py:226-234`).

## Invariants

- **Caller owns the browser.** `fetch` connects with
  `chromium.connect_over_cdp("http://localhost:{port}")` and uses
  `browser.contexts[0]` — the user's own context. Nothing in this package
  launches or closes a browser.
- **Failure is never fatal.** Missing config yields an empty `LoginSitesOffers`
  plus a warning; unresolved walls register a requirement and skip. Per-card and
  per-page exceptions are caught and logged.
- **No duplicate offers.** Within a single `fetch`, a `source_job_id` already
  seen in the run, or present in `skip_source_job_ids`, is skipped and counted
  in `jobs_skipped`; it is never emitted twice.
- **Defaults are Costa Rica / Spanish.** `country` defaults to `"CR"` and
  `posting_language` is emitted as `"es"` with
  `posting_language_origin = "source"`; both are placeholders corrected
  downstream.
- **An empty listing is not a wall.** A legitimately empty result is
  "0 positions", not a pending-login entry. **⚠ In code:** the literal
  `"0 posiciones"` / `"0 positions"` is never emitted; the empty-listing path
  only logs `"LoginSites %s: sin tarjetas en %s"` and breaks
  (`browser_sites.py:191-192`).
- **Credential gate is explicit.** `intentar_login` refuses to act unless a
  stored credential exists *and* `cfg["login_url"]` is configured; a missing
  credential is reported as `"sin credencial guardada"`. **⚠ The `auto_login`
  opt-in flag is checked exclusively in `hay_login_configurable`**, which no
  production code calls (`auto_login.py:193-199,211-219`) — so the opt-in is
  not enforced on the login path itself.
- **Known quirks (maintenance hazards, behavior-neutral today).**
  `_limpiar` is defined twice in `browser_sites.py` (module top and file end);
  the later, identical definition wins. `LoginSitesFetchError` is declared but
  unused. `_fetch_api`'s `api.item` entries are documented as "dot-paths" but
  are looked up as flat keys.

## Side effects and boundaries

- **Browser:** navigates, fills inputs, clicks controls, and may open a Google
  SSO popup; each sweep page is closed in a `finally` block. No page or context
  created by the caller is closed. **⚠ Exception:** the Google popup opened by
  `_login_sso` is **never closed** — the code only polls `pop.is_closed()` to
  detect that Google closed it by itself (`auto_login.py:122-128,153`).
- **Filesystem / registry:** on an unresolved wall, `registrar_requerimiento`
  (from `jobpulse_v15.credenciales`) records the pending login in
  **`data/empresas/login_requerido.json`** (`REQ_JSON`); note that
  `data/empresas/pending_login.json` is a *separate* store — the one named in
  the module's own docstring (`credenciales.py:41`,
  `browser_sites.py:25`). `auto_login` only reads credentials (keyring →
  `credenciales.json` → `.env`). Passwords are never logged — only the company,
  the SSO provider, and the account email.
- **Database:** no access. Persistence is the caller's responsibility.
- **Dependencies:** `playwright.async_api` and `jobpulse_v15.credenciales`.
  `auto_login` imports `credenciales` lazily inside its functions to avoid an
  import cycle.

## Verification

- Full suite: `python -m pytest tests/ -q`
- Single file: `python -m pytest tests/ -k <pattern> -q`. **⚠ These modules
  are NOT covered**: neither `tests/test_browser_sites.py` nor
  `tests/test_auto_login.py` exists in `tests/` — the project convention of one
  test file per fetcher is not met for this package.

  pytest must run on the **system** interpreter — the project `.venv` does not
  install pytest.
