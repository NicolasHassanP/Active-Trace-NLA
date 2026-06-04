"""
comunicacion_estados.py — Máquina de estados pura para Comunicacion (sin DB).

C-12 Design Decisions:
    - OQ-5: Error es TERMINAL — no existe reintento automático.
    - Enviado y Cancelado también son TERMINALES.
    - Transiciones válidas: Pendiente→Enviando, Enviando→Enviado,
      Enviando→Error, Pendiente→Cancelado.
    - transicionar() lanza TransicionInvalidaError si la transición no es válida.

snake_case; ≤500 LOC. Sin efectos secundarios.
"""
import enum


# ---------------------------------------------------------------------------
# ComunicacionEstado — enum de estados del ciclo de vida
# ---------------------------------------------------------------------------

class ComunicacionEstado(str, enum.Enum):
    """
    Estados del ciclo de vida de una Comunicacion.

    Terminales (OQ-5): Error, Enviado, Cancelado.
    No existe reintento automático desde Error.
    """
    Pendiente = "Pendiente"
    Enviando = "Enviando"
    Enviado = "Enviado"
    Error = "Error"
    Cancelado = "Cancelado"


# ---------------------------------------------------------------------------
# Mapa de transiciones válidas (tarea 1.4 REFACTOR: constante explícita)
# ---------------------------------------------------------------------------

# Cada entry: estado_actual → frozenset de estados destino permitidos.
TRANSICIONES_VALIDAS: dict[ComunicacionEstado, frozenset[ComunicacionEstado]] = {
    ComunicacionEstado.Pendiente: frozenset({
        ComunicacionEstado.Enviando,
        ComunicacionEstado.Cancelado,
    }),
    ComunicacionEstado.Enviando: frozenset({
        ComunicacionEstado.Enviado,
        ComunicacionEstado.Error,
    }),
    # Terminales: no tienen salida.
    ComunicacionEstado.Enviado: frozenset(),
    ComunicacionEstado.Error: frozenset(),
    ComunicacionEstado.Cancelado: frozenset(),
}


# ---------------------------------------------------------------------------
# Excepción de transición inválida
# ---------------------------------------------------------------------------

class TransicionInvalidaError(Exception):
    """
    Se lanza cuando se intenta una transición de estado no permitida.

    Attributes:
        actual: estado de origen.
        destino: estado de destino rechazado.
    """

    def __init__(self, actual: ComunicacionEstado, destino: ComunicacionEstado) -> None:
        self.actual = actual
        self.destino = destino
        super().__init__(
            f"Transición inválida: {actual.value} → {destino.value}"
        )


# ---------------------------------------------------------------------------
# puede_transicionar — consulta sin efecto secundario
# ---------------------------------------------------------------------------

def puede_transicionar(
    actual: ComunicacionEstado,
    destino: ComunicacionEstado,
) -> bool:
    """
    Retorna True si la transición actual → destino está permitida.

    Pura: no modifica estado, no accede a DB.
    """
    return destino in TRANSICIONES_VALIDAS.get(actual, frozenset())


# ---------------------------------------------------------------------------
# transicionar — valida y retorna el nuevo estado
# ---------------------------------------------------------------------------

def transicionar(
    actual: ComunicacionEstado,
    destino: ComunicacionEstado,
) -> ComunicacionEstado:
    """
    Valida que la transición sea permitida y retorna el estado destino.

    Raises:
        TransicionInvalidaError: si la transición no está permitida.

    Pura: no modifica estado, no accede a DB. El llamador es responsable
    de persistir el nuevo estado.
    """
    if not puede_transicionar(actual, destino):
        raise TransicionInvalidaError(actual, destino)
    return destino
