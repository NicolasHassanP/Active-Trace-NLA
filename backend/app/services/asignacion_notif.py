"""
asignacion_notif.py — Helper compartido: notificación de asignación docente.

Usado por EquipoService y AsignacionService para enviar mensajería interna
cuando se asigna un docente a una materia/cohorte.

snake_case; ≤500 LOC.
"""
import uuid
from datetime import date
from typing import Optional

from app.models.usuario import RolAsignacion
from app.repositories.mensajeria_repository import MensajeriaRepository


async def notificar_asignacion(
    mensajeria_repo: MensajeriaRepository,
    remitente_id: uuid.UUID,
    destinatario_id: uuid.UUID,
    *,
    materia_id: Optional[uuid.UUID],
    cohorte_id: Optional[uuid.UUID],
    rol: RolAsignacion,
    desde: date,
    materia_nombre: Optional[str] = None,
    cohorte_nombre: Optional[str] = None,
) -> None:
    """
    Notifica al docente asignado vía mensajería interna.

    Crea o reutiliza el hilo 1:1 entre el actor (remitente) y el docente
    (destinatario). La campanita del destinatario incrementa automáticamente.

    Auto-asignación (remitente == destinatario) → no enviar mensaje.

    materia_nombre / cohorte_nombre: nombres legibles resueltos por el caller
    (vía MateriaRepository / CohorteRepository). Si no se pueden resolver,
    se usa el UUID como fallback defensivo — no crashea.
    """
    if remitente_id == destinatario_id:
        return  # auto-asignación: no notificar

    mat_str = materia_nombre or (str(materia_id) if materia_id else "—")
    coh_str = cohorte_nombre or (str(cohorte_id) if cohorte_id else "—")
    cuerpo = (
        f"Fuiste asignado a {mat_str} ({coh_str}) "
        f"como {rol.value}, vigente desde {desde}."
    )
    asunto = "Nueva asignación"

    hilo_id = await mensajeria_repo.buscar_hilo_existente(remitente_id, destinatario_id)
    if hilo_id is None:
        await mensajeria_repo.crear_hilo(
            remitente_id=remitente_id,
            destinatario_id=destinatario_id,
            asunto=asunto,
            cuerpo=cuerpo,
        )
    else:
        await mensajeria_repo.agregar_mensaje(
            hilo_id=hilo_id,
            remitente_id=remitente_id,
            asunto=asunto,
            cuerpo=cuerpo,
        )
