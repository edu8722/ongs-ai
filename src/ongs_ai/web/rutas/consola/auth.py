"""Login del operador — ADR-006 §2.2.

Clave de operador por variable de entorno (`ONGS_AI_OPERADOR_CLAVE`),
comparada en tiempo constante (`hmac.compare_digest`). Sin magic-link: el
operador es quien arranca el proceso, no hay buzón que verificar (ADR §2.2).

`solo_loopback` protege TODAS las rutas de este router, incluido el propio
login: una petición no-loopback recibe 404 genérico incluso antes de ver el
formulario.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from ongs_ai.web.dependencias_operador import (
    CLAVE_SESION_OPERADOR,
    clave_operador_configurada,
    comparar_clave_en_tiempo_constante,
    solo_loopback,
)

router = APIRouter(prefix="/consola", dependencies=[Depends(solo_loopback)])

_RAIZ_PLANTILLAS = Path(__file__).resolve().parent.parent.parent / "plantillas"
_plantillas = Jinja2Templates(directory=str(_RAIZ_PLANTILLAS))

MENSAJE_CLAVE_INVALIDA = "Clave incorrecta."
MENSAJE_CONSOLA_NO_DISPONIBLE = (
    "La consola no está disponible: falta configurar ONGS_AI_OPERADOR_CLAVE en el entorno."
)


@router.get("/login")
def formulario_login(request: Request):
    if not clave_operador_configurada(request):
        return _plantillas.TemplateResponse(
            request, "error.html", {"mensaje": MENSAJE_CONSOLA_NO_DISPONIBLE}, status_code=404
        )
    return _plantillas.TemplateResponse(request, "consola/login.html", {})


@router.post("/login")
def enviar_clave(request: Request, clave: str = Form(...)):
    clave_configurada = clave_operador_configurada(request)
    if not clave_configurada or not comparar_clave_en_tiempo_constante(clave_configurada, clave):
        return _plantillas.TemplateResponse(
            request,
            "consola/login.html",
            {"mensaje": MENSAJE_CLAVE_INVALIDA},
            status_code=401,
        )
    request.session[CLAVE_SESION_OPERADOR] = True
    return RedirectResponse(url="/consola/prospectos", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.pop(CLAVE_SESION_OPERADOR, None)
    return RedirectResponse(url="/consola/login", status_code=303)
