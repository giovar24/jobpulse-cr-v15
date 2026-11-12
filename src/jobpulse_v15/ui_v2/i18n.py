# -*- coding: utf-8 -*-
"""i18n de la UI v2 (es → en) — SIN Tk.

CÓMO FUNCIONA
-------------
La **clave** del catálogo es el literal EN ESPAÑOL tal como está escrito en
el código; el valor es su traducción al inglés. `t(clave)` devuelve la
traducción si el idioma vigente es `en`, y la MISMA clave si es `es` (o si
no está en el catálogo): así una cadena sin traducir nunca rompe nada.

DÓNDE SE USA `t()`
------------------
- **Texto fijo de los componentes** (`widgets.py`): `SectionTitle`,
  `StatTile`, `Badge`, `FlatButton`, `EmptyState`, `KeyValue` y
  `SearchField` traducen sus propios argumentos. Una pestaña nueva que use
  componentes queda traducida sin escribir una línea de i18n.
- **Texto fijo suelto** (etiquetas `tk.Label`, `ttk.Checkbutton`,
  encabezados de tabla, títulos de diálogo): `t("literal")` en el punto.
- **Texto dinámico** (f-strings): se traduce la parte fija con
  `t("... {} ...").format(...)`; lo que viene de los datos no se traduce.

IDIOMA VIGENTE
--------------
Estado de módulo (una sola UI por proceso). Lo fija `app.crear_app()` y
`app.reconstruir_con_paleta()` leyendo `ui_config.json` (clave «idioma»,
ver `configuracion.idioma_actual`). Cambiarlo desde Configuración reconstruye
la app entera, así que todos los widgets se vuelven a montar traducidos.
"""
from __future__ import annotations

# Nombres visibles del selector de Configuración.
IDIOMAS: dict[str, str] = {
    "es": "Español",
    "en": "English",
}

IDIOMA_DEFECTO = "es"

