# -*- coding: utf-8 -*-
"""Cuentas de login (credenciales de los sitios que piden sesión) — SIN Tk.

Envuelve `jobpulse_v15.credenciales`, que es la única verdad:

- **LA LISTA** (`lista_sitios_login()`): ANE, Indeed, LinkedIn y todo lo que
  los proveedores detectaron en vivo (login-wall) — con el estado de cada uno
  (obligatorio, auto-login, pendiente, si ya hay credencial).
- **El almacén**: metadatos en `data/empresas/credenciales.json` (gitignored)
  y la **contraseña en el Administrador de Credenciales de Windows**
  (keyring). El `.env` sigue siendo el respaldo de ANE
  (`ANE_USER`/`ANE_PASSWORD`).

REGLA DE ORO: la contraseña **nunca** se lee desde aquí ni se muestra en la
UI. La interfaz solo puede **escribirla**; dejarla vacía significa
"conserva la que ya está guardada".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jobpulse_v15 import credenciales


@dataclass(frozen=True)
class SitioCuenta:
    """Un sitio que pide login, con su estado (SIN la contraseña)."""

    empresa: str
    url: str
    grupo: str
    grupo_label: str
    obligatorio: bool
    auto_login: bool
    tiene_credencial: bool
    usuario: str
    acceso: str
    sso: str
    almacen: str
    pendiente: str
    motivo: str
    detectado: str

    @classmethod
    def desde(cls, item: dict[str, Any]) -> "SitioCuenta":
        tiene = bool(item.get("tiene_credencial"))
        return cls(
            empresa=str(item.get("empresa") or ""),
            url=str(item.get("url") or ""),
            grupo=str(item.get("grupo") or ""),
            grupo_label=str(item.get("grupo_label") or ""),
            obligatorio=bool(item.get("obligatorio")),
            auto_login=bool(item.get("auto_login")),
            tiene_credencial=tiene,
            usuario=str(item.get("usuario") or ""),
            # El método de acceso solo se muestra si HAY credencial: un sitio
            # que admite Google pero sin usuario guardado no accede a nada.
            acceso=(str(item.get("acceso") or "") if tiene else ""),
            sso=str(item.get("sso") or ""),
            almacen=str(item.get("almacen") or ""),
            pendiente=str(item.get("pendiente") or ""),
            motivo=str(item.get("motivo") or ""),
            detectado=str(item.get("detectado") or ""),
        )

    @property
    def estado(self) -> str:
        """Texto corto del estado de la cuenta (para la tabla)."""
        if self.tiene_credencial:
            return "Con credencial"
        if self.pendiente:
            return "Pendiente"
        return "Sin credencial"


class CuentasStore:
    """Operaciones sobre las cuentas de login (sin Tk)."""

    def sitios(self) -> list[SitioCuenta]:
        """LA LISTA de sitios que piden login, con su estado."""
        return [SitioCuenta.desde(item)
                for item in credenciales.lista_sitios_login()]

    def resumen(self) -> dict[str, int]:
        """Totales para la franja de métricas."""
        datos = credenciales.resumen()
        return {
            "total": int(datos.get("total", 0)),
            "obligatorios": int(datos.get("obligatorios", 0)),
            "con_credencial": int(datos.get("con_credencial", 0)),
            "pendientes": int(datos.get("pendientes", 0)),
            "auto_login": int(datos.get("auto_login", 0)),
        }

    def guardar(self, empresa: str, usuario: str = "", password: str = "",
                url: str = "", auto_login: bool = True, nota: str = "",
                sso: str = "", obligatorio: bool = False) -> dict[str, Any]:
        """Guarda la credencial (la contraseña va al almacén seguro del SO).

        ``password`` vacío = conserva la que ya estaba guardada.
        """
        return credenciales.upsert_credencial(
            empresa=empresa,
            usuario=usuario,
            password=password,
            url=url,
            auto_login=auto_login,
            nota=nota,
            sso=sso,
            obligatorio=obligatorio,
        )

    def borrar(self, empresa: str) -> bool:
        """Borra la credencial (metadatos + contraseña del keyring)."""
        return credenciales.borrar_credencial(empresa)

    def agregar(self, empresa: str, url: str = "", motivo: str = "",
                grupo: str = "directos", obligatorio: bool = False) -> dict[str, Any]:
        """Da de alta un sitio nuevo en el flujo (lista + barrido de portales)."""
        return credenciales.agregar_sitio_login(
            empresa, url, motivo=motivo, grupo=grupo, obligatorio=obligatorio)

    def quitar(self, empresa: str) -> dict[str, Any]:
        """Quita un sitio manual del flujo (los seeds fijos NO se tocan)."""
        return credenciales.quitar_sitio_login(empresa)

    def auto_login(self, empresa: str, valor: bool) -> bool:
        """Activa/desactiva el auto-login del sitio."""
        return credenciales.marcar_auto_login(empresa, valor)
