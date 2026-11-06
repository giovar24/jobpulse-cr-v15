# -*- coding: utf-8 -*-
"""El estado "requiere_login" de los sitios (O13 · Ola 3.3).

Un sitio que devuelve 0 avisos porque **pide iniciar sesion** no esta roto:
es otra cosa. Antes ese caso se contaba como `zero_results` y llenaba la
racha de "sitio muerto" (3 corridas seguidas con 0 avisos ->
``review_required=1``), que el usuario tenia que revisar a mano sin saber
que lo que faltaba era iniciar sesion.

Los adaptadores que detectan un muro de login lanzan
:class:`RequiereLoginError`; la ingesta lo traduce al estado
``requires_login`` de la corrida y al estado ``requiere_login`` de la salud
del sitio, SIN sumar a la racha de ceros.
"""

from __future__ import annotations


class RequiereLoginError(RuntimeError):
    """El sitio exige una sesion iniciada (no es un selector roto)."""

    def __init__(
        self,
        mensaje: str = "El sitio exige iniciar sesion.",
        *,
        sitio: str | None = None,
    ) -> None:
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.sitio = sitio


def mensaje_requiere_login(sitio: str | None = None) -> str:
    """Mensaje para el usuario (con el nombre del sitio si se sabe)."""
    if sitio:
        return f"{sitio}: el sitio exige iniciar sesion."
    return "El sitio exige iniciar sesion."