# Catálogo es → en. Agregar un texto nuevo = escribirlo en español en el
# código y añadir aquí su traducción (el test de cobertura lo exige).
_EN: dict[str, str] = {
    # --- shell (app.py) ---
    "JobPulse CR · v1.5": "JobPulse CR · v1.5",
    "Actualizar": "Refresh",
    # --- títulos y subtítulos de las pestañas ---
    "Datos crudos": "Raw data",
    "Cada aviso con los valores originales de la fuente":
        "Each posting with the source's original values",
    "Perfil": "Profile",
    "Datos del candidato que alimentan la evaluación":
        "Candidate data that feeds the evaluation",
    "Vacantes": "Postings",
    "Ranking ATS: las vacantes que mejor encajan con tu perfil":
        "ATS ranking: the postings that best fit your profile",
    "Scraping": "Scraping",
    "Ejecutar un barrido de las fuentes del sistema":
        "Run a scan of the system sources",
    "Cuentas": "Accounts",
    "Credenciales de los sitios que piden inicio de sesión":
        "Credentials for sites that require sign-in",
    "Configuración": "Settings",
    "IA, navegador, sondas, apariencia, cachés, retención y diagnóstico":
        "AI, browser, probes, appearance, caches, retention and diagnostics",
    # --- diálogo de importación de CV (dialogs.py) ---
    "Datos detectados en el CV": "Data detected in the CV",
    "No se detectaron datos compatibles.": "No compatible data was found.",
    "Seleccionar todo": "Select all",
    "Ninguno": "None",
    "Cancelar": "Cancel",
    "Revisar datos del CV": "Review CV data",
    "Importar seleccionados": "Import selected",
    # --- datos crudos (tabs/crudos.py) ---
    "Buscar por título, empresa o texto…":
        "Search by title, company or text…",
    "Solo con descripción completa": "Only with full description",
    "Exportar CSV": "Export CSV",
    "Ajusta los filtros o ejecuta un barrido desde la UI principal.":
        "Adjust the filters or run a scan from the main UI.",
    "Sin avisos": "No postings",
    "Ningún aviso seleccionado": "No posting selected",
    "Elige una fila para ver sus datos crudos.":
        "Select a row to see its raw data.",
    "Fuentes": "Sources",
    "Abrir aviso en el navegador": "Open posting in browser",
    "Sin registros de fuente": "No source records",
    # --- perfil (tabs/perfil.py) ---
    "Importar CV…": "Import CV…",
    "Revertir importación": "Revert import",
    "Buscar por valor o código…": "Search by value or code…",
    "Importa un CV o registra el primer dato con el formulario.":
        "Import a CV or add the first record with the form.",
    "Sin datos de perfil": "No profile data",
    "Nuevo dato de perfil": "New profile record",
    "Identificación": "Identification",
    "Detalle": "Details",
    "Notas": "Notes",
    "Guardar dato": "Save record",
    "Eliminar": "Delete",
    "Limpiar": "Clear",
    "Editar dato de perfil": "Edit profile record",
    "Seleccionar CV": "Select CV",
    # --- vacantes (tabs/vacantes.py) ---
    "Buscar por puesto o empresa…": "Search by position or company…",
    "Solo áreas de mi perfil": "Only areas in my profile",
    "Solo con requisitos obligatorios": "Only with mandatory requirements",
    "Evaluar todo": "Evaluate everything",
    "Ejecutar Paso 5": "Run Step 5",
    "Recalcular": "Recalculate",
    "Pulsa «Recalcular» para calcular el score ATS de los avisos.":
        "Press “Recalculate” to compute the ATS score of the postings.",
    "Sin ranking": "No ranking",
    "Ninguna vacante seleccionada": "No posting selected",
    "Elige una fila para ver el desglose del score ATS.":
        "Select a row to see the ATS score breakdown.",
    "No hay avisos guardados para rankear.":
        "There are no saved postings to rank.",
    "Calculando el ranking ATS…": "Computing the ATS ranking…",
    "{} análisis obsoleto(s)": "{} stale analysis",
    "Evidencia": "Evidence",
    "Evidencia OK": "Evidence OK",
    "Evidencia con fallos": "Evidence with failures",
    "Generada {} ({}) y verificada: {} con frase literal.":
        "Generated {} ({}) and verified: {} with literal wording.",
    ("Generada {}, pero la verificación tiene {} discrepancia(s):\n\n{}"):
        ("Generated {}, but verification found {} discrepancy(ies):\n\n{}"),
    "No se pudo generar la evidencia:\n{}":
        "Could not generate the evidence:\n{}",
    ("Hay {} aviso(s) con análisis obsoleto: la IA ya llenó sus "
     "skills/idiomas, pero el análisis no los integró (así quedan "
     "«sin requisitos» en el matching).\n\n"
     "¿Re-analizarlos ahora antes de evaluar?"):
        ("There are {} posting(s) with a stale analysis: the AI already "
         "filled their skills/languages, but the analysis did not integrate "
         "them (so they end up “without requirements” in the matching).\n\n"
         "Re-analyze them now before evaluating?"),
    ("Se evaluará con los análisis actuales: esos avisos pueden "
     "salir «sin_requisitos» aunque el perfil sí califique."):
        ("It will run with the current analyses: those postings may come out "
         "“without requirements” even if the profile does qualify."),
    # --- scraping (tabs/scraping.py) ---
    "Grupo:": "Group:",
    "Páginas:": "Pages:",
    "Puerto CDP:": "CDP port:",
    "Ejecutar grupo": "Run group",
    "Ejecutar seleccionados": "Run selected",
    ("Solo se barren los sitios activos. «Páginas» es el valor por defecto: "
     "cada sitio usa el suyo de site_config si lo tiene. El puerto CDP solo "
     "afecta a ANE, Indeed, LinkedIn y Elempleo. «Procesar» corre el pipeline "
     "sobre lo que YA está en la base (análisis → IA → re-análisis → Paso 5 "
     "→ evidencia) sin volver a raspar."):
        ("Only active sites are scanned. “Pages” is the default value: each "
         "site uses its own from site_config if it has one. The CDP port "
         "only affects ANE, Indeed, LinkedIn and Elempleo. “Process” runs the "
         "pipeline over what is ALREADY in the database (analysis → AI → "
         "re-analysis → Step 5 → evidence) without scraping again."),
    "Procesar": "Process",
    "Enriquecer IA": "Enrich with AI",
    "seleccioná las que quieras barrer": "pick the ones you want to scan",
    "Listo.": "Done.",
    "Bitácora": "Log",
    # --- cuentas (tabs/cuentas.py) ---
    "Sitios que piden login": "Sites that require login",
    "Quitar sitio": "Remove site",
    "Agregar sitio": "Add site",
    "Credencial": "Credential",
    "la contraseña va al Administrador de Credenciales":
        "the password goes to Windows Credential Manager",
    "Mostrar": "Show",
    "Obligatorio": "Required",
    "Eliminar credencial": "Delete credential",
    "Limpiar formulario": "Clear form",
    # --- configuración (tabs/configuracion.py) ---
    "IA local (servidor llama.cpp)": "Local AI (llama.cpp server)",
    "bajo demanda · O7.3": "on demand · O7.3",
    "Estado: comprobando…": "Status: checking…",
    "Verificar": "Check",
    "Arrancar": "Start",
    "Detener": "Stop",
    ("La UI apaga solo lo que ella arranca; el servidor que ya corría no se "
     "toca. Log: data/ia_server.log."):
        ("The UI only stops what it started itself; a server that was "
         "already running is untouched. Log: data/ia_server.log."),
    ".env del proyecto": "project .env",
    "IA externa (LLM)": "External AI (LLM)",
    ("IA_MAX_LLAMADAS · vacío = sin tope (opt-in)"):
        "IA_MAX_LLAMADAS · empty = no cap (opt-in)",
    ("IA_RPM · vacío = sin rate limit (opt-in)"):
        "IA_RPM · empty = no rate limit (opt-in)",
    "Probar conexión": "Test connection",
    "Listar modelos": "List models",
    "Guardar en .env": "Save to .env",
    ("Variables equivalentes: IA_PROVEEDOR, IA_BASE_URL, IA_MODEL, "
     "IA_API_KEY. Custom (llama.cpp u otro) se configura a mano en Base URL "
     "y Modelo."):
        ("Equivalent variables: IA_PROVEEDOR, IA_BASE_URL, IA_MODEL, "
         "IA_API_KEY. Custom (llama.cpp or another) is set by hand in Base "
         "URL and Model."),
    "Navegador (Brave / CDP)": "Browser (Brave / CDP)",
    "Examinar…": "Browse…",
    "BRAVE_PERFIL · el que tiene la sesión iniciada":
        "BRAVE_PERFIL · the one with the signed-in session",
    "BRAVE_CDP_PORT · 1024-65535 (por defecto 9222)":
        "BRAVE_CDP_PORT · 1024-65535 (default 9222)",
    "Estado: sin comprobar": "Status: not checked",
    "Verificar CDP": "Check CDP",
    "Abrir Brave": "Open Brave",
    "Detener Brave": "Stop Brave",
    ("«Abrir Brave» guarda la configuración en el .env y abre el navegador "
     "con CDP. La UI solo detiene el navegador que ella abrió: el que ya "
     "estaba vivo no se toca. El puerto es el que usan el CLI, los scripts y "
     "la pestaña de Scraping."):
        ("“Open Brave” saves the configuration to the .env and opens the "
         "browser with CDP. The UI only stops the browser it opened: one "
         "that was already running is untouched. The port is the one used "
         "by the CLI, the scripts and the Scraping tab."),
    "Ejecutable de Brave": "Brave executable",
    "Estado: no se encontró Brave (indica la ruta)":
        "Status: Brave not found (set its path)",
    "Sondas de scraping (fuentes del sistema)":
        "Scraping probes (system sources)",
    "Activar seleccionadas": "Enable selected",
    "Pausar seleccionadas": "Pause selected",
    "Activar todas": "Enable all",
    "Pausar todas": "Pause all",
    "⚠ Ningún sitio activo: ninguna corrida podrá ejecutarse.":
        "⚠ No active site: no run can be executed.",
    "Todas las plataformas": "All platforms",
    "Apariencia": "Appearance",
    "ui_config.json · claves «paleta» y «densidad»":
        "ui_config.json · keys «paleta» and «densidad»",
    "Esquema:": "Scheme:",
    "Densidad:": "Density:",
    "  Texto de muestra  ": "  Sample text  ",
    "Aplicar ahora": "Apply now",
    ("Se guarda en ~/.jobpulse_v15/ui_config.json y la interfaz se "
     "reconstruye con el nuevo esquema y la nueva densidad (o se aplicarán "
     "al reiniciar)."):
        ("Saved to ~/.jobpulse_v15/ui_config.json and the interface rebuilds "
         "with the new scheme and density (or they apply on restart)."),
    "Cachés": "Caches",
    "data/usuario/ · qué ocupa y qué se puede borrar":
        "data/usuario/ · what it takes up and what can be deleted",
    ("Borrar la caché de la IA hace que el enriquecimiento vuelva a llamar "
     "al modelo (con IA externa, cuesta dinero). Borrar la de embeddings "
     "solo obliga a re-vectorizar los avisos la próxima vez. Los archivos "
     "ajenos al sistema no se tocan."):
        ("Deleting the AI cache makes enrichment call the model again (with "
         "external AI, that costs money). Deleting the embeddings cache only "
         "forces the postings to be re-vectorized next time. Files that do "
         "not belong to the system are left alone."),
    "O8/O10 · ocultar, nunca borrar": "O8/O10 · hide, never delete",
    "Retención y vigencia": "Retention and validity",
    "Retención:": "Retention:",
    "meses (un aviso más viejo deja de mostrarse)":
        "months (older postings stop being shown)",
    "Solo vacantes vigentes": "Only valid postings",
    "Guardar": "Save",
    ("La retención solo OCULTA los avisos vencidos o publicados fuera de la "
     "ventana: no borra nada de la base. Afecta a las pestañas «Datos "
     "crudos» y «Vacantes»."):
        ("Retention only HIDES expired postings or ones published outside "
         "the window: it deletes nothing from the database. Affects the "
         "“Raw data” and “Postings” tabs."),
    "Diagnóstico": "Diagnostics",
    "integridad · calidad · huecos": "integrity · quality · gaps",
    "Ejecutar diagnóstico": "Run diagnostics",
    "Diagnosticando…": "Running diagnostics…",
    "Exportaciones CSV": "CSV exports",
    "ui_config.json · clave «csv_dir»": "ui_config.json · key «csv_dir»",
    "Usar predeterminado": "Use default",
    ("Directorio inicial de los diálogos «Exportar CSV» (Datos crudos, "
     "Perfil y Vacantes). Vacío = última carpeta que usó Tk."):
        ("Starting directory for the “Export CSV” dialogs (Raw data, "
         "Profile and Postings). Empty = the last folder Tk used."),
    "Estado: apagado": "Status: off",
    "Carpeta para exportar CSV": "Folder to export CSV to",
    # --- nombres visibles de los selectores de Apariencia ---
    "Claro · azul": "Light · blue",
    "Claro · verde": "Light · green",
    "Oscuro": "Dark",
    "Compacta": "Compact",
    "Normal": "Normal",
    "Amplia": "Spacious",
    # --- encabezados de tabla ---
    "Fecha": "Date",
    "Título": "Title",
    "Empresa": "Company",
    "Ubicación (cruda)": "Location (raw)",
    "Idioma": "Language",
    "Idioma:": "Language:",
    "Salario": "Salary",
    "Fuente": "Source",
    "Desc.": "Desc.",
    "Categoría": "Category",
    "Código": "Code",
    "Valor": "Value",
    "Nivel / detalle": "Level / detail",
    "Origen": "Origin",
    "Canónico": "Canonical",
    "Veredicto": "Verdict",
    "Ajuste": "Fit",
    "Banda": "Band",
    "Ajuste técnico": "Technical fit",
    "Faltantes obligatorios": "Missing mandatory requirements",
    "Aplicar": "Apply",
    "Revisar": "Review",
    "No prioritario": "Not a priority",
    "Descartado": "Discarded",
    "Todas las bandas": "All bands",
    "Solo aplicar": "Only apply",
    "Puesto": "Position",
    "Área": "Area",
    "Idiomas": "Languages",
    "Paso 5": "Step 5",
    # --- franjas de métricas (StatTile) ---
    "Avisos": "Postings",
    "Fuerte": "Strong",
    "Ajustable": "Adjustable",
    "Débil": "Weak",
    "Sin datos": "No data",
    "Avisos en vista": "Postings in view",
    "Con descripción": "With description",
    "Con ubicación": "With location",
    "Con salario": "With salary",
    "Con fecha": "With date",
    # --- etiquetas del panel de detalle ---
    "Ubicación": "Location",
    "Ciudad": "City",
    "Provincia": "Province",
    "País": "Country",
    "Condiciones": "Conditions",
    "Modalidad": "Work mode",
    "Tipo de empleo": "Employment type",
    "Idioma del aviso": "Posting language",
    "Publicada": "Published",
    "Visto por última vez": "Last seen",
    "Mínimo": "Minimum",
    "Máximo": "Maximum",
    "Periodo": "Period",
    "Campos derivados": "Derived fields",
    "Estado manual": "Manual status",
    "Duplicado de": "Duplicate of",
    "Requisitos (texto crudo)": "Requirements (raw text)",
    "Descripción (texto crudo)": "Description (raw text)",
    # --- estados vacíos / comunes ---
    "Buscar…": "Search…",
}

