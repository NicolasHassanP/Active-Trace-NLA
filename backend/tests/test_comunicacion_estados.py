"""
TDD tests for comunicacion_estados.py — máquina de estados pura (sin DB).

C-12 Design Decisions:
    - ComunicacionEstado enum: Pendiente, Enviando, Enviado, Error, Cancelado.
    - puede_transicionar(actual, destino) -> bool para las transiciones válidas.
    - transicionar(actual, destino) -> ComunicacionEstado | raises TransicionInvalidaError.
    - Error, Enviado y Cancelado son TERMINALES (OQ-5): no existe salida de reintento.

Tasks: 1.1 (RED), 1.3 (TRIANGULATE), 1.4 (REFACTOR verified).
"""
import pytest

from app.services.comunicacion_estados import (
    ComunicacionEstado,
    TransicionInvalidaError,
    puede_transicionar,
    transicionar,
)


# ---------------------------------------------------------------------------
# §1.1 — RED: enum existe con los 5 valores esperados
# ---------------------------------------------------------------------------

def test_enum_tiene_cinco_estados():
    estados = {e.value for e in ComunicacionEstado}
    assert estados == {"Pendiente", "Enviando", "Enviado", "Error", "Cancelado"}


# ---------------------------------------------------------------------------
# §1.1 — RED: transiciones válidas definidas en el diseño
# ---------------------------------------------------------------------------

def test_pendiente_puede_transicionar_a_enviando():
    """Pendiente → Enviando: el worker toma el mensaje."""
    assert puede_transicionar(ComunicacionEstado.Pendiente, ComunicacionEstado.Enviando) is True


def test_enviando_puede_transicionar_a_enviado():
    """Enviando → Enviado: envío exitoso."""
    assert puede_transicionar(ComunicacionEstado.Enviando, ComunicacionEstado.Enviado) is True


def test_enviando_puede_transicionar_a_error():
    """Enviando → Error: fallo de envío."""
    assert puede_transicionar(ComunicacionEstado.Enviando, ComunicacionEstado.Error) is True


def test_pendiente_puede_transicionar_a_cancelado():
    """Pendiente → Cancelado: cancelación antes de despacho."""
    assert puede_transicionar(ComunicacionEstado.Pendiente, ComunicacionEstado.Cancelado) is True


# ---------------------------------------------------------------------------
# §1.3 — TRIANGULATE: transiciones inválidas deben retornar False
# ---------------------------------------------------------------------------

def test_enviado_no_puede_transicionar_a_enviando():
    """Enviado es TERMINAL — no puede volver a Enviando."""
    assert puede_transicionar(ComunicacionEstado.Enviado, ComunicacionEstado.Enviando) is False


def test_cancelado_no_puede_transicionar_a_enviando():
    """Cancelado es TERMINAL — no puede volver a Enviando."""
    assert puede_transicionar(ComunicacionEstado.Cancelado, ComunicacionEstado.Enviando) is False


def test_enviado_no_puede_transicionar_a_cancelado():
    """No se puede cancelar un mensaje ya enviado."""
    assert puede_transicionar(ComunicacionEstado.Enviado, ComunicacionEstado.Cancelado) is False


def test_error_no_puede_transicionar_a_enviando():
    """Error es TERMINAL (OQ-5) — NO existe reintento automático."""
    assert puede_transicionar(ComunicacionEstado.Error, ComunicacionEstado.Enviando) is False


def test_error_no_puede_transicionar_a_pendiente():
    """Error es TERMINAL — no puede regresar a Pendiente."""
    assert puede_transicionar(ComunicacionEstado.Error, ComunicacionEstado.Pendiente) is False


def test_error_no_puede_transicionar_a_cancelado():
    """Error es TERMINAL — cancelar no tiene sentido."""
    assert puede_transicionar(ComunicacionEstado.Error, ComunicacionEstado.Cancelado) is False


def test_pendiente_no_puede_transicionar_a_enviado():
    """No se puede saltar Enviando → Enviado directamente."""
    assert puede_transicionar(ComunicacionEstado.Pendiente, ComunicacionEstado.Enviado) is False


def test_pendiente_no_puede_transicionar_a_error():
    """No puede pasar a Error sin pasar por Enviando."""
    assert puede_transicionar(ComunicacionEstado.Pendiente, ComunicacionEstado.Error) is False


# ---------------------------------------------------------------------------
# §1.3 — TRIANGULATE: transicionar() lanza TransicionInvalidaError en los inválidos
# ---------------------------------------------------------------------------

def test_transicionar_valido_retorna_destino():
    """transicionar en una transición válida retorna el estado destino."""
    resultado = transicionar(ComunicacionEstado.Pendiente, ComunicacionEstado.Enviando)
    assert resultado == ComunicacionEstado.Enviando


def test_transicionar_invalido_lanza_error():
    """transicionar en una transición inválida lanza TransicionInvalidaError."""
    with pytest.raises(TransicionInvalidaError):
        transicionar(ComunicacionEstado.Enviado, ComunicacionEstado.Enviando)


def test_transicionar_invalido_no_muta_estado():
    """La excepción se lanza antes de mutar — el estado original no cambia."""
    actual = ComunicacionEstado.Error
    with pytest.raises(TransicionInvalidaError):
        transicionar(actual, ComunicacionEstado.Pendiente)
    # El estado original no fue mutado (es un enum — inmutable por naturaleza)
    assert actual == ComunicacionEstado.Error


def test_transicionar_enviando_a_error_retorna_error():
    """Envío fallido: Enviando → Error retorna ComunicacionEstado.Error."""
    resultado = transicionar(ComunicacionEstado.Enviando, ComunicacionEstado.Error)
    assert resultado == ComunicacionEstado.Error


def test_transicionar_enviando_a_enviado_retorna_enviado():
    """Envío exitoso: Enviando → Enviado retorna ComunicacionEstado.Enviado."""
    resultado = transicionar(ComunicacionEstado.Enviando, ComunicacionEstado.Enviado)
    assert resultado == ComunicacionEstado.Enviado


# ---------------------------------------------------------------------------
# §1.3 — TRIANGULATE: estados terminales (OQ-5)
# ---------------------------------------------------------------------------

def test_todos_los_terminales_no_tienen_salida():
    """
    Error, Enviado y Cancelado son TERMINALES.
    Ningún estado terminal puede hacer ninguna transición válida.
    """
    terminales = [ComunicacionEstado.Error, ComunicacionEstado.Enviado, ComunicacionEstado.Cancelado]
    todos_los_estados = list(ComunicacionEstado)
    for terminal in terminales:
        for destino in todos_los_estados:
            assert puede_transicionar(terminal, destino) is False, (
                f"{terminal} es TERMINAL pero puede_transicionar({terminal}, {destino}) retornó True"
            )
