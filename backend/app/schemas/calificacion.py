"""
Schemas Pydantic v2 para C-10 calificaciones y umbral.

Todos con model_config = ConfigDict(extra='forbid').
tenant_id NUNCA expuesto como editable en schemas de Request/Response.

ActividadDetectada     — actividad detectada en un archivo de calificaciones.
PreviewCalificaciones  — resultado del preview (sin escritura en DB).
ImportarCalificacionesRequest — payload de confirmación de importación.
CalificacionRead       — respuesta de calificación persistida (sin tenant_id).
ConfigurarUmbralRequest — payload de configuración de umbral.
UmbralMateriaRead      — respuesta de umbral efectivo (sin tenant_id).
ReporteFinalizacionRequest — payload del reporte de finalización (F1.2).
EntregaSinCorregir     — entrega textual completada sin nota.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, field_validator


# ---------------------------------------------------------------------------
# ActividadDetectada — actividad detectada en el archivo
# ---------------------------------------------------------------------------

class ActividadDetectada(BaseModel):
    """
    Actividad detectada en el archivo de calificaciones importado.

    actividad: nombre de la actividad (ej. "Tarea 1" tras strip del sufijo "(Real)").
    escala: 'numerica' si el header termina en '(Real)'; 'textual' si los valores
            pertenecen al conjunto de escala textual configurado.
    """
    model_config = ConfigDict(extra="forbid")

    actividad: str
    escala: Literal["numerica", "textual"]


# ---------------------------------------------------------------------------
# PreviewCalificaciones — resultado del parse sin escritura en DB
# ---------------------------------------------------------------------------

class PreviewCalificaciones(BaseModel):
    """
    Resultado del endpoint POST /calificaciones/preview.

    actividades: lista de actividades detectadas con su escala.
    filas: filas del archivo (email como clave de identidad, una entrada por alumno).
    no_en_padron: emails detectados en el archivo pero sin match en el padrón activo.
    """
    model_config = ConfigDict(extra="forbid")

    actividades: List[ActividadDetectada]
    filas: List[Dict[str, Any]]
    no_en_padron: List[str]


# ---------------------------------------------------------------------------
# ImportarCalificacionesRequest — payload del endpoint POST /calificaciones/importar
# ---------------------------------------------------------------------------

class ImportarCalificacionesRequest(BaseModel):
    """
    Payload de confirmación de importación de calificaciones.

    materia_id: ID de la materia en activia-trace.
    cohorte_id: ID de la cohorte (para resolver el padrón activo — D7).
    actividades_seleccionadas: subconjunto de actividades a persistir.
    filas: filas del archivo tal como las devolvió preview.

    La identidad del actor viene del JWT (nunca del body).
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    actividades_seleccionadas: List[str]
    filas: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# CalificacionRead — respuesta de calificación persistida
# ---------------------------------------------------------------------------

class CalificacionRead(BaseModel):
    """
    Representación pública de una Calificacion persistida.

    Omite tenant_id (no se expone en respuestas) y cualquier PII del alumno
    (la identidad está en EntradaPadron, accesible por entrada_padron_id si se necesita).
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: uuid.UUID
    entrada_padron_id: uuid.UUID
    materia_id: uuid.UUID
    actividad: str
    nota_numerica: Optional[Decimal] = None
    nota_textual: Optional[str] = None
    aprobado: bool
    origen: str
    importado_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# ConfigurarUmbralRequest — payload del endpoint PUT /calificaciones/umbral
# ---------------------------------------------------------------------------

class ConfigurarUmbralRequest(BaseModel):
    """
    Payload para configurar el umbral de aprobación de una materia.

    materia_id: materia a configurar.
    umbral_pct: porcentaje mínimo aprobatorio (0–100 inclusive).
    valores_aprobatorios: valores textuales que se consideran aprobados.
    cohorte_id: (opcional) para defaults scope global ADMIN: limita el default a una cohorte.
        Si None con scope global → default aplica a la materia en todas las cohortes.

    La asignacion_id se resuelve desde current_user + materia (D5, regla dura #8/#14).
    NUNCA enviar asignacion_id en el body.
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    umbral_pct: int
    valores_aprobatorios: List[str]
    cohorte_id: Optional[uuid.UUID] = None

    @field_validator("umbral_pct")
    @classmethod
    def umbral_must_be_0_to_100(cls, v: int) -> int:
        if not (0 <= v <= 100):
            raise ValueError("umbral_pct must be between 0 and 100")
        return v


# ---------------------------------------------------------------------------
# UmbralMateriaRead — respuesta del endpoint GET/PUT /calificaciones/umbral
# ---------------------------------------------------------------------------

class UmbralMateriaRead(BaseModel):
    """
    Representación pública del umbral efectivo de una asignación×materia o default.

    Omite tenant_id (no se expone en respuestas).
    from_attributes=True para mapeo desde ORM.
    is_default=True cuando se retorna el default del tenant o el default materia/cohorte.
    asignacion_id=None → default scope global (ADMIN).
    cohorte_id: presente cuando el default es específico de una cohorte.
    """
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: Optional[uuid.UUID] = None
    asignacion_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    materia_id: uuid.UUID
    umbral_pct: int
    valores_aprobatorios: List[str]
    is_default: bool = False


# ---------------------------------------------------------------------------
# ReporteFinalizacionRequest — payload del endpoint POST /calificaciones/finalizacion
# ---------------------------------------------------------------------------

class ReporteFinalizacionRequest(BaseModel):
    """
    Payload para el endpoint de reporte de finalización (F1.2).

    materia_id: materia para cruzar calificaciones.
    cohorte_id: cohorte para resolver el padrón activo.
    filas_finalizacion: filas del reporte de finalización del LMS
        (cada fila tiene al menos 'email', 'actividad', 'completado': bool).
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    filas_finalizacion: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# EntregaSinCorregir — entrega textual completada sin nota (F1.2, RN-07/RN-08)
# ---------------------------------------------------------------------------

class EntregaSinCorregir(BaseModel):
    """
    Entrega de un alumno que está marcada como completada en el LMS pero
    no tiene Calificacion con nota_textual registrada.

    Solo se reporta para actividades de escala textual (RN-08).
    """
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    actividad: str
