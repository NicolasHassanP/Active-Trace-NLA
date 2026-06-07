"""
Schemas Pydantic v2 para C-11 análisis, atrasados y reportes.

Todos con model_config = ConfigDict(extra='forbid').
tenant_id/usuario_id NUNCA expuesto como editable en schemas de Request.

AlumnoAtrasado      — alumno con actividades faltantes o reprobadas.
RankingFila         — fila del ranking de aprobadas.
ReporteMateria      — métricas consolidadas por materia.
NotaFinalAlumno     — nota final agrupada por alumno.
MonitorFila         — fila del monitor de seguimiento.
MonitorFiltros      — filtros de query para el monitor.
ExportSinCorregirRequest — payload de exportación de TPs sin corregir.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator


# ---------------------------------------------------------------------------
# AlumnoAtrasado — alumno con al menos una actividad faltante o reprobada (RN-06)
# ---------------------------------------------------------------------------

class AlumnoAtrasado(BaseModel):
    """
    Alumno que está atrasado: tiene actividades faltantes y/o reprobadas.

    entrada_padron_id: identificador opaco del alumno en el padrón (nunca PII directa).
    nombre: nombre del alumno (campo ya descifrado en EntradaPadron — no PII en JSON).
    email: email del alumno descifrado (expuesto por el padrón, no re-loguear).
    actividades_faltantes: actividades seleccionadas sin calificación registrada.
    actividades_no_aprobadas: actividades con aprobado=False.
    """
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[str] = None
    actividades_faltantes: List[str]
    actividades_no_aprobadas: List[str]


# ---------------------------------------------------------------------------
# RankingFila — fila del ranking de actividades aprobadas (RN-09)
# ---------------------------------------------------------------------------

class RankingFila(BaseModel):
    """
    Fila del ranking: alumno con su conteo de actividades aprobadas.

    Solo aparecen alumnos con al menos una actividad aprobada (RN-09).
    Ordenado descendente por cantidad_aprobadas.
    """
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    cantidad_aprobadas: int


# ---------------------------------------------------------------------------
# ReporteMateria — métricas consolidadas por materia×cohorte (F2.4)
# ---------------------------------------------------------------------------

class ReporteMateria(BaseModel):
    """
    Reporte rápido de métricas para una materia y cohorte.

    sin_datos=True cuando no hay calificaciones o no se seleccionaron actividades.
    tasa_aprobacion: ratio [0.0, 1.0] de calificaciones aprobadas sobre total.
    """
    model_config = ConfigDict(extra="forbid")

    total_actividades: int
    total_alumnos: int
    total_atrasados: int
    total_aprobadas: int
    tasa_aprobacion: float
    sin_datos: bool


# ---------------------------------------------------------------------------
# NotaFinalAlumno — nota final agrupada por alumno (F2.5, D7)
# ---------------------------------------------------------------------------

class NotaFinalAlumno(BaseModel):
    """
    Nota final de un alumno calculada como promedio simple de nota_numerica
    sobre las actividades seleccionadas (OQ-C11-1: promedio simple, determinista).

    nota_final=None cuando el alumno no tiene calificaciones numéricas.
    actividades_consideradas: cantidad de actividades con nota_numerica incluida.
    """
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    nota_final: Optional[Decimal]
    actividades_consideradas: int


# ---------------------------------------------------------------------------
# ActividadResumen — detalle de una actividad por alumno en el monitor
# ---------------------------------------------------------------------------

class ActividadResumen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actividad: str
    aprobado: bool
    nota: Optional[str] = None


# MonitorFila — fila del monitor de seguimiento (F2.7/F2.8)
# ---------------------------------------------------------------------------

class MonitorFila(BaseModel):
    """
    Fila del monitor: estado de actividades de un alumno.

    estado: 'atrasado' | 'al_dia' | 'sin_datos'
    aprobadas: cantidad de actividades aprobadas en el período filtrado.
    faltantes: cantidad de actividades seleccionadas sin calificación.
    nombre / apellidos / email / comision / regional: datos desde EntradaPadron.
    actividades_detalle: lista de actividades con su resultado individual.
    """
    model_config = ConfigDict(extra="forbid")

    entrada_padron_id: uuid.UUID
    estado: Literal["atrasado", "al_dia", "sin_datos"]
    aprobadas: int
    faltantes: int
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[str] = None
    comision: Optional[str] = None
    regional: Optional[str] = None
    actividades_detalle: List[ActividadResumen] = []


# ---------------------------------------------------------------------------
# MonitorFiltros — filtros de query para el monitor (F2.7/F2.8/F2.9)
# ---------------------------------------------------------------------------

class MonitorFiltros(BaseModel):
    """
    Filtros opcionales para el monitor de seguimiento.

    Todos los campos son opcionales; si no se proveen, no filtran (no-op).
    Validación: fecha_desde <= fecha_hasta si ambas están presentes.

    fecha_desde/fecha_hasta: acota por importado_at de Calificacion (OQ-C11-3).
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: Optional[uuid.UUID] = None
    cohorte_id: Optional[uuid.UUID] = None
    comision: Optional[str] = None
    regional: Optional[str] = None
    busqueda: Optional[str] = None
    actividad: Optional[str] = None
    min_cumplidas: Optional[int] = None
    fecha_desde: Optional[datetime] = None
    fecha_hasta: Optional[datetime] = None

    @model_validator(mode="after")
    def validar_rango_fechas(self) -> "MonitorFiltros":
        """Valida que fecha_desde <= fecha_hasta si ambas están presentes."""
        if self.fecha_desde is not None and self.fecha_hasta is not None:
            if self.fecha_desde > self.fecha_hasta:
                raise ValueError(
                    "fecha_desde no puede ser posterior a fecha_hasta"
                )
        return self


# ---------------------------------------------------------------------------
# ExportSinCorregirRequest — payload de exportación de TPs sin corregir (F2.6)
# ---------------------------------------------------------------------------

class ExportSinCorregirRequest(BaseModel):
    """
    Payload de exportación de TPs sin corregir.

    materia_id: ID de la materia.
    cohorte_id: ID de la cohorte (para resolver padrón activo).
    filas_finalizacion: filas del reporte de finalización del LMS.

    La identidad del actor viene del JWT (nunca del body).
    """
    model_config = ConfigDict(extra="forbid")

    materia_id: uuid.UUID
    cohorte_id: uuid.UUID
    filas_finalizacion: List[dict]
