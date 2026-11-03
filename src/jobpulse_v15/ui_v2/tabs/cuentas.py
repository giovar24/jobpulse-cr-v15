# -*- coding: utf-8 -*-
"""Pestaña "Cuentas": las credenciales de los sitios que piden login.

Es la versión plana (y sin Toplevel) de la pestaña "Credenciales / Login" de
la UI clásica:

- **LA LISTA** (`credenciales.lista_sitios_login()`): ANE, Indeed, LinkedIn y
  todo lo que los proveedores detectaron en vivo (login-wall), con su estado
  (obligatorio, auto-login, pendiente, si ya hay credencial).
- **Formulario**: usuario, contraseña, método SSO, URL y notas. Guardar
  escribe los metadatos en `data/empresas/credenciales.json` y la contraseña
  en el **Administrador de Credenciales de Windows** (keyring).

REGLA DE ORO: la contraseña **nunca** se lee ni se muestra. El campo arranca
vacío y vacío significa "conserva la que ya está guardada" (así se editan
los metadatos sin re-teclear la clave).

Patrones: un solo gestor de geometría por padre; nada de Tk desde hilos
(aquí todo es síncrono y rápido: son archivos JSON locales).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from jobpulse_v15.ui_v2.data.cuentas import CuentasStore, SitioCuenta
from jobpulse_v15.ui_v2.tabs.base import BaseTab
from jobpulse_v15.ui_v2.widgets import Card, FlatButton, SectionTitle

SSO_OPCIONES = ("", "google")
GRUPOS = ("directos", "boards", "estatales")


class CuentasTab(BaseTab):
    """Gestiona las cuentas de login de las fuentes."""

    key = "cuentas"
    title = "Cuentas"
    subtitle = "Credenciales de los sitios que piden inicio de sesión"
    icon = "🔑"

    def __init__(self, context) -> None:
        super().__init__(context)
        self.store: CuentasStore = context.services.setdefault(
            "cuentas_store", CuentasStore()
        )
        self._widgets: dict[str, Any] = {}
        self._sitios: dict[str, SitioCuenta] = {}

    # ================================================================
    # Construcción
    # ================================================================
    def build(self, parent: tk.Misc) -> tk.Frame:
        marco = super().build(parent)
        theme = self.theme
        marco.rowconfigure(1, weight=1)
        marco.columnconfigure(0, weight=1)

        self._card_métricas(marco)
        self._card_lista(marco)
        self._card_formulario(marco)
        self.refresh()
        return marco

    # -- métricas ---------------------------------------------------
    def _card_métricas(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme, padding=theme.metrics.pad // 2)
        card.grid(row=0, column=0, sticky="ew", padx=theme.metrics.pad,
                  pady=(theme.metrics.pad, 0))
        fila = tk.Frame(card.body, bg=theme.color("surface"))
        fila.pack(fill="x")
        for clave, etiqueta in (("total", "Sitios"),
                                ("obligatorios", "Obligatorios"),
                                ("con_credencial", "Con credencial"),
                                ("pendientes", "Pendientes"),
                                ("auto_login", "Auto-login")):
            marco = tk.Frame(fila, bg=theme.color("surface"))
            marco.pack(side="left", padx=(0, 24))
            valor = tk.Label(marco, text="0", bg=theme.color("surface"),
                             fg=theme.color("text"), font=theme.font(13, "bold"))
            valor.pack(anchor="w")
            tk.Label(marco, text=etiqueta, bg=theme.color("surface"),
                     fg=theme.color("text_faint"), font=theme.font(8)).pack(anchor="w")
            self._widgets[f"resumen_{clave}"] = valor

    # -- lista ------------------------------------------------------
    def _card_lista(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme, padding=theme.metrics.pad // 2)
        card.grid(row=1, column=0, sticky="nsew", padx=theme.metrics.pad,
                  pady=(theme.metrics.gap // 2, 0))
        card.body.columnconfigure(0, weight=1)
        card.body.rowconfigure(1, weight=1)

        barra = tk.Frame(card.body, bg=theme.color("surface"))
        barra.grid(row=0, column=0, sticky="ew")
        SectionTitle(barra, theme, "Sitios que piden login").pack(side="left")
        botones = tk.Frame(barra, bg=theme.color("surface"))
        botones.pack(side="right")
        FlatButton(botones, theme, "Actualizar",
                   command=self.refresh).pack(side="left")
        FlatButton(botones, theme, "Quitar sitio", variant="ghost",
                   command=self.quitar_sitio).pack(side="left", padx=(6, 0))
        FlatButton(botones, theme, "Agregar sitio",
                   command=self.agregar_sitio).pack(side="left", padx=(6, 0))

        marco_tabla = tk.Frame(card.body, bg=theme.color("surface"))
        marco_tabla.grid(row=1, column=0, sticky="nsew", pady=(6, 0))
        marco_tabla.columnconfigure(0, weight=1)
        marco_tabla.rowconfigure(0, weight=1)

        columnas = ("empresa", "grupo", "acceso", "usuario", "estado", "auto")
        tree = ttk.Treeview(
            marco_tabla, columns=columnas, show="headings", selectmode="browse",
            style="Flat.Treeview",
        )
        anchos = {"empresa": 170, "grupo": 150, "acceso": 110, "usuario": 190,
                  "estado": 140, "auto": 70}
        for col in columnas:
            tree.heading(col, text=col.upper())
            tree.column(col, width=anchos[col], minwidth=60,
                        stretch=(col in ("empresa", "usuario")))
        tree.grid(row=0, column=0, sticky="nsew")
        barra_y = ttk.Scrollbar(marco_tabla, orient="vertical", command=tree.yview,
                                style="Flat.Vertical.TScrollbar")
        barra_y.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=barra_y.set)
        tree.tag_configure("sin_credencial", foreground=theme.color("text_faint"))
        tree.bind("<<TreeviewSelect>>", lambda _e: self._seleccion_cambiada())
        self._widgets["tabla"] = tree

        self._widgets["detalle"] = tk.Label(
            card.body, text="", bg=theme.color("surface"),
            fg=theme.color("text_faint"), font=theme.font(8), anchor="w",
            justify="left", wraplength=900,
        )
        self._widgets["detalle"].grid(row=2, column=0, sticky="ew", pady=(6, 0))

    # -- formulario -------------------------------------------------
    def _card_formulario(self, parent: tk.Misc) -> None:
        theme = self.theme
        card = Card(parent, theme, padding=theme.metrics.pad // 2)
        card.grid(row=2, column=0, sticky="ew", padx=theme.metrics.pad,
                  pady=(theme.metrics.gap // 2, theme.metrics.pad))
        card.body.columnconfigure(0, weight=1)

        SectionTitle(card.body, theme, "Credencial",
                     hint="la contraseña va al Administrador de Credenciales").grid(
            row=0, column=0, sticky="ew")

        form = tk.Frame(card.body, bg=theme.color("surface"))
        form.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        self._widgets["empresa"] = ttk.Entry(form, font=theme.font(9))
        self._fila(form, 0, 0, "Sitio:", self._widgets["empresa"])
        self._widgets["usuario"] = ttk.Entry(form, font=theme.font(9))
        self._fila(form, 0, 2, "Usuario / email:", self._widgets["usuario"])

        clave = ttk.Entry(form, show="*", font=theme.font(9))
        self._widgets["password"] = clave
        self._fila(form, 1, 0, "Contraseña:", clave)
        FlatButton(form, theme, "Mostrar", command=self._toggle_password).grid(
            row=1, column=1, sticky="e", padx=(8, 0))

        combo_sso = ttk.Combobox(form, values=list(SSO_OPCIONES), state="readonly",
                                 width=14, font=theme.font(9))
        self._widgets["sso"] = combo_sso
        self._fila(form, 1, 2, "Método SSO:", combo_sso)

        self._widgets["url"] = ttk.Entry(form, font=theme.font(9))
        self._fila(form, 2, 0, "URL de login:", self._widgets["url"])

        self._widgets["nota"] = ttk.Entry(form, font=theme.font(9))
        self._fila(form, 2, 2, "Nota:", self._widgets["nota"])

        self._widgets["auto_login"] = tk.BooleanVar(value=True)
        self._widgets["obligatorio"] = tk.BooleanVar(value=False)
        checks = tk.Frame(form, bg=theme.color("surface"))
        checks.grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))
        ttk.Checkbutton(checks, text="Auto-login", variable=self._widgets["auto_login"]).pack(
            side="left")
        ttk.Checkbutton(checks, text="Obligatorio",
                        variable=self._widgets["obligatorio"]).pack(
            side="left", padx=(16, 0))

        botones = tk.Frame(card.body, bg=theme.color("surface"))
        botones.grid(row=2, column=0, sticky="w", pady=(10, 0))
        FlatButton(botones, theme, "Guardar", command=self.guardar,
                   variant="accent").pack(side="left")
        FlatButton(botones, theme, "Eliminar credencial",
                   command=self.eliminar).pack(side="left", padx=(8, 0))
        FlatButton(botones, theme, "Limpiar formulario", variant="ghost",
                   command=self.limpiar_formulario).pack(side="left", padx=(8, 0))

        self._widgets["estado"] = tk.Label(
            card.body, text="", bg=theme.color("surface"),
            fg=theme.color("text_muted"), font=theme.font(9), anchor="w",
        )
        self._widgets["estado"].grid(row=3, column=0, sticky="ew", pady=(8, 0))

    def _fila(self, form: tk.Frame, fila: int, columna: int, etiqueta: str,
              widget: tk.Widget) -> None:
        """Etiqueta + widget en la fila/columna indicada."""
        theme = self.theme
        tk.Label(
            form, text=etiqueta, bg=theme.color("surface"),
            fg=theme.color("text_muted"), font=theme.font(9), anchor="w",
        ).grid(row=fila, column=columna, sticky="w", pady=3,
               padx=(0 if columna in (0, 2) else 10, 10))
        widget.grid(row=fila, column=columna + 1, sticky="ew", pady=3)

    # ================================================================
    # Datos
    # ================================================================
    def on_show(self) -> None:
        self.refresh()

    def refresh(self) -> None:
        """Recarga la lista de sitios y sus estados."""
        if "tabla" not in self._widgets:
            return
        sitios = self.store.sitios()
        self._sitios = {s.empresa: s for s in sitios}
        tree: ttk.Treeview = self._widgets["tabla"]
        seleccion = set(tree.selection())
        for iid in tree.get_children():
            tree.delete(iid)
        for sitio in sitios:
            tree.insert(
                "", "end", iid=sitio.empresa,
                values=(sitio.empresa, sitio.grupo_label or sitio.grupo,
                        sitio.acceso or "—", sitio.usuario or "—",
                        sitio.estado, "Sí" if sitio.auto_login else "No"),
                tags=() if sitio.tiene_credencial else ("sin_credencial",),
            )
        if seleccion:
            vivos = [i for i in seleccion if tree.exists(i)]
            if vivos:
                tree.selection_set(*vivos)
        self._pintar_resumen()
        self._pintar_detalle()

    def _pintar_resumen(self) -> None:
        datos = self.store.resumen()
        for clave, valor in datos.items():
            etiqueta = self._widgets.get(f"resumen_{clave}")
            if etiqueta is not None:
                try:
                    etiqueta.configure(text=str(valor))
                except tk.TclError:
                    pass

    def _pintar_detalle(self) -> None:
        """Línea de detalle del sitio seleccionado (motivo / almacén / URL)."""
        etiqueta = self._widgets.get("detalle")
        if etiqueta is None:
            return
        tree: ttk.Treeview = self._widgets["tabla"]
        seleccion = tree.selection()
        sitio = self._sitios.get(seleccion[0]) if seleccion else None
        if sitio is None:
            etiqueta.configure(text="")
            return
        partes = [f"{sitio.empresa} · {sitio.grupo_label or sitio.grupo}"]
        if sitio.almacen:
            partes.append(f"contraseña en: {sitio.almacen}")
        if sitio.url:
            partes.append(sitio.url)
        if sitio.pendiente:
            partes.append(f"pendiente: {sitio.pendiente}")
        elif sitio.motivo:
            partes.append(sitio.motivo[:200])
        try:
            etiqueta.configure(text=" · ".join(partes))
        except tk.TclError:
            pass

    # ================================================================
    # Formulario
    # ================================================================
    def _toggle_password(self) -> None:
        entry = self._widgets["password"]
        actual = str(entry.cget("show"))
        entry.configure(show="" if actual == "*" else "*")

    def _seleccion_cambiada(self) -> None:
        tree: ttk.Treeview = self._widgets["tabla"]
        seleccion = tree.selection()
        if not seleccion:
            return
        sitio = self._sitios.get(seleccion[0])
        if sitio is None:
            return
        self._widgets["empresa"].delete(0, "end")
        self._widgets["empresa"].insert(0, sitio.empresa)
        self._widgets["usuario"].delete(0, "end")
        if sitio.usuario:
            self._widgets["usuario"].insert(0, sitio.usuario)
        self._widgets["url"].delete(0, "end")
        if sitio.url:
            self._widgets["url"].insert(0, sitio.url)
        self._widgets["sso"].set(sitio.sso)
        self._widgets["auto_login"].set(sitio.auto_login)
        self._widgets["obligatorio"].set(sitio.obligatorio)
        # La contraseña NUNCA se carga en el campo: vacío = se conserva la
        # que ya está guardada.
        self._widgets["password"].delete(0, "end")
        self._estado(
            f"Credencial de {sitio.empresa}: "
            + ("hay clave guardada (no se muestra)."
               if sitio.tiene_credencial else "sin clave guardada."),
            )
        self._pintar_detalle()

    def _estado(self, texto: str) -> None:
        etiqueta = self._widgets.get("estado")
        if etiqueta is not None:
            try:
                etiqueta.configure(text=texto)
            except tk.TclError:
                pass

    def limpiar_formulario(self) -> None:
        for clave in ("empresa", "usuario", "password", "url", "nota"):
            widget = self._widgets[clave]
            widget.delete(0, "end")
        self._widgets["sso"].set("")
        self._widgets["auto_login"].set(True)
        self._widgets["obligatorio"].set(False)
        tree: ttk.Treeview = self._widgets["tabla"]
        tree.selection_remove(tree.selection())
        self._estado("Formulario limpio.")

    def guardar(self) -> None:
        """Guarda la credencial del sitio del formulario."""
        empresa = self._get("empresa")
        if not empresa:
            self._estado("Indica el sitio (empresa) de la cuenta.")
            return
        password = self._get("password")
        try:
            self.store.guardar(
                empresa=empresa,
                usuario=self._get("usuario"),
                password=password,
                url=self._get("url"),
                auto_login=bool(self._widgets["auto_login"].get()),
                nota=self._get("nota"),
                sso=self._get("sso"),
                obligatorio=bool(self._widgets["obligatorio"].get()),
            )
        except Exception as exc:  # noqa: BLE001 - el error va a la etiqueta
            self._estado(f"No se pudo guardar: {exc}")
            return
        self.refresh()
        self._estado(
            f"Credencial de {empresa} guardada"
            + ("" if password else " (se conservó la contraseña anterior).")
        )

    def eliminar(self) -> None:
        """Borra la credencial del sitio seleccionado (no el sitio de la lista)."""
        empresa = self._get("empresa")
        if not empresa:
            self._estado("Selecciona un sitio para eliminar su credencial.")
            return
        try:
            borrada = self.store.borrar(empresa)
        except Exception as exc:  # noqa: BLE001
            self._estado(f"No se pudo eliminar: {exc}")
            return
        self.refresh()
        self._estado("Credencial eliminada." if borrada else
                     "Ese sitio no tenía credencial guardada.")

    def agregar_sitio(self) -> None:
        """Da de alta un sitio nuevo: se pide el nombre y la URL."""
        from jobpulse_v15.ui_v2.dialogs import pedir_texto

        empresa = pedir_texto(self.frame, "Agregar sitio",
                              "Nombre del sitio (empresa):")
        if not empresa:
            return
        url = pedir_texto(self.frame, "Agregar sitio",
                          f"URL de login de {empresa} (opcional):") or ""
        try:
            self.store.agregar(empresa, url=url)
        except Exception as exc:  # noqa: BLE001
            self._estado(f"No se pudo agregar: {exc}")
            return
        self.refresh()
        self._estado(f"{empresa} agregado a la lista de sitios con login.")

    def quitar_sitio(self) -> None:
        """Quita el sitio manual seleccionado de la lista (los seeds no)."""
        tree: ttk.Treeview = self._widgets["tabla"]
        seleccion = tree.selection()
        if not seleccion:
            self._estado("Selecciona un sitio en la tabla.")
            return
        empresa = seleccion[0]
        sitio = self._sitios.get(empresa)
        if sitio is not None and sitio.detectado == "seed":
            self._estado(
                f"{empresa} es un sitio base del sistema: no se puede quitar.")
            return
        try:
            self.store.quitar(empresa)
        except Exception as exc:  # noqa: BLE001
            self._estado(f"No se pudo quitar: {exc}")
            return
        self.refresh()
        self._estado(f"{empresa} quitado del flujo (la credencial se conserva).")

    def _get(self, clave: str) -> str:
        return str(self._widgets[clave].get() or "").strip()

    def _set(self, clave: str, valor: str) -> None:
        """Pone un valor en un campo de texto del formulario."""
        widget = self._widgets[clave]
        widget.delete(0, "end")
        if valor:
            widget.insert(0, valor)
