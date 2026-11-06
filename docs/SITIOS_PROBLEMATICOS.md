# Sitios problemáticos: ANE, Indeed, LinkedIn y Elempleo

> Guía técnica de los 4 scrapers de navegador (CDP) que suelen dar problemas.
> Incluye: cómo funciona cada sitio, errores comunes con su solución exacta y
> procedimientos de recuperación. Actualizado: 2026-11-06 (O13 · Ola 3).

---

## Arquitectura común a los 4

Todos usan **Playwright sobre CDP conectado a TU Brave real** (no abren un
navegador aparte), de modo que las cookies/sesiones que ya tienes en Brave se
reutilizan.

```
┌──────────────┐  CDP :9222  ┌──────────────────┐
│  Fetcher     │────────────▶│  Brave (perfil    │
│  (v1_5)      │  WebSocket  │  real del usuario)│──▶ sitio web
└──────────────┘             └──────────────────┘
```

> **LinkedIn es la excepción (O13 · Ola 3.1):** su listado público se puede
> pedir por **HTTP simple** (sin navegador). El scraper usa HTTP primero y el
> navegador (Brave/CDP) como refuerzo que fusiona resultados y aporta cookies.
> Elempleo también es "navegador primero", pero su listado se puede pedir por
> HTTP (se usa para investigar, no en producción).

### El estado `requiere_login` (O13 · Ola 3.3)

Un sitio que da 0 avisos **porque pide iniciar sesión** no está roto: es otra
cosa. Antes caía en `zero_results` y llenaba la racha de "sitio muerto"
(3 corridas con 0 avisos → `review_required=1`) que el usuario tenía que
revisar sin saber que lo que faltaba era la sesión.

| Pieza | Valor |
|---|---|
| Salud del sitio (`source_sites.health_status`) | `requiere_login` |
| Estado de la corrida (`source_run_sites.status`) | `requires_login` |
| Racha de ceros (`consecutive_zero_runs`) | **NO** cuenta este estado |
| `review_required` | **sí** (el usuario tiene que iniciar sesión) |
| `site mark-reviewed` | Lo reconoce, pero la salud sigue diciendo `requiere_login` |
| UI v2 | La fila de la sonda muestra 🔑; el barrido lista los sitios que piden login |

En código: `jobpulse_v15.requiere_login.RequiereLoginError` (la lanzan ANE,
LinkedIn y Elempleo) → `ingestion.py` la traduce a `requires_login` →
`repository.record_site_result(status=…)` actualiza la salud.

### Requisito previo (el más importante)

Brave debe estar corriendo con **depuración remota en el puerto 9222** y con el
**perfil real**:

```
"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    --remote-debugging-port=9222
    --user-data-dir="C:\Users\giova\AppData\Local\BraveSoftware\Brave-Browser\User Data"
```

**⚠️ Error de configuración histórico:** `--user-data-dir` debe apuntar a la
**raíz** `User Data`, **NO** a `User Data\Default`. Si apuntas a `Default`,
Chromium crea un perfil NUEVO y vacío dentro de ese directorio: Brave se abre
"como si fuera la primera vez" (sin marcadores, sin sesiones) y el login
siempre falla. Este bug estuvo en `jobpulse-v15.bat` y se corrigió.
**2026-10-27: el MISMO bug se encontró vivo en `BraveManager._get_user_data_dir()`**
(la ruta genérica que usan el botón "Login manual" de Configuración y el CLI
`login`); lo enmascaraba `login_ane.py` — teclea credenciales frescas y ANE
"funciona" — pero con ese perfil Indeed/LinkedIn nunca veían las sesiones
reales. **CORREGIDO el mismo día (O7.1)**: `--user-data-dir` a la raíz +
`--profile-directory={perfil}`.

**Verificar que CDP está vivo:**

```powershell
curl.exe -s http://127.0.0.1:9222/json/version
# Debe responder JSON con "Browser": "Chrome/..."
```

**Error típico si no está vivo:** `BrowserType.connect_over_cdp: connect
ECONNREFUSED 127.0.0.1:9222` → el barrido termina en `error`. Solución: lanzar
Brave con el comando de arriba (o usar el launcher `jobpulse-v15.bat`).
Nota: **desde O7.2 (2026-10-27) el barrido de la UI abre Brave solo** y lo
cierra al terminar (solo si ella lo abrió). Si tu Brave diario corre SIN CDP,
la app no puede abrir el puerto: ciérralo del todo y reintenta. CINDE/Procomer
(API) siempre corren — sus "0 nuevas" son idempotencia normal, no un fallo.

