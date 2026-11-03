# -*- coding: utf-8 -*-
"""Pestaña "Configuración": IA, navegador, sondas, apariencia, cachés y CSV.

Siete tarjetas (una Card cada una):

1. **IA local** — estado/arranque/detención del servidor llama.cpp.
   Política O7.3: solo se detiene el servidor que ESTA UI arrancó; uno que
   ya corría (arrancado a mano o por otra ventana) no se toca. El handle
   vive en el módulo (no en la instancia) para sobrevivir a un cambio de
   esquema en caliente.
2. **IA externa** — proveedor LLM → `.env` del proyecto
   (IA_PROVEEDOR / IA_BASE_URL / IA_MODEL / IA_API_KEY + límites opt-in
   IA_MAX_LLAMADAS / IA_RPM; vacío = sin tope).
3. **Navegador (Brave / CDP)** — ruta del ejecutable, perfil con la sesión
   iniciada y puerto CDP → `.env` (BRAVE_BIN / BRAVE_PERFIL /
   BRAVE_CDP_PORT). El puerto deja de estar fijo en 9222: es la misma
   variable que leen el CLI, los scripts y la pestaña de Scraping.
4. **Sondas de scraping** — activa/pausa `source_sites` (la única verdad
   que miran `run_scrapes.py`, `run_full_flow.py` y `Repository.select_sites`).
5. **Apariencia** — esquema de color (`theme.PALETAS`) → `ui_config.json` y
   reconstrucción en caliente vía el servicio `reconstruir_ui`.
6. **Cachés** — qué ocupa `data/usuario/` (caché de la IA y caché de
   embeddings) y botones para limpiarlas (el dominio está en
   `jobpulse_v15.caches`, sin Tk).
7. **Exportaciones CSV** — directorio inicial de los diálogos "Exportar CSV".

Patrones: un solo gestor de geometría por padre; hilos que solo tocan Tk vía
`_programar` (marco.after); ningún color escrito a mano (van de `theme`).
"""
from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Any

from jobpulse_v15.configuration_window import IA_PROVIDERS
from jobpulse_v15.ia_servidor import asegurar_servidor, servidor_arriba
from jobpulse_v15.ui_v2 import configuracion
from jobpulse_v15.ui_v2.data.fuentes import FuentesStore
from jobpulse_v15.ui_v2.dialogs import confirmar
from jobpulse_v15.ui_v2.tabs.base import BaseTab
from jobpulse_v15.ui_v2.theme import NOMBRES_PALETA, PALETA_DEFECTO, paleta_por_nombre
from jobpulse_v15.ui_v2.widgets import Card, FlatButton, ScrollFrame, SectionTitle

TODAS_LAS_PLATAFORMAS = "Todas las plataformas"

# Handle del servidor IA que ESTA UI arrancó (O7.3: el preexistente no se
# toca). Va en el módulo para sobrevivir al reconstruir la app al cambiar el
# esquema de color (la pestaña se destruye; el proceso no).
_HANDLE_SERVIDOR: Any = None

# Handle del Brave que ESTA UI arrancó (misma política que el servidor IA:
# el navegador que ya estaba vivo —el del usuario— no se toca ni se cierra).
_HANDLE_BRAVE: Any = None