# Estado del idioma (una UI por proceso; lo fija `app.crear_app`).
_idioma: str = IDIOMA_DEFECTO


def idioma_actual() -> str:
    """Código del idioma vigente («es» o «en»)."""
    return _idioma


def establecer_idioma(nombre: str | None) -> str:
    """Pone el idioma vigente; un valor desconocido cae al defecto."""
    global _idioma
    codigo = str(nombre or "").strip().lower()
    _idioma = codigo if codigo in IDIOMAS else IDIOMA_DEFECTO
    return _idioma


def t(clave: str, **sustituciones: object) -> str:
    """Traduce `clave` al idioma vigente.

    Sin traducción (o en español) devuelve la MISMA clave: nunca rompe una
    cadena. `sustituciones` aplica `.format()` sobre el resultado, para los
    textos dinámicos (`t("{} de {} activas").format(a, b)`).
    """
    if _idioma == IDIOMA_DEFECTO:
        texto = clave
    else:
        texto = _EN.get(clave, clave)
    if sustituciones:
        try:
            return texto.format(**sustituciones)
        except (KeyError, IndexError, ValueError):
            return texto
    return texto


def catalogo() -> dict[str, str]:
    """Copia del catálogo (para tests y para auditar la cobertura)."""
    return dict(_EN)