---

## 1) ANE (ane.cr) — sitio estatal, ASP.NET MVC

### Cómo funciona

| Aspecto | Detalle |
|---|---|
| URL base | `https://www.ane.cr` |
| Tipo | Sesión obligatoria (listado y detalles piden login) |
| Login | Usuario/contraseña en `/Cuenta/Login` |
| Credenciales guardadas | `data/empresas/credenciales.json` → clave `"ane"` |
| Verificación de sesión | Visita `/Puesto` y busca enlaces `Puesto/Detalles` |
| Detalles | Se piden por **HTTP** (`context.request.get`) reutilizando cookies del navegador |
| Sesión guardada | `data/usuario/sesiones/ane.json` (cookie de sesión, ver abajo) |

Flujo del fetcher (`src/jobpulse_v15/ane.py`):

1. `connect_over_cdp(port)`
2. `_asegurar_sesion(ctx)`: abre `/Puesto`; si el HTML **no** contiene
   `Puesto/Detalles` → tries restaurar la sesión guardada (ver "la cookie de
   sesión") y, si tampoco, **omite el barrido** con estado `requires_login`
   (log: `ANE: sin sesión de detalle; barrido omitido.`; la corrida queda
   `requires_login`, NO es error).
3. Extrae el listado de vacantes (config del sitio: `search_text` y `pages`).
4. Cada detalle se descarga con `requiere_sesion=True`; si el HTML muestra
   `loginForm` o `Cuenta/RegistroUsuario` → error `sesión ANE caducada`.

### La cookie de ANE es de SESIÓN (medido 2026-11-06)

ANE usa `ASP.NET_SessionId`, que es una **cookie de sesión** (`expires = -1`).
Chromium **no** escribe las cookies de sesión en disco al salir: da igual que
el cierre sea **ordenado** (`Browser.close` por CDP, el arreglo de O12 · 1.5).

| Situación | Resultado |
|---|---|
| Login → raspar con el mismo Brave vivo | ✅ funciona (24 avisos medidos) |
| Login → cerrar Brave (ordenado) → reabrir → raspar | ❌ "sin sesión de detalle" (la cookie se perdió) |
| Login → **guardar la sesión** → cerrar → reabrir → raspar | ✅ funciona (ver abajo) |

**El arreglo (O13):** `jobpulse_v15.sesion_navegador` guarda las cookies del
sitio tras un login exitoso en `data/usuario/sesiones/ane.json` (**fuera del
repo**: `data/usuario/` está gitignoreado; es un token de sesión, un secret).
Cuando el scraper detecta que falta la sesión, restaura esas cookies en el
contexto del navegador y vuelve a comprobar. Si la sesión del servidor caducó,
el archivo se borra (no se reintenta para siempre).

Verificación en vivo (2026-11-06): login → 24 avisos; cerrar Brave → reabrir →
raspar → **24 avisos restaurando la sesión** (antes: `requires_login`, 0).

### Errores comunes y soluciones

| Síntoma | Causa | Solución |
|---|---|---|
| `sin sesión de detalle; barrido omitido` | Cookies de ANE vencidas o perfil equivocado | Re-login (ver procedimiento abajo) |
| `sesión ANE caducada (redirige a login)` | La sesión venció a mitad del barrido | Re-login y repetir |
| `connect ECONNREFUSED` | Brave sin CDP | Lanzar Brave con `--remote-debugging-port=9222` |
| `zero_results` en corrida | Sesión OK pero la búsqueda (`search_text` en site_config) no devuelve nada | Ajustar `search_text` en Administrar fuentes (ej: "Soporte" → "Soporte") o revisar el sitio a mano |
| Jobs con descripción muy corta (30–100 chars) | La descripción real está tras el detalle paginado y no se alcanzó a recuperar | Re-barrido tras re-login; el enriquecimiento IA no inventa descripciones |

### Procedimiento de re-login de ANE

**Opción automática (credenciales guardadas, `auto_login=true`):** ejecutar el
script de login contra CDP — completa usuario/contraseña en `/Cuenta/Login`
y verifica el resultado:

```
python <raíz del proyecto>/login_ane.py --mantener-abierto   # imprime "LOGIN ANE: OK"
```

`--mantener-abierto` deja el Brave vivo: la cookie está en la instancia con la
que vas a raspar (es el flujo que evita el "sin sesión de detalle"). El login
**guarda además la sesión** en `data/usuario/sesiones/ane.json`, así que
también funciona aunque cierres y reabras Brave (ver "la cookie de ANE es de
SESIÓN").

Sin ese flag, el script cierra Brave de forma **ordenada** (`Browser.close` por
CDP, O12 · 1.5): el perfil se vuelca bien (lo que el antiguo
`terminate()`/`kill()` no lograba), pero la cookie de sesión de ANE se pierde
igualmente — por eso la sesión se guarda aparte.

Después de un login OK, reejecutar el barrido:

```
python run_scrapes.py ane     # en el barrido del 2026-10-24 devolvió 120 ofertas
```

**Opción manual:** abrir `https://www.ane.cr/Cuenta/Login` en tu Brave,
loguearte, y volver a ejecutar el barrido. La cookie queda en el perfil y el
siguiente barrido la reutiliza.

**Datos de sesión válidos** (para verificar a mano): entrar a
`https://www.ane.cr/Puesto` con tu Brave; si ves la tabla de vacantes con
enlaces a `/Puesto/Detalles/...`, hay sesión.

---

## 2) Indeed (cr.indeed.com) — SPA con overlays agresivos

### Cómo funciona

| Aspecto | Detalle |
|---|---|
| URL base | `https://cr.indeed.com/jobs` |
| Tipo | SPA (web components); listado por JS, detalles vía RPC |
| Login | **SSO Google** (sin contraseña propia): credencial `sso=google`, usuario `giovar24@gmail.com` |
| Verificación de sesión | `_hay_sesion()`: busca "Cerrar sesión"/`/settings` |
| Muro de login | `_muro_login()`: redirección a `/login` o authwall |
| Descripciones | POST a `/rpc/jobdescs` **por lotes** usando la sesión del navegador |

Flujo del fetcher (`src/jobpulse_v15/indeed.py`):

1. `goto cr.indeed.com/jobs?q=<search_text>&l=<location>`
2. **`_cerrar_popups(page)`** (nuevo): cierra overlays que interceptan clics.
3. Extrae tarjetas con `_JS_EXTRACT_JOBS` (y fallback `_JS_EXTRACT_JOBS_FALLBACK`).
4. Pagina hasta `pages` con el botón `a[data-testid='pagination-page-next']`.
5. `_enrich_descriptions()`: POST `/rpc/jobdescs` en lotes para traer la
   descripción completa de cada `jk`.

### El problema más frecuente: el popup de alertas de empleo

Indeed muestra un popup (`DesktopSERPJobAlertPopup`, dentro de un elemento
`<ifl-portal>`) con el email del usuario prellenado para "crear alerta de
empleo". Ese overlay **intercepta los pointer events** y hace que el click en
la paginación falle con:

```
ElementHandle.click: Timeout 30000ms exceeded.
<input type="email" ... id="DesktopSERPJobAlertPopup-email" ...>
  from <ifl-portal> subtree intercepts pointer events
```

**La versión anterior (v1.4) NO tenía manejo de este popup** (su
`next_btn.click()` era idéntico). Solución implementada en v1_5
(`_cerrar_popups`), que se ejecuta tras cada `goto` y antes de cada click de
paginación:

1. Tecla `Escape`.
2. Click en botones de cierre conocidos: `button[aria-label='Close']`,
   `button[aria-label='Cerrar']`, `button[data-testid='alerts-popup-close-button']`,
   `[data-testid='modal-close-button']`, `button[data-testid='serp_close_button']`.
3. Último recurso: `document.querySelectorAll('ifl-portal').forEach(el => el.remove())`
   — retira la capa de overlays de Indeed (solo contiene modales; no rompe el listado).
4. Si aun así el click falla: reintento con `page.evaluate("el => el.click()")`
   (click JS directo, inmune a overlays).

### Errores comunes y soluciones

| Síntoma | Causa | Solución |
|---|---|---|
| Timeout en click + "intercepts pointer events" | Popup de alertas | Ya resuelto con `_cerrar_popups`; si vuelve a aparecer, agregar el nuevo selector a `_POPUP_SELECTORES` |
| Muro de login al extraer 0 tarjetas | Sin sesión en Brave | SSO Google manual: abrir `cr.indeed.com` y loguearse con Google en tu Brave; el barrido reutiliza la sesión |
| `found 0 cards` sin muro de login | Indeed cambió su DOM | Revisar `_JS_EXTRACT_JOBS` y `_JS_EXTRACT_JOBS_FALLBACK` (selectores de tarjetas) |
| Descripciones vacías | `/rpc/jobdescs` rechazó el lote (sesión/cookies) | Revisar log `Indeed rpc/jobdescs no disponible`; re-login o fetch HTTP por vacante como fallback |

---

## 3) LinkedIn (linkedin.com) — el más hostil a automatización

### Cómo funciona (reescrito 2026-11-06 · O13 · Ola 3.1)

| Aspecto | Detalle |
|---|---|
| URL base (listado) | `https://www.linkedin.com/jobs/search/?keywords=…&location=…` |
| Tipo | **Listado público por HTTP simple** + refuerzo por navegador |
| Login | **Opcional**: con sesión hay más resultados y menos rate-limit; el login automático dispara CAPTCHA/2FA |
| Muro de login | El navegador sin sesión recibe **authwall**; por eso el listado se pide por HTTP |
| Detalles | Endpoint público **`jobs-guest`**: `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/<job_id>` |

**Qué cambió (el motivo de los 0 avisos):** el listado que funciona es
`/jobs/search/` (no `/jobs/search-results/`, que responde **999**) y sus
tarjetas son `div.base-card` con `data-entity-urn="urn:li:jobPosting:<id>"`,
`h3.base-search-card__title`, `h4.base-search-card__subtitle`,
`span.job-search-card__location`, `time.job-search-card__listdate` y
`a.base-card__full-link`. Los selectores que se usaban antes
(`[data-occludable-job-id]`, `li[data-job-id]`, `div[data-job-id]`,
`.job-card-container`) **NO existen** en el HTML actual → 0 avisos.

Flujo del fetcher (`src/jobpulse_v15/linkedin.py`):

1. `_listar_http`: pide el listado por HTTP y lo parsea con BeautifulSoup
   (`div.base-card`). El JSON-LD `ItemList` es el **respaldo** (si el DOM
   cambia, el JSON-LD todavía trae título, empresa y ubicación).
2. `_listar_navegador`: si hay CDP, se conecta y fusiona lo que所带来的
   (más resultados + cookies). Si el navegador recibe **authwall**, se marca
   `requires_login` (no es un error).
3. `_fetch_details_guest`: descripción por el endpoint público `jobs-guest`.
4. Si el guest no responde, `_fetch_details_http` con las cookies del navegador.

**Medición en vivo (2026-11-05/06): 60 avisos** (antes 0), con título,
empresa, ubicación, fecha y descripción.

### Rate limit del endpoint `jobs-guest` (medido 2026-11-05)

| Espera entre peticiones | Resultado |
|---|---|
| 0 s | 10 peticiones OK y luego **429** (a partir de la #11) |
| **1,5 s** | **19 OK / 0 429** |

Por eso `request_delay` = **1,5 s** por defecto y, ante un 429, se espera y se
reintenta (8 s, luego 16 s). Con un 429 **no** se prueba enseguida la otra
URL: sería el doble de tráfico y otro 429.

### Errores comunes y soluciones

| Síntoma | Causa | Solución |
|---|---|---|
| `authwall detectado. Se necesita sesión` | LinkedIn redirige a login | Login manual en tu Brave (linkedin.com), luego re-ejecutar barrido |
| Descripciones cortas/ausentes | `jobs-guest` rate-limited (HTTP 429) | El scraper ya espera 1,5 s y reintenta; si persiste, esperar minutos y re-ejecutar |
| 429 / "Too many requests" | Demasiados detalles seguidos | `request_delay` en `site_config` (0–10 s) o menos `pages` |
| El listado devuelve 999 | Se usó `/jobs/search-results/` | Usar `/jobs/search/` (el que usa `_url_listado`) |
| 0 avisos | Selectores desactualizados | `div.base-card` + `data-entity-urn` (ver arriba) |

---

## 4) Elempleo (elempleo.com/cr) — menú lateral que no es el listado

### Cómo funciona (reescrito 2026-11-06 · O13 · Ola 3.2)

| Aspecto | Detalle |
|---|---|
| URL base | `https://www.elempleo.com/cr/ofertas-empleo/` |
| Tipo | Listado + **una navegación por oferta** (el detalle) |
| Login | No hace falta para listar; el botón "Inicia sesión" del encabezado NO es un muro |
| Límite | `site_config["max_ofertas"]` (sin tope por defecto): cada oferta abre su ficha |

**Los 3 bugs reales que daban 0 avisos (verificados 2026-11-05):**

1. **Falso muro de login**: el encabezado de elempleo.com **siempre** trae el
   enlace "Inicia sesión" (es el botón de entrar). La detección `_es_login_wall`
   lo tomaba por un muro y cortaba el barrido en la página 1. Ahora un muro
   real es un **formulario de acceso** (`input[type=password]`,
   `form[action*='iniciar-sesion']`, URL `/iniciar-sesion`), y si hay
   `.result-item` en la página **no** hay muro.
2. **`.ee_list-item` NO son las ofertas**: es el **menú lateral** ("Todos los
   anuncios de empleo", filtros...). Las ofertas siguen en **`.result-item`**
   con `.js-area-bind.area-bind` dentro.
3. **El filtro de país miraba el cantón**: la ubicación del aviso es "San José"
   y el país ("Costa Rica") va aparte → se descartaban **todas** las ofertas.
   Ahora `_pasa_filtro_pais` mira título + empresa + ubicación + país.

Además: la empresa ya no viene en `datalayertag` sino en `.js-offer-company`;
la descripción se lee de `.description-block` y los requisitos de las etiquetas
`.requirements-content li .info-tag-not-select` (el aviso no tiene sección
"Requisitos"); la ciudad de la ficha es `.js-offer-city`.

**Medición en vivo (2026-11-05): 3 avisos** (antes 0) con descripción,
empresa, ubicación y fecha.

### Errores comunes y soluciones

| Síntoma | Causa | Solución |
|---|---|---|
| 0 avisos y el log dice "login-wall detectado" | Falso positivo del botón del encabezado | Ya corregido: solo un formulario de acceso es muro |
| 0 avisos y el log dice "sin tarjetas" | Se buscaron `.ee_list-item` (menú lateral) | Ya corregido: `.result-item` + `.js-area-bind.area-bind` |
| 0 avisos y no hay error | El filtro de país descartó todo (ubicación = cantón) | Ya corregido: se mira también el país |
| El barrido tarda mucho | Cada oferta abre su ficha | `site_config["max_ofertas"]` (ej: 20) |
| Faltan requisitos | El aviso no tiene sección "Requisitos" | Se leen las etiquetas `.requirements-content` |

---

## Checklist de diagnóstico rápido (los 4 sitios)

1. **¿Brave vive con CDP?** → `curl http://127.0.0.1:9222/json/version`
2. **¿Es el perfil real?** → si Brave se ve vacío, el launcher (o
   `BraveManager`) apunta a `User Data\Default` (mal) en vez de `User Data`
   (bien).
3. **¿Hay sesión en el sitio?** → abrir el sitio en tu Brave y verificar a mano.
4. **¿Qué dijo la última corrida?** → tabla `source_run_sites` en la BD
   (`status`, `error_message`).
5. **¿El sitio cambió su DOM?** → abrir el sitio con "Inspeccionar" y comparar
   los selectores del fetcher.

## Estado del barrido de referencia (2026-11-06, O13 - Ola 3)

| Fuente | Resultado | Notas |
|---|---|---|
| CINDE | 17 nuevas | API, sin navegador |
| Procomer | 1 nueva | API; antes devolvía 17 — la fuente expuso menos |
| ANE | **24 avisos** (2 barridos seguidos) | Con login + sesión restaurada; sin login → `requires_login` |
| Indeed | 30 nuevas | Requirió fix del popup de alertas |
| LinkedIn | **60 avisos** | Antes 0: selectores nuevos + listado por HTTP |
| Elempleo | **3 avisos** | Antes 0: falso muro de login + filtro de país |

## Bugs sistémicos corregidos en este ciclo (memoria)

1. **`cli.py` sin guard `if __name__ == "__main__"`** → `python -m
   jobpulse_v15.cli <cualquier comando>` no hacía NADA (exit 0, sin salida).
2. **`.env` no cargado en `run_ia_enrichment`** → "IA no configurada:
   base_url requerido" al llamar el enriquecimiento desde UI/scripts.
   Ahora `load_dotenv()` corre dentro de la función.
3. **Launcher con ruta de Brave equivocada** (exe en `AppData\Local` cuando la
   instalación real está en `C:\Program Files\...`) y perfil apuntando a
   `User Data\Default`.
4. **Popups de Indeed** interceptando paginación (ver sección 2).
5. **LinkedIn con selectores muertos** (ver sección 3) → 0 avisos.
6. **Elempleo con un falso muro de login** (ver sección 4) → 0 avisos.
7. **La cookie de ANE es de sesión y Chromium no la persiste** (ver sección
   1) → la sesión se guarda aparte en `data/usuario/sesiones/`.