class ConfiguracionTab(BaseTab):
    """Configuración del sistema dentro de la UI v2."""

    key = "configuracion"
    title = "Configuración"
    subtitle = "IA, navegador, sondas de scraping, apariencia, cachés y CSV"
    icon = "⚙"

    def __init__(self, context) -> None:
        super().__init__(context)
        self.store: FuentesStore = context.services.setdefault(
            "fuentes_store", FuentesStore(context.repository)
        )
        self._widgets: dict[str, Any] = {}
        self._csv_var = tk.StringVar(value="")
        # Estado de las cachés (medido en disco al abrir la pestaña).
        self._estados_cache: dict[str, Any] = {}
        # Fila de la tarjeta -> clave de caché (para el botón "Limpiar").
        self._cache_claves: dict[int, str] = {1: "ia", 2: "embeddings"}

    # ================================================================
    # Construcción
    # ================================================================
    def build(self, parent: tk.Misc) -> tk.Frame:
        marco = super().build(parent)
        theme = self.theme
        marco.rowconfigure(0, weight=1)
        marco.columnconfigure(0, weight=1)

        scroll = ScrollFrame(marco, theme, background=theme.color("bg"))
        scroll.grid(row=0, column=0, sticky="nsew")
        scroll.inner.columnconfigure(0, weight=1)

        self._card_ia_local(scroll.inner)
        self._card_ia_externa(scroll.inner)
        self._card_navegador(scroll.inner)
        self._card_sondas(scroll.inner)
        self._card_apariencia(scroll.inner)
        self._card_caches(scroll.inner)
        self._card_csv(scroll.inner)

        self._cargar_ia()
        self._cargar_navegador()
        self._cargar_apariencia()
        self._cargar_caches()
        return marco

    # -- tarjeta 1: IA local ----------------------------------------
    def _card_ia_local(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme)
        card.grid(row=0, column=0, sticky="ew", pady=(0, theme.metrics.gap))
        card.body.columnconfigure(0, weight=1)

        SectionTitle(card.body, theme, "IA local (servidor llama.cpp)",
                     hint="bajo demanda · O7.3").grid(
            row=0, column=0, sticky="ew")

        self._widgets["ia_estado"] = tk.Label(
            card.body, text="Estado: comprobando…", bg=theme.color("surface"),
            fg=theme.color("text"), font=theme.font(10, "bold"), anchor="w",
        )
        self._widgets["ia_estado"].grid(row=1, column=0, sticky="ew",
                                        pady=(6, 0))

        base = ""
        try:
            from jobpulse_v15.ia_servidor import _config as _ia_config
            base = _ia_config()[0]
        except Exception:  # noqa: BLE001 - solo para el texto de apoyo
            base = ""
        self._widgets["ia_base"] = tk.Label(
            card.body, text=base or "—", bg=theme.color("surface"),
            fg=theme.color("text_muted"), font=theme.font(9), anchor="w",
        )
        self._widgets["ia_base"].grid(row=2, column=0, sticky="ew")

        botones = tk.Frame(card.body, bg=theme.color("surface"))
        botones.grid(row=3, column=0, sticky="w", pady=(8, 0))
        FlatButton(botones, theme, "Verificar",
                   command=self.verificar_ia_local).pack(side="left")
        self._widgets["ia_arrancar"] = FlatButton(
            botones, theme, "Arrancar", command=self.arrancar_ia_local,
            variant="accent",
        )
        self._widgets["ia_arrancar"].pack(side="left", padx=(8, 0))
        self._widgets["ia_detener"] = FlatButton(
            botones, theme, "Detener", command=self.detener_ia_local,
        )
        self._widgets["ia_detener"].pack(side="left", padx=(8, 0))
        self._widgets["ia_detener"].configure(state="disabled")

        tk.Label(
            card.body,
            text=("La UI apaga solo lo que ella arranca; el servidor que ya "
                  "corría no se toca. Log: data/ia_server.log."),
            bg=theme.color("surface"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w",
        ).grid(row=4, column=0, sticky="ew", pady=(8, 0))

    # -- tarjeta 2: IA externa --------------------------------------
    def _card_ia_externa(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme)
        card.grid(row=1, column=0, sticky="ew", pady=(0, theme.metrics.gap))
        card.body.columnconfigure(0, weight=1)

        SectionTitle(card.body, theme, "IA externa (LLM)",
                     hint=".env del proyecto").grid(
            row=0, column=0, sticky="ew")

        form = tk.Frame(card.body, bg=theme.color("surface"))
        form.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        form.columnconfigure(1, weight=1)

        combo = ttk.Combobox(
            form, values=[p["nombre"] for p in IA_PROVIDERS.values()],
            state="readonly", width=26, font=theme.font(9),
        )
        combo.bind("<<ComboboxSelected>>", lambda _e: self._on_proveedor())
        self._fila_form(form, 0, "Proveedor:", combo)
        self._widgets["ia_proveedor"] = combo

        self._widgets["ia_base_url"] = self._fila_form(
            form, 1, "Base URL:", ttk.Entry(form, font=theme.font(9)))
        self._widgets["ia_model"] = self._fila_form(
            form, 2, "Modelo:", ttk.Entry(form, font=theme.font(9)))

        key_entry = ttk.Entry(form, show="*", font=theme.font(9))
        self._widgets["ia_api_key"] = self._fila_form(
            form, 3, "API key:", key_entry)
        FlatButton(form, theme, "Mostrar",
                   command=self._toggle_key).grid(
            row=3, column=2, sticky="w", padx=(8, 0))

        self._widgets["ia_max"] = self._fila_form(
            form, 4, "Máx. llamadas:", ttk.Entry(form, width=12),
            hint="IA_MAX_LLAMADAS · vacío = sin tope (opt-in)")
        self._widgets["ia_rpm"] = self._fila_form(
            form, 5, "RPM:", ttk.Entry(form, width=12),
            hint="IA_RPM · vacío = sin rate limit (opt-in)")

        botones = tk.Frame(card.body, bg=theme.color("surface"))
        botones.grid(row=2, column=0, sticky="w", pady=(10, 0))
        FlatButton(botones, theme, "Probar conexión",
                   command=self.probar_ia).pack(side="left")
        FlatButton(botones, theme, "Listar modelos",
                   command=self.listar_modelos).pack(side="left", padx=(8, 0))
        FlatButton(botones, theme, "Guardar en .env",
                   command=self.guardar_ia, variant="accent").pack(
            side="left", padx=(8, 0))

        tk.Label(
            card.body,
            text=("Variables equivalentes: IA_PROVEEDOR, IA_BASE_URL, "
                  "IA_MODEL, IA_API_KEY. Custom (llama.cpp u otro) se "
                  "configura a mano en Base URL y Modelo."),
            bg=theme.color("surface"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w",
        ).grid(row=3, column=0, sticky="ew", pady=(8, 0))

    # -- tarjeta 3: navegador (Brave / CDP) --------------------------
    def _card_navegador(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme)
        card.grid(row=2, column=0, sticky="ew", pady=(0, theme.metrics.gap))
        card.body.columnconfigure(0, weight=1)

        SectionTitle(card.body, theme, "Navegador (Brave / CDP)",
                     hint="ANE · Indeed · LinkedIn · Elempleo").grid(
            row=0, column=0, sticky="ew")

        form = tk.Frame(card.body, bg=theme.color("surface"))
        form.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        form.columnconfigure(1, weight=1)

        self._widgets["brave_bin"] = self._fila_form(
            form, 0, "Ejecutable:", ttk.Entry(form, font=theme.font(9)))
        FlatButton(form, theme, "Examinar…",
                   command=self._elegir_brave).grid(
            row=0, column=2, sticky="w", padx=(8, 0))

        perfiles = self._perfiles_brave()
        combo_perfil = ttk.Combobox(
            form, values=perfiles or ["Default"], state="normal", width=22,
            font=theme.font(9),
        )
        self._widgets["brave_perfil"] = self._fila_form(
            form, 1, "Perfil:", combo_perfil,
            hint="BRAVE_PERFIL · el que tiene la sesión iniciada")

        self._widgets["brave_puerto"] = self._fila_form(
            form, 2, "Puerto CDP:", ttk.Entry(form, width=12, font=theme.font(9)),
            hint="BRAVE_CDP_PORT · 1024-65535 (por defecto 9222)")

        self._widgets["brave_estado"] = tk.Label(
            card.body, text="Estado: sin comprobar", bg=theme.color("surface"),
            fg=theme.color("text_muted"), font=theme.font(9), anchor="w",
        )
        self._widgets["brave_estado"].grid(row=2, column=0, sticky="ew",
                                           pady=(8, 0))

        botones = tk.Frame(card.body, bg=theme.color("surface"))
        botones.grid(row=3, column=0, sticky="w", pady=(10, 0))
        FlatButton(botones, theme, "Verificar CDP",
                   command=self.verificar_cdp).pack(side="left")
        self._widgets["brave_abrir"] = FlatButton(
            botones, theme, "Abrir Brave", command=self.abrir_brave,
            variant="accent",
        )
        self._widgets["brave_abrir"].pack(side="left", padx=(8, 0))
        self._widgets["brave_detener"] = FlatButton(
            botones, theme, "Detener Brave", command=self.detener_brave,
        )
        self._widgets["brave_detener"].pack(side="left", padx=(8, 0))
        self._widgets["brave_detener"].configure(state="disabled")
        FlatButton(botones, theme, "Guardar en .env",
                   command=self.guardar_brave).pack(side="left", padx=(8, 0))

        tk.Label(
            card.body,
            text=("«Abrir Brave» guarda la configuración en el .env y abre "
                  "el navegador con CDP. La UI solo detiene el navegador "
                  "que ella abrió: el que ya estaba vivo no se toca. "
                  "El puerto es el que usan el CLI, los scripts y la "
                  "pestaña de Scraping."),
            bg=theme.color("surface"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w", wraplength=760, justify="left",
        ).grid(row=4, column=0, sticky="ew", pady=(8, 0))

    # -- tarjeta 4: sondas de scraping ------------------------------
    def _card_sondas(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme)
        card.grid(row=3, column=0, sticky="ew", pady=(0, theme.metrics.gap))
        card.body.columnconfigure(0, weight=1)

        SectionTitle(card.body, theme,
                     "Sondas de scraping (fuentes del sistema)").grid(
            row=0, column=0, sticky="ew")
        self._widgets["sondas_hint"] = tk.Label(
            card.body, text="", bg=theme.color("surface"),
            fg=theme.color("text_faint"), font=theme.font(8), anchor="e",
        )
        self._widgets["sondas_hint"].grid(row=0, column=1, sticky="e",
                                          padx=(10, 0))

        barra = tk.Frame(card.body, bg=theme.color("surface"))
        barra.grid(row=1, column=0, columnspan=2, sticky="ew",
                   pady=(8, 8))
        plataformas = [TODAS_LAS_PLATAFORMAS] + self.store.plataformas()
        combo = ttk.Combobox(
            barra, values=plataformas, state="readonly", width=24,
            font=theme.font(9),
        )
        combo.current(0)
        combo.bind("<<ComboboxSelected>>", lambda _e: self.refresh())
        combo.pack(side="left")
        self._widgets["sondas_filtro"] = combo

        FlatButton(barra, theme, "Activar seleccionadas",
                   command=self.activar_seleccion).pack(
            side="left", padx=(12, 0))
        FlatButton(barra, theme, "Pausar seleccionadas",
                   command=self.pausar_seleccion).pack(
            side="left", padx=(6, 0))
        FlatButton(barra, theme, "Activar todas", variant="ghost",
                   command=self.activar_todas).pack(
            side="left", padx=(16, 0))
        FlatButton(barra, theme, "Pausar todas", variant="ghost",
                   command=self.pausar_todas).pack(
            side="left", padx=(6, 0))

        marco_tabla = tk.Frame(card.body, bg=theme.color("surface"))
        marco_tabla.grid(row=2, column=0, columnspan=2, sticky="ew")
        marco_tabla.columnconfigure(0, weight=1)

        columnas = ("estado", "plataforma", "tipo", "sitio", "grupos")
        tree = ttk.Treeview(
            marco_tabla, columns=columnas, show="headings",
            selectmode="extended", height=8, style="Flat.Treeview",
        )
        anchos = {"estado": 90, "plataforma": 150, "tipo": 80,
                  "sitio": 360, "grupos": 160}
        for col in columnas:
            tree.heading(col, text=col.upper())
            tree.column(col, width=anchos[col], minwidth=60,
                        stretch=(col == "sitio"))
        tree.grid(row=0, column=0, sticky="ew")
        barra_y = ttk.Scrollbar(
            marco_tabla, orient="vertical", command=tree.yview,
            style="Flat.Vertical.TScrollbar",
        )
        barra_y.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=barra_y.set)
        tree.tag_configure("pausado", foreground=theme.color("text_faint"))
        tree.bind("<Double-1>", self._alternar_doble)
        self._widgets["tabla"] = tree

        aviso = tk.Label(
            card.body,
            text="⚠ Ningún sitio activo: ninguna corrida podrá ejecutarse.",
            bg=theme.color("surface"), fg=theme.color("danger"),
            font=theme.font(9, "bold"), anchor="w",
        )
        aviso.grid(row=3, column=0, columnspan=2, sticky="ew",
                   pady=(8, 0))
        aviso.grid_remove()
        self._widgets["sondas_aviso"] = aviso

    # -- tarjeta 5: apariencia --------------------------------------
    def _card_apariencia(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme)
        card.grid(row=4, column=0, sticky="ew", pady=(0, theme.metrics.gap))
        card.body.columnconfigure(0, weight=1)

        SectionTitle(card.body, theme, "Esquema de color",
                     hint="ui_config.json · clave «paleta»").grid(
            row=0, column=0, sticky="ew")

        fila = tk.Frame(card.body, bg=theme.color("surface"))
        fila.grid(row=1, column=0, sticky="w", pady=(8, 0))
        tk.Label(fila, text="Esquema:", bg=theme.color("surface"),
                 fg=theme.color("text_muted"), font=theme.font(9)).pack(
            side="left")
        combo = ttk.Combobox(
            fila, values=list(NOMBRES_PALETA.values()), state="readonly",
            width=22, font=theme.font(9),
        )
        combo.pack(side="left", padx=(8, 0))
        combo.bind("<<ComboboxSelected>>", lambda _e: self._preview_paleta())
        self._widgets["paleta"] = combo

        preview = tk.Frame(card.body, bg=theme.color("surface"))
        preview.grid(row=2, column=0, sticky="w", pady=(10, 0))
        for nombre in ("bg", "surface", "accent", "sidebar_bg"):
            muestrario = tk.Frame(
                preview, width=52, height=24, bg=theme.color(nombre),
                highlightthickness=1,
                highlightbackground=theme.color("border_strong"),
            )
            muestrario.pack(side="left", padx=(0, 6))
            muestrario.pack_propagate(False)
            self._widgets[f"muestra_{nombre}"] = muestrario
        muestra_texto = tk.Label(
            preview, text="  Texto de muestra  ", bg=theme.color("surface"),
            fg=theme.color("text"), font=theme.font(9),
            highlightthickness=1, highlightbackground=theme.color("border"),
        )
        muestra_texto.pack(side="left", padx=(6, 0))
        self._widgets["muestra_texto"] = muestra_texto

        botones = tk.Frame(card.body, bg=theme.color("surface"))
        botones.grid(row=3, column=0, sticky="w", pady=(10, 0))
        FlatButton(botones, theme, "Aplicar ahora",
                   command=self.aplicar_paleta, variant="accent").pack(
            side="left")

        tk.Label(
            card.body,
            text=("Se guarda en ~/.jobpulse_v15/ui_config.json y la "
                  "interfaz se reconstruye con el nuevo esquema (o se "
                  "aplicará al reiniciar)."),
            bg=theme.color("surface"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w",
        ).grid(row=4, column=0, sticky="ew", pady=(8, 0))

    # -- tarjeta 6: cachés -------------------------------------------
    def _card_caches(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme)
        card.grid(row=5, column=0, sticky="ew", pady=(0, theme.metrics.gap))
        card.body.columnconfigure(0, weight=1)

        SectionTitle(card.body, theme, "Cachés",
                     hint="data/usuario/ · qué ocupa y qué se puede borrar"
                     ).grid(row=0, column=0, sticky="ew")

        # Una fila por caché: nombre, estado y botón de limpieza.
        self._widgets["cache_ia"] = self._fila_cache(
            card.body, 1, "Caché de la IA",
            "las respuestas ya pagadas al LLM (se repiten al enricher)")
        self._widgets["cache_embeddings"] = self._fila_cache(
            card.body, 2, "Caché de embeddings",
            "los vectores del ranking ATS (no cuesta dinero re-vectorizar)")

        botones = tk.Frame(card.body, bg=theme.color("surface"))
        botones.grid(row=3, column=0, sticky="w", pady=(10, 0))
        FlatButton(botones, theme, "Actualizar", variant="ghost",
                   command=self._cargar_caches).pack(side="left")

        tk.Label(
            card.body,
            text=("Borrar la caché de la IA hace que el enriquecimiento "
                  "vuelva a llamar al modelo (con IA externa, cuesta dinero). "
                  "Borrar la de embeddings solo obliga a re-vectorizar los "
                  "avisos la próxima vez. Los archivos ajenos al sistema no "
                  "se tocan."),
            bg=theme.color("surface"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w", wraplength=760, justify="left",
        ).grid(row=4, column=0, sticky="ew", pady=(8, 0))

    def _fila_cache(self, parent: tk.Misc, fila: int, titulo: str,
                    ayuda: str) -> tk.Label:
        """Fila de una caché: título + estado (devuelve la etiqueta)."""
        theme = self.theme
        marco = tk.Frame(parent, bg=theme.color("surface"))
        marco.grid(row=fila, column=0, sticky="ew", pady=(8, 0))
        marco.columnconfigure(0, weight=1)

        texto = tk.Label(
            marco, text=titulo, bg=theme.color("surface"),
            fg=theme.color("text"), font=theme.font(9, "bold"), anchor="w",
        )
        texto.grid(row=0, column=0, sticky="w")
        estado = tk.Label(
            marco, text="…", bg=theme.color("surface"),
            fg=theme.color("text_muted"), font=theme.font(9), anchor="w",
        )
        estado.grid(row=1, column=0, sticky="w")
        tk.Label(
            marco, text=ayuda, bg=theme.color("surface"),
            fg=theme.color("text_faint"), font=theme.font(8), anchor="w",
        ).grid(row=2, column=0, sticky="w")

        boton = FlatButton(marco, theme, "Limpiar", variant="ghost",
                           command=lambda c=fila: self._limpiar_cache(c))
        boton.grid(row=0, column=1, rowspan=3, sticky="e")
        self._widgets[f"cache_boton_{fila}"] = boton
        return estado

    def _cargar_caches(self) -> None:
        """Mide las cachés y las pinta (rápido: solo mira el disco)."""
        try:
            from jobpulse_v15 import caches
        except Exception:  # noqa: BLE001 - si falla, la tarjeta queda muda
            return
        try:
            estados = caches.estado_caches()
        except Exception as exc:  # noqa: BLE001
            for clave in ("cache_ia", "cache_embeddings"):
                etiqueta = self._widgets.get(clave)
                if etiqueta is not None:
                    etiqueta.configure(text=f"No se pudo leer: {exc}")
            return
        self._estados_cache = estados
        for clave, etiqueta_clave in (("ia", "cache_ia"),
                                      ("embeddings", "cache_embeddings")):
            etiqueta = self._widgets.get(etiqueta_clave)
            estado = estados.get(clave)
            if etiqueta is None or estado is None:
                continue
            try:
                etiqueta.configure(
                    text=f"{estado.texto_resumen}  ·  {estado.ruta}",
                    fg=self.theme.color("text_muted"),
                )
            except tk.TclError:
                pass

    def _limpiar_cache(self, fila: int) -> None:
        """Limpia una caché (con confirmación: la de la IA cuesta dinero)."""
        from jobpulse_v15 import caches

        clave = self._cache_claves.get(fila)
        if clave is None:
            return
        estado = getattr(self, "_estados_cache", {}).get(clave)
        if estado is None:
            self._cargar_caches()
            estado = getattr(self, "_estados_cache", {}).get(clave)
        if estado is None:
            return
        if not confirmar(
            self.frame,
            "Limpiar caché",
            f"¿Borrar la {estado.titulo.lower()}?\n\n"
            f"{estado.texto_resumen}\n\n{estado.nota}",
        ):
            return

        def tarea() -> None:
            resultado = caches.limpiar(clave)
            self._programar(lambda: self._tras_limpiar_cache(clave, resultado))

        self._lanzar_hilo(tarea)

    def _tras_limpiar_cache(self, clave: str, resultado) -> None:
        self._cargar_caches()
        if not resultado.ok:
            self._error("No se pudo limpiar la caché", resultado.error)
            return
        self._info(
            "Caché limpiada",
            f"{resultado.archivos_borrados} archivo(s) borrados · "
            f"{resultado.tamano_liberado} liberados.",
        )

    # -- tarjeta 7: exportaciones CSV -------------------------------
    def _card_csv(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme)
        card.grid(row=6, column=0, sticky="ew")
        card.body.columnconfigure(0, weight=1)

        SectionTitle(card.body, theme, "Exportaciones CSV",
                     hint="ui_config.json · clave «csv_dir»").grid(
            row=0, column=0, sticky="ew")

        fila = tk.Frame(card.body, bg=theme.color("surface"))
        fila.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        entry = tk.Entry(
            fila, textvariable=self._csv_var, bd=0, relief="flat",
            bg=theme.color("surface"), fg=theme.color("text"),
            insertbackground=theme.color("text"), font=theme.font(9),
            highlightthickness=1, highlightbackground=theme.color("border_strong"),
        )
        entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        FlatButton(fila, theme, "Examinar…",
                   command=self._elegir_directorio).pack(side="left")
        FlatButton(fila, theme, "Usar predeterminado", variant="ghost",
                   command=self._usar_predeterminado).pack(
            side="left", padx=(6, 0))

        tk.Label(
            card.body,
            text=("Directorio inicial de los diálogos «Exportar CSV» "
                  "(Datos crudos, Perfil y Vacantes). Vacío = última "
                  "carpeta que usó Tk."),
            bg=theme.color("surface"), fg=theme.color("text_faint"),
            font=theme.font(8), anchor="w",
        ).grid(row=2, column=0, sticky="ew", pady=(8, 0))

    # ================================================================
    # Ciclo de vida
    # ================================================================
    def on_show(self) -> None:
        self.refresh()
        self.verificar_ia_local()
        self.verificar_cdp()
        self._cargar_caches()

    def refresh(self) -> None:
        """Recarga las sondas (el resto NO: no pisar ediciones del usuario)."""
        if "tabla" in self._widgets:
            self._refresh_sondas()

    # ================================================================
    # IA local
    # ================================================================
    def verificar_ia_local(self) -> None:
        """Comprueba /health en un hilo (puede tardar hasta 3 s)."""
        estado = self._widgets.get("ia_estado")
        if estado is None:
            return
        try:
            estado.configure(text="Estado: comprobando…")
        except tk.TclError:
            return

        def tarea() -> None:
            base, arriba, error = "", False, ""
            try:
                from jobpulse_v15.ia_servidor import _config
                base = _config()[0]
                arriba = servidor_arriba(timeout=3.0)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
            self._programar(lambda: self._pintar_estado(base, arriba, error))

        self._lanzar_hilo(tarea)

    def _pintar_estado(self, base: str, arriba: bool, error: str) -> None:
        estado = self._widgets.get("ia_estado")
        if estado is None:
            return
        try:
            if error:
                estado.configure(
                    text=f"Estado: no se pudo comprobar — {error}",
                    fg=self.theme.color("danger"),
                )
            elif arriba:
                estado.configure(
                    text=f"Estado: ARRIBA · {base}",
                    fg=self.theme.color("success"),
                )
            else:
                estado.configure(
                    text=f"Estado: apagado · {base}",
                    fg=self.theme.color("text_muted"),
                )
            detener = self._widgets.get("ia_detener")
            if detener is not None:
                detener.configure(
                    state="normal" if _HANDLE_SERVIDOR else "disabled")
        except tk.TclError:
            pass

    def arrancar_ia_local(self) -> None:
        boton = self._widgets.get("ia_arrancar")
        if boton is not None:
            boton.configure(state="disabled")

        def tarea() -> None:
            global _HANDLE_SERVIDOR
            ok, mensaje = False, ""
            try:
                handle = asegurar_servidor(on_log=None)
                if handle is not None:      # None = ya estaba arriba
                    _HANDLE_SERVIDOR = handle
                    mensaje = "Servidor IA arrancado y listo."
                else:
                    mensaje = "El servidor ya estaba arriba."
                ok = True
            except Exception as exc:  # noqa: BLE001
                mensaje = str(exc)
            self._programar(lambda: self._tras_arranque(ok, mensaje))

        self._lanzar_hilo(tarea)

    def _tras_arranque(self, ok: bool, mensaje: str) -> None:
        boton = self._widgets.get("ia_arrancar")
        if boton is not None:
            boton.configure(state="normal")
        if ok:
            self.verificar_ia_local()
        else:
            self._error("No se pudo arrancar la IA local", mensaje)

    def detener_ia_local(self) -> None:
        global _HANDLE_SERVIDOR
        handle = _HANDLE_SERVIDOR
        if handle is None:
            return
        _HANDLE_SERVIDOR = None    # el hilo de abajo solo ejecuta handle.detener()

        def tarea() -> None:
            ok, mensaje = False, ""
            try:
                handle.detener()
                ok, mensaje = True, "Servidor IA detenido."
            except Exception as exc:  # noqa: BLE001
                mensaje = str(exc)
            self._programar(lambda: self._tras_detener(ok, mensaje))

        self._lanzar_hilo(tarea)

    def _tras_detener(self, ok: bool, mensaje: str) -> None:
        self._pintar_estado("", False, "" if ok else mensaje)
        if ok:
            estado = self._widgets.get("ia_estado")
            if estado is not None:
                try:
                    estado.configure(text="Estado: apagado",
                                     fg=self.theme.color("text_muted"))
                except tk.TclError:
                    pass
        else:
            self._error("No se pudo detener la IA local", mensaje)

    # ================================================================
    # IA externa
    # ================================================================
    def _cargar_ia(self) -> None:
        try:
            from dotenv import load_dotenv
            load_dotenv(configuracion.ruta_env())
        except Exception:  # noqa: BLE001 - sin dotenv no hay .env que leer
            pass
        clave = os.getenv("IA_PROVEEDOR", "custom")
        self._widgets["ia_proveedor"].set(
            IA_PROVIDERS.get(clave, IA_PROVIDERS["custom"])["nombre"])
        self._set("ia_base_url",
                  os.getenv("IA_BASE_URL", "http://127.0.0.1:8081/v1"))
        self._set("ia_model", os.getenv("IA_MODEL", "gemma4-e2b-qat"))
        self._set("ia_api_key", os.getenv("IA_API_KEY", "sk-no-key-needed"))
        self._set("ia_max", os.getenv("IA_MAX_LLAMADAS", ""))
        self._set("ia_rpm", os.getenv("IA_RPM", ""))

    def _clave_proveedor(self) -> str:
        """Clave del proveedor elegido (el combo muestra nombres legibles)."""
        visible = self._widgets["ia_proveedor"].get()
        return next(
            (k for k, p in IA_PROVIDERS.items() if p["nombre"] == visible),
            "custom",
        )

    def _on_proveedor(self) -> None:
        preset = IA_PROVIDERS.get(self._clave_proveedor())
        if not preset:
            return
        # Solo aplica presets NO vacíos: "custom" deja lo que hay para
        # que el usuario lo edite a mano (borrar base_url/modelo rompería
        # el .env si guarda sin rellenar).
        if preset["base_url"]:
            self._set("ia_base_url", preset["base_url"])
        if preset["modelo_def"]:
            self._set("ia_model", preset["modelo_def"])

    def _toggle_key(self) -> None:
        entry = self._widgets["ia_api_key"]
        actual = str(entry.cget("show"))
        entry.configure(show="" if actual == "*" else "*")

    def guardar_ia(self) -> None:
        proveedor = self._clave_proveedor()
        base_url = self._get("ia_base_url")
        modelo = self._get("ia_model")
        if not proveedor or not base_url or not modelo:
            self._warn("IA externa incompleta",
                       "Proveedor, Base URL y Modelo son obligatorios "
                       "(para Ollama/LM Studio usa el modelo «auto»).")
            return
        max_llamadas = self._get("ia_max")
        rpm = self._get("ia_rpm")
        for nombre, valor in (("IA_MAX_LLAMADAS", max_llamadas),
                              ("IA_RPM", rpm)):
            if valor and not valor.isdigit():
                self._warn("Límite inválido",
                           f"{nombre} debe ser un número entero "
                           "(o vacío = sin tope).")
                return
        try:
            valores = {
                "IA_PROVEEDOR": proveedor,
                "IA_BASE_URL": base_url,
                "IA_MODEL": modelo,
                "IA_API_KEY": self._get("ia_api_key"),
                # Vacío = sin tope: ia_api trata "" como falsy (opt-in).
                "IA_MAX_LLAMADAS": max_llamadas,
                "IA_RPM": rpm,
            }
            configuracion.guardar_env(valores)
        except OSError as exc:
            self._error("Error al guardar IA (.env)", str(exc))
            return
        # El .env ya no manda hasta el próximo arranque: load_dotenv NO pisa
        # variables ya presentes en os.environ. Se actualizan aquí para que
        # el cambio rija en esta misma sesión.
        for clave, valor in valores.items():
            os.environ[clave] = valor
        self._info("Guardado",
                   "Configuración de IA externa escrita en el .env "
                   "del proyecto (ese archivo nunca se sube al repo).")

    def _config_ia(self) -> dict[str, Any]:
        """Config del cliente IA con lo que hay en el formulario."""
        # El combo muestra nombres legibles; el cliente necesita la CLAVE.
        config: dict[str, Any] = {"proveedor": self._clave_proveedor()}
        for campo, clave in (("base_url", "ia_base_url"),
                             ("modelo", "ia_model"),
                             ("api_key", "ia_api_key")):
            valor = self._get(clave)
            if valor:
                config[campo] = valor
        return config

    def listar_modelos(self) -> None:
        """Lista los modelos que expone el endpoint (GET /models)."""
        config = self._config_ia()
        # "auto" = detección automática: el cliente no exige modelo para listar.
        config["modelo"] = config.get("modelo") or "auto"

        def tarea() -> None:
            import asyncio
            try:
                from jobpulse_v15.ia_api import IAClient

                async def _do() -> list[str]:
                    client = IAClient(dict(config))
                    return await client.listar_modelos()

                modelos = asyncio.run(_do())
                texto = "\n".join(f"- {m}" for m in modelos[:30])
                if len(modelos) > 30:
                    texto += f"\n... y {len(modelos) - 30} más"
                if not texto:
                    texto = "No se encontraron modelos."
                self._programar(
                    lambda: self._info("Modelos disponibles", texto))
            except Exception as exc:  # noqa: BLE001
                self._programar(lambda: self._error("Error", str(exc)))

        self._lanzar_hilo(tarea)

    def probar_ia(self) -> None:
        config = self._config_ia()

        def tarea() -> None:
            import asyncio
            mensaje, es_error = "", False
            try:
                try:
                    from dotenv import load_dotenv
                    load_dotenv(configuracion.ruta_env())
                except Exception:  # noqa: BLE001
                    pass
                from jobpulse_v15.ia_api import IAClient

                async def _do() -> str:
                    client = IAClient(dict(config))
                    resp = await client.chat_json(
                        messages=[
                            {"role": "system",
                             "content": "Responde SOLO JSON."},
                            {"role": "user",
                             "content": 'Di hola en JSON: {"ok": true}'},
                        ],
                        schema={"type": "object",
                                "properties": {"ok": {"type": "boolean"}},
                                "required": ["ok"]},
                        temperature=0.1,
                        max_tokens=50,
                        use_cache=False,  # probar la conexión DE verdad
                    )
                    return str(resp)

                mensaje, es_error = asyncio.run(_do()), False
            except Exception as exc:  # noqa: BLE001
                mensaje, es_error = str(exc), True
            if es_error:
                self._programar(
                    lambda: self._error("Error de conexión", mensaje))
            else:
                self._programar(
                    lambda: self._info("Conexión OK",
                                       f"Respuesta: {mensaje}"))

        self._lanzar_hilo(tarea)

    # ================================================================
    # Navegador (Brave / CDP)
    # ================================================================
    def _perfiles_brave(self) -> list[str]:
        """Perfiles de Brave detectados en el disco (para el desplegable)."""
        try:
            from jobpulse_v15.browser_manager import perfiles_disponibles

            return perfiles_disponibles()
        except Exception:  # noqa: BLE001 - solo es ayuda visual
            return []

    def _cargar_navegador(self) -> None:
        """Puebla el formulario con lo que hay en el `.env` / entorno."""
        self._set("brave_bin",
                  configuracion.valor_env(configuracion.CLAVE_BRAVE_BIN))
        self._set("brave_perfil",
                  configuracion.valor_env(configuracion.CLAVE_BRAVE_PERFIL,
                                          "Default"))
        self._set("brave_puerto",
                  str(configuracion.puerto_cdp()))
        # Si no hay ruta configurada, se muestra la detectada (información,
        # no se escribe: el .env queda como está).
        if not self._get("brave_bin"):
            try:
                from jobpulse_v15.browser_manager import detectar_brave

                detectada = detectar_brave()
            except Exception:  # noqa: BLE001
                detectada = None
            if detectada:
                self._widgets["brave_estado"].configure(
                    text=f"Estado: Brave detectado en {detectada}")
            else:
                self._widgets["brave_estado"].configure(
                    text="Estado: no se encontró Brave (indica la ruta)")

    def _puerto_brave(self) -> int | None:
        """Puerto del formulario (None si no es válido)."""
        texto = self._get("brave_puerto")
        if not texto:
            return None
        try:
            puerto = int(texto)
        except ValueError:
            return None
        return puerto if 1024 <= puerto <= 65535 else None

    def _estado_brave(self, texto: str, color: str | None = None) -> None:
        etiqueta = self._widgets.get("brave_estado")
        if etiqueta is None:
            return
        try:
            etiqueta.configure(
                text=texto,
                fg=color or self.theme.color("text_muted"),
            )
        except tk.TclError:
            pass

    def _elegir_brave(self) -> None:
        inicial = self._get("brave_bin")
        kwargs: dict[str, Any] = {}
        if inicial and Path(inicial).exists():
            kwargs["initialdir"] = str(Path(inicial).parent)
        ruta = filedialog.askopenfilename(
            title="Ejecutable de Brave", parent=self._raiz(),
            filetypes=[("Ejecutables", "*.exe"), ("Todos", "*.*")], **kwargs,
        )
        if ruta:
            self._set("brave_bin", ruta)

    def guardar_brave(self) -> None:
        """Guarda la configuración del navegador en el `.env`."""
        puerto = self._puerto_brave()
        if puerto is None:
            self._warn("Puerto CDP inválido",
                       "El puerto debe ser un número entre 1024 y 65535 "
                       f"(por defecto {configuracion.PUERTO_CDP_DEFECTO}).")
            return
        try:
            valores = configuracion.guardar_navegador(
                self._get("brave_bin"), self._get("brave_perfil"), puerto)
        except OSError as exc:
            self._error("Error al guardar navegador (.env)", str(exc))
            return
        self._info(
            "Navegador guardado",
            "Configuración escrita en el .env del proyecto:\n"
            f"BRAVE_BIN={valores[configuracion.CLAVE_BRAVE_BIN] or '(detección automática)'}\n"
            f"BRAVE_PERFIL={valores[configuracion.CLAVE_BRAVE_PERFIL] or '(Default)'}\n"
            f"BRAVE_CDP_PORT={valores[configuracion.CLAVE_BRAVE_CDP_PORT]}\n\n"
            "Ese archivo nunca se sube al repo.",
        )

    def verificar_cdp(self) -> None:
        """Comprueba si hay un navegador escuchando en el puerto CDP."""
        puerto = self._puerto_brave() or configuracion.puerto_cdp()
        self._estado_brave(f"Estado: comprobando el puerto {puerto}…")

        def tarea() -> None:
            try:
                from jobpulse_v15.browser_manager import cdp_vivo

                vivo = cdp_vivo(puerto)
            except Exception as exc:  # noqa: BLE001
                self._programar(
                    lambda: self._estado_brave(
                        f"Estado: no se pudo comprobar — {exc}",
                        self.theme.color("danger")))
                return
            self._programar(lambda: self._pintar_cdp(vivo, puerto))

        self._lanzar_hilo(tarea)

    def _pintar_cdp(self, vivo: bool, puerto: int) -> None:
        if vivo:
            self._estado_brave(
                f"Estado: hay un navegador con CDP en el puerto {puerto}",
                self.theme.color("success"))
        else:
            self._estado_brave(
                f"Estado: no hay navegador con CDP en el puerto {puerto}",
                self.theme.color("text_muted"))

    def abrir_brave(self) -> None:
        """Guarda la configuración y abre Brave con CDP (si no había uno)."""
        puerto = self._puerto_brave()
        if puerto is None:
            self._warn("Puerto CDP inválido",
                       "El puerto debe ser un número entre 1024 y 65535.")
            return
        try:
            configuracion.guardar_navegador(
                self._get("brave_bin"), self._get("brave_perfil"), puerto)
        except OSError as exc:
            self._error("Error al guardar navegador (.env)", str(exc))
            return
        self._estado_brave(f"Estado: abriendo Brave con CDP en {puerto}…")

        def tarea() -> None:
            global _HANDLE_BRAVE
            mensaje, error = "", ""
            try:
                from jobpulse_v15.browser_manager import asegurar_brave

                manager = asegurar_brave(puerto)
                if manager is None:
                    mensaje = (f"Ya había un navegador con CDP en el puerto "
                               f"{puerto}: no se tocó.")
                else:
                    _HANDLE_BRAVE = manager
                    mensaje = (f"Brave abierto por la UI con CDP en el "
                               f"puerto {puerto}.")
            except Exception as exc:  # noqa: BLE001
                error = f"{type(exc).__name__}: {exc}"
            self._programar(
                lambda: self._tras_abrir_brave(mensaje, error, puerto))

        self._lanzar_hilo(tarea)

    def _tras_abrir_brave(self, mensaje: str, error: str, puerto: int) -> None:
        if error:
            self._estado_brave(f"Estado: no se pudo abrir Brave — {error}",
                               self.theme.color("danger"))
            self._error("Error al abrir Brave", error)
            return
        self._estado_brave(f"Estado: {mensaje}", self.theme.color("success"))
        detener = self._widgets.get("brave_detener")
        if detener is not None:
            try:
                detener.configure(
                    state="normal" if _HANDLE_BRAVE is not None else "disabled")
            except tk.TclError:
                pass

    def detener_brave(self) -> None:
        """Detiene SOLO el Brave que abrió esta UI (política O7.3)."""
        global _HANDLE_BRAVE
        manager = _HANDLE_BRAVE
        if manager is None:
            self._info("Brave", "No hay ningún navegador abierto por esta UI.")
            return
        _HANDLE_BRAVE = None

        def tarea() -> None:
            ok, mensaje = False, ""
            try:
                manager.stop_brave_sync()
                ok, mensaje = True, "Brave detenido."
            except Exception as exc:  # noqa: BLE001
                mensaje = str(exc)
            self._programar(lambda: self._tras_detener_brave(ok, mensaje))

        self._lanzar_hilo(tarea)

    def _tras_detener_brave(self, ok: bool, mensaje: str) -> None:
        if ok:
            self._estado_brave("Estado: navegador detenido")
        else:
            self._estado_brave(f"Estado: no se pudo detener — {mensaje}",
                               self.theme.color("danger"))
        detener = self._widgets.get("brave_detener")
        if detener is not None:
            try:
                detener.configure(state="disabled")
            except tk.TclError:
                pass

    # ================================================================
    # Sondas de scraping
    # ================================================================
    def _refresh_sondas(self) -> None:
        tree: ttk.Treeview = self._widgets["tabla"]
        for iid in tree.get_children():
            tree.delete(iid)
        filas = self.store.sitios()
        filtro = self._widgets["sondas_filtro"].get()
        if filtro and filtro != TODAS_LAS_PLATAFORMAS:
            filas = [f for f in filas if f.plataforma == filtro]
        for fila in filas:
            estado = "Activo" if fila.activo else "Pausado"
            if fila.revision:
                estado += " ⚠"
            tree.insert(
                "", "end", iid=fila.site_id,
                values=(estado, fila.plataforma, fila.tipo, fila.nombre,
                        fila.grupos),
                tags=() if fila.activo else ("pausado",),
            )
        activos, total = self.store.conteo()
        hint = self._widgets.get("sondas_hint")
        if hint is not None:
            hint.configure(text=f"{activos} de {total} activas")
        aviso = self._widgets.get("sondas_aviso")
        if aviso is not None:
            try:
                if activos == 0 and total > 0:
                    aviso.grid()
                else:
                    aviso.grid_remove()
            except tk.TclError:
                pass

    def _visibles(self) -> list[str]:
        return list(self._widgets["tabla"].get_children())

    def _seleccion(self) -> list[str]:
        return list(self._widgets["tabla"].selection())

    def activar_seleccion(self) -> None:
        self._alternar(True)

    def pausar_seleccion(self) -> None:
        self._alternar(False)

    def _alternar(self, activo: bool) -> None:
        ids = self._seleccion()
        if not ids:
            self._info("Sondas de scraping",
                       "Selecciona uno o más sitios en la tabla primero.")
            return
        self.store.alternar(ids, activo)
        self.refresh()

    def activar_todas(self) -> None:
        ids = self._visibles()
        if not ids:
            return
        self.store.alternar(ids, True)
        self.refresh()

    def pausar_todas(self) -> None:
        ids = self._visibles()
        if not ids:
            return
        if not confirmar(
            self.frame,
            "Pausar todas",
            f"Se pausarán {len(ids)} sonda(s) visibles. Ninguna corrida "
            "las incluirá hasta que las reactives.",
        ):
            return
        self.store.alternar(ids, False)
        self.refresh()

    def _alternar_doble(self, _event: tk.Event) -> None:
        ids = self._seleccion()
        if not ids:
            return
        estado_actual = next(
            (f.activo for f in self.store.sitios() if f.site_id == ids[0]),
            True,
        )
        self.store.alternar(ids, not estado_actual)
        self.refresh()

    # ================================================================
    # Apariencia
    # ================================================================
    def _cargar_apariencia(self) -> None:
        clave = configuracion.paleta_actual() or PALETA_DEFECTO
        if clave not in NOMBRES_PALETA:
            clave = PALETA_DEFECTO
        self._widgets["paleta"].set(NOMBRES_PALETA[clave])
        self._preview_paleta()

    def _clave_paleta_elegida(self) -> str:
        visible = self._widgets["paleta"].get()
        return next(
            (k for k, v in NOMBRES_PALETA.items() if v == visible),
            PALETA_DEFECTO,
        )

    def _preview_paleta(self) -> None:
        paleta = paleta_por_nombre(self._clave_paleta_elegida())
        for nombre in ("bg", "surface", "accent", "sidebar_bg"):
            self._widgets[f"muestra_{nombre}"].configure(
                bg=getattr(paleta, nombre))
        texto = self._widgets["muestra_texto"]
        texto.configure(bg=paleta.surface, fg=paleta.text)

    def aplicar_paleta(self) -> None:
        clave = self._clave_paleta_elegida()
        configuracion.guardar({configuracion.CLAVE_PALETA: clave})
        servicio = self.context.services.get("reconstruir_ui")
        if servicio is None:
            self._info("Esquema guardado",
                       "Se aplicará la próxima vez que abras la UI v2.")
            return
        # after(1): este callback termina ANTES de destruir los widgets.
        try:
            self.frame.after(1, lambda: servicio(clave))
        except tk.TclError:
            pass

    # ================================================================
    # Exportaciones CSV
    # ================================================================
    def _elegir_directorio(self) -> None:
        actual = self._csv_var.get().strip()
        kwargs: dict[str, Any] = {}
        if actual and Path(actual).is_dir():
            kwargs["initialdir"] = actual
        ruta = filedialog.askdirectory(
            title="Carpeta para exportar CSV", parent=self.frame, **kwargs)
        if not ruta:
            return
        self._csv_var.set(ruta)
        self._guardar_csv_dir(ruta)

    def _usar_predeterminado(self) -> None:
        self._csv_var.set("")
        self._guardar_csv_dir("")

    def _guardar_csv_dir(self, valor: str) -> None:
        configuracion.guardar({configuracion.CLAVE_CSV_DIR: valor})

    # ================================================================
    # Utilidades (hilos, diálogos, formulario)
    # ================================================================
    def _raiz(self) -> tk.Misc | None:
        if self.frame is None:
            return None
        try:
            return self.frame.winfo_toplevel()
        except tk.TclError:
            return None

    def _info(self, titulo: str, mensaje: str) -> None:
        try:
            messagebox.showinfo(titulo, mensaje, parent=self._raiz())
        except tk.TclError:
            pass

    def _warn(self, titulo: str, mensaje: str) -> None:
        try:
            messagebox.showwarning(titulo, mensaje, parent=self._raiz())
        except tk.TclError:
            pass

    def _error(self, titulo: str, mensaje: str) -> None:
        try:
            messagebox.showerror(titulo, mensaje, parent=self._raiz())
        except tk.TclError:
            pass

    def _fila_form(self, form: tk.Frame, fila: int, etiqueta: str,
                   widget: tk.Widget, hint: str | None = None) -> tk.Widget:
        """Fila etiqueta/entrada (+ hint opcional) de un formulario grid."""
        theme = self.theme
        tk.Label(
            form, text=etiqueta, bg=theme.color("surface"),
            fg=theme.color("text_muted"), font=theme.font(9), anchor="w",
        ).grid(row=fila, column=0, sticky="w", pady=3, padx=(0, 10))
        widget.grid(row=fila, column=1, sticky="ew", pady=3)
        if hint:
            tk.Label(
                form, text=hint, bg=theme.color("surface"),
                fg=theme.color("text_faint"), font=theme.font(8), anchor="w",
            ).grid(row=fila, column=2, sticky="w", padx=(8, 0))
        return widget

    def _set(self, clave: str, valor: str) -> None:
        widget = self._widgets[clave]
        widget.delete(0, "end")
        if valor:
            widget.insert(0, valor)

    def _get(self, clave: str) -> str:
        return str(self._widgets[clave].get() or "").strip()
