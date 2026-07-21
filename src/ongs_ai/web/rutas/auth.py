"""Rutas de autenticación por magic link — ADR-005 §2.2/§2.4/§5.

Respuesta genérica SIEMPRE en `POST /login` (exista o no el email — anti
user-enumeration). El error de confirmación nunca distingue el motivo exacto
de un fallo (caducado/usado/inventado): siempre el mismo error genérico.

PROMPT-022 B: `GET /login/confirmar` DEJA DE CONSUMIR el token (fallo real
del operador — una petición especulativa de prefetch/escáner de correo hace
GET antes que la navegación real del usuario y gasta el enlace de un solo
uso). El GET solo valida presencia del parámetro y devuelve una página con un
botón que hace `POST /login/confirmar`; el consumo atómico del token vive
SOLO en el POST, que un prefetcher nunca dispara. El GET no toca el almacén
ni siquiera para comprobar si el token es válido — la página es idéntica
exista o no el token (misma anti-enumeración que el resto del flujo)."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from ongs_ai.servicios.autenticacion import generar_y_enviar_enlace, validar_y_consumir_token

router = APIRouter()

_RAIZ_PLANTILLAS = Path(__file__).resolve().parent.parent / "plantillas"
_plantillas = Jinja2Templates(directory=str(_RAIZ_PLANTILLAS))

MENSAJE_ENLACE_ENVIADO = "Si el correo está dado de alta, se ha enviado un enlace de acceso."
MENSAJE_ENLACE_INVALIDO = "El enlace no es válido o ha caducado. Solicita uno nuevo."


@router.get("/login")
def formulario_login(request: Request):
    return _plantillas.TemplateResponse(request, "login.html", {})


@router.post("/login")
def enviar_enlace(request: Request, email: str = Form(...)):
    estado = request.app.state
    generar_y_enviar_enlace(
        email,
        estado.almacen,
        estado.almacen,
        estado.enviador_enlace,
        generador_token=estado.generador_token,
        reloj=estado.reloj,
        ttl=estado.ttl_token,
    )
    return _plantillas.TemplateResponse(
        request, "login.html", {"mensaje": MENSAJE_ENLACE_ENVIADO}
    )


@router.get("/login/confirmar")
def confirmar_login(request: Request, token: str):
    """Solo valida presencia de `token` (FastAPI ya lo exige) y renderiza la
    página de confirmación — SIN tocar el almacén (B1). Un prefetcher/escáner
    solo hace GET; con esto ya no puede consumir el enlace."""
    return _plantillas.TemplateResponse(request, "confirmar.html", {"token": token})


@router.post("/login/confirmar")
def confirmar_login_consumir(request: Request, token: str = Form(...)):
    """Aquí vive TODO lo que antes hacía el GET: consumo atómico del token,
    creación de sesión, 303 a `/panel` (B2). Sin token CSRF de sesión: en
    este punto no existe sesión previa (el usuario aún no ha entrado) — el
    propio token de un solo uso, generado por el servidor y recibido solo
    por quien abrió el enlace, ES la prueba de posesión; exigir un CSRF de
    sesión aquí no añadiría protección real y solo complicaría el flujo."""
    estado = request.app.state
    entidad_id = validar_y_consumir_token(token, estado.almacen, estado.reloj)
    if entidad_id is None:
        return _plantillas.TemplateResponse(
            request, "error.html", {"mensaje": MENSAJE_ENLACE_INVALIDO}, status_code=400
        )
    request.session["entidad_id"] = entidad_id
    return RedirectResponse(url="/panel", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)
