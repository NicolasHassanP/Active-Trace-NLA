"""
analisis_service.py — Servicio de análisis de atrasados y reportes.

C-11 Design Decision D4:
    Scoping por rol resuelto en el servicio desde el scope del permiso + asignaciones.
    NUNCA desde body ni query params.

C-11 Design Decision D5:
    Todos los endpoints bajo require_permission("atrasados:ver").
    Scope (propio/global) determinado por el grant del JWT.

Métodos:
    atrasados          — lista de alumnos atrasados (RN-06).
    ranking            — ranking por actividades aprobadas (RN-09).
    reporte_materia    — métricas consolidadas (F2.4).
    notas_finales      — notas finales agrupadas (F2.5, D7).
    monitor            — monitor general/seguimiento (F2.7/F2.8/F2.9).
    export_sin_corregir — exportación de TPs sin corregir (F2.6).

Identidad/tenant SIEMPRE desde current_user (regla dura #8).
SQL NUNCA aquí — solo en repositories (regla dura #11).
snake_case; ≤500 LOC.
"""
import uuid
from typing import List, Optional

from app.core.dependencies import CurrentUser
from app.models.rbac import PermisoScope
from app.repositories.analisis_repository import AnalisisRepository
from app.repositories.audit_repository import AuditRepository
from app.schemas.analisis import (
    ActividadResumen,
    AlumnoAtrasado,
    MonitorFila,
    MonitorFiltros,
    NotaFinalAlumno,
    RankingFila,
    ReporteMateria,
)
from app.services.analisis_calculo import calcular_nota_final, calcular_ranking
from app.services.atrasados_calculo import calcular_atrasados


class AnalisisService:
    """
    Servicio de análisis de atrasados, ranking, reportes y monitores.

    Orquestación sin SQL. Identidad/tenant desde current_user (JWT).
    El scope (propio/global) se determina desde el grant RBAC, no del body.
    Fail-closed: sin asignación ni scope global → vacío (D4).
    """

    def __init__(
        self,
        repo: AnalisisRepository,
        audit_repo: AuditRepository,
    ) -> None:
        self._repo = repo
        self._audit_repo = audit_repo

    # -----------------------------------------------------------------------
    # Helpers de scope (D4)
    # -----------------------------------------------------------------------

    def _es_scope_global(self, grant) -> bool:
        """
        True si el grant tiene scope global.
        El scope se lee del PermissionGrant (del sistema RBAC C-04).
        """
        return grant.scope == PermisoScope.global_

    # -----------------------------------------------------------------------
    # atrasados — RN-06 (5.1, 5.2, 5.3)
    # -----------------------------------------------------------------------

    async def atrasados(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        actividades: List[str],
        current_user: CurrentUser,
        grant,
        domain_user_id: uuid.UUID,
    ) -> List[AlumnoAtrasado]:
        """
        Lista de alumnos atrasados para materia×cohorte×actividades.

        Scope propio: filtra por importado_por=domain_user_id (RN-04).
        Scope global: todas las importaciones del tenant.
        Sin actividades: usa todas las actividades importadas para la materia.

        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        Identidad/tenant SIEMPRE desde current_user.
        """
        importado_por = (
            None
            if self._es_scope_global(grant)
            else domain_user_id
        )

        # Fetch todas las cals (sin filtro de actividades si no se especificaron)
        calificaciones = await self._repo.calificaciones_por_materia(
            materia_id,
            importado_por=importado_por,
            actividades=actividades if actividades else None,
        )

        # Construir mapa entrada_padron_id → [cal dicts]
        cals_map: dict[uuid.UUID, list[dict]] = {}
        for cal in calificaciones:
            cals_map.setdefault(cal.entrada_padron_id, []).append({
                "entrada_padron_id": cal.entrada_padron_id,
                "actividad": cal.actividad,
                "aprobado": cal.aprobado,
                "nota_numerica": cal.nota_numerica,
                "nota_textual": cal.nota_textual,
            })

        # Si no se pasaron actividades, derivarlas de las calificaciones cargadas
        actividades_efectivas = actividades if actividades else list({
            cal.actividad for cal in calificaciones if cal.actividad
        })

        if not actividades_efectivas:
            return []

        atrasados = calcular_atrasados(actividades_efectivas, cals_map)
        if not atrasados:
            return []

        # Enriquecer con nombre/apellidos/email desde EntradaPadron.
        # Se busca por los IDs concretos de los atrasados (no por versión activa)
        # para que re-importaciones del padrón no rompan el lookup: las
        # calificaciones siguen apuntando a los UUIDs de la versión anterior.
        ids_a_buscar = [a.entrada_padron_id for a in atrasados]
        entradas = await self._repo.get_entradas_by_ids(ids_a_buscar)
        entradas_map = {e.id: e for e in entradas}

        resultado: List[AlumnoAtrasado] = []
        for a in atrasados:
            entry = entradas_map.get(a.entrada_padron_id)
            resultado.append(
                AlumnoAtrasado(
                    entrada_padron_id=a.entrada_padron_id,
                    nombre=entry.nombre if entry else None,
                    apellidos=entry.apellidos if entry else None,
                    email=entry.email_encrypted if entry else None,
                    actividades_faltantes=a.actividades_faltantes,
                    actividades_no_aprobadas=a.actividades_no_aprobadas,
                )
            )
        return resultado

    # -----------------------------------------------------------------------
    # ranking — RN-09 (5.4)
    # -----------------------------------------------------------------------

    async def ranking(
        self,
        materia_id: uuid.UUID,
        actividades: List[str],
        current_user: CurrentUser,
        grant,
        domain_user_id: uuid.UUID,
    ) -> List[RankingFila]:
        """
        Ranking de alumnos por actividades aprobadas (RN-09).

        Solo alumnos con al menos 1 aprobada en las actividades seleccionadas.
        Ordenado descendente.
        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        """
        if not actividades:
            return []

        importado_por = (
            None
            if self._es_scope_global(grant)
            else domain_user_id
        )

        calificaciones = await self._repo.calificaciones_por_materia(
            materia_id,
            importado_por=importado_por,
            actividades=actividades,
        )

        cals_map: dict[uuid.UUID, list[dict]] = {}
        for cal in calificaciones:
            cals_map.setdefault(cal.entrada_padron_id, []).append({
                "entrada_padron_id": cal.entrada_padron_id,
                "actividad": cal.actividad,
                "aprobado": cal.aprobado,
                "nota_numerica": cal.nota_numerica,
                "nota_textual": cal.nota_textual,
            })

        return calcular_ranking(actividades, cals_map)

    # -----------------------------------------------------------------------
    # reporte_materia — F2.4 (5.5)
    # -----------------------------------------------------------------------

    async def reporte_materia(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        actividades: List[str],
        current_user: CurrentUser,
        grant,
        domain_user_id: uuid.UUID,
    ) -> ReporteMateria:
        """
        Métricas consolidadas de una materia×cohorte (F2.4).

        sin_datos=True si no hay calificaciones.
        Sin actividades: usa todas las importadas para la materia.
        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        """
        importado_por = (
            None
            if self._es_scope_global(grant)
            else domain_user_id
        )

        calificaciones = await self._repo.calificaciones_por_materia(
            materia_id,
            importado_por=importado_por,
            actividades=actividades if actividades else None,
        )

        if not calificaciones:
            return ReporteMateria(
                total_actividades=len(actividades),
                total_alumnos=0,
                total_atrasados=0,
                total_aprobadas=0,
                tasa_aprobacion=0.0,
                sin_datos=True,
            )

        # Construir mapa
        cals_map: dict[uuid.UUID, list[dict]] = {}
        for cal in calificaciones:
            cals_map.setdefault(cal.entrada_padron_id, []).append({
                "entrada_padron_id": cal.entrada_padron_id,
                "actividad": cal.actividad,
                "aprobado": cal.aprobado,
                "nota_numerica": cal.nota_numerica,
                "nota_textual": cal.nota_textual,
            })

        # Usar actividades efectivas (las pasadas, o derivadas de las calificaciones)
        actividades_efectivas = actividades if actividades else list({
            cal.actividad for cal in calificaciones if cal.actividad
        })
        atrasados = calcular_atrasados(actividades_efectivas, cals_map)
        total_alumnos = len(cals_map)
        total_aprobadas = sum(1 for c in calificaciones if c.aprobado)
        total_registros = len(calificaciones)
        tasa = total_aprobadas / total_registros if total_registros > 0 else 0.0

        return ReporteMateria(
            total_actividades=len(actividades),
            total_alumnos=total_alumnos,
            total_atrasados=len(atrasados),
            total_aprobadas=total_aprobadas,
            tasa_aprobacion=round(tasa, 4),
            sin_datos=False,
        )

    # -----------------------------------------------------------------------
    # notas_finales — F2.5, D7 (5.6)
    # -----------------------------------------------------------------------

    async def notas_finales(
        self,
        materia_id: uuid.UUID,
        actividades: List[str],
        current_user: CurrentUser,
        grant,
        domain_user_id: uuid.UUID,
    ) -> List[NotaFinalAlumno]:
        """
        Notas finales por alumno (promedio simple, D7, OQ-C11-1).

        Incluye alumnos sin calificaciones (nota_final=None).
        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        """
        if not actividades:
            return []

        importado_por = (
            None
            if self._es_scope_global(grant)
            else domain_user_id
        )

        calificaciones = await self._repo.calificaciones_por_materia(
            materia_id,
            importado_por=importado_por,
            actividades=actividades,
        )

        cals_map: dict[uuid.UUID, list[dict]] = {}
        for cal in calificaciones:
            cals_map.setdefault(cal.entrada_padron_id, []).append({
                "entrada_padron_id": cal.entrada_padron_id,
                "actividad": cal.actividad,
                "aprobado": cal.aprobado,
                "nota_numerica": float(cal.nota_numerica) if cal.nota_numerica is not None else None,
                "nota_textual": cal.nota_textual,
            })

        return calcular_nota_final(actividades, cals_map)

    # -----------------------------------------------------------------------
    # monitor — F2.7/F2.8/F2.9 (5.7)
    # -----------------------------------------------------------------------

    async def monitor(
        self,
        filtros: MonitorFiltros,
        actividades: List[str],
        current_user: CurrentUser,
        grant,
        domain_user_id: uuid.UUID,
    ) -> List[MonitorFila]:
        """
        Monitor de seguimiento (F2.7/F2.8/F2.9).

        Scope global: todos los alumnos del tenant con datos.
        Scope propio: solo alumnos de materias asignadas al docente (D4).

        Filtros: comision, regional, busqueda, rango de fechas (OQ-C11-3).
        domain_user_id: usuario.id resuelto en el router (auth_identity_id != usuario.id).
        """
        if filtros.materia_id is None:
            return []

        importado_por = (
            None
            if self._es_scope_global(grant)
            else domain_user_id
        )

        # Obtener entradas del padrón activo (con filtros de comisión/regional/búsqueda)
        cohorte_id = filtros.cohorte_id
        if cohorte_id is None:
            return []

        entradas = await self._repo.entradas_padron_activas(
            filtros.materia_id,
            cohorte_id,
            comision=filtros.comision,
            regional=filtros.regional,
            busqueda=filtros.busqueda,
        )

        if not entradas:
            return []

        entrada_ids = [e.id for e in entradas]

        # Obtener calificaciones con filtros de fecha (F2.9).
        # Cuando hay actividad_busqueda (búsqueda parcial libre del monitor),
        # se omite el filtro SQL de actividades para traer todo y luego aplicar
        # la coincidencia case-insensitive en Python.
        actividades_sql = actividades if actividades else None
        calificaciones = await self._repo.calificaciones_por_materia(
            filtros.materia_id,
            importado_por=importado_por,
            actividades=actividades_sql,
            fecha_desde=filtros.fecha_desde,
            fecha_hasta=filtros.fecha_hasta,
        )

        # Filtrar por las entradas del padrón visible
        entrada_ids_set = set(entrada_ids)
        calificaciones = [c for c in calificaciones if c.entrada_padron_id in entrada_ids_set]

        # Búsqueda parcial case-insensitive sobre actividad (solo monitor, F2.7).
        # Se aplica después del fetch para no alterar el contrato del repositorio.
        if filtros.actividad_busqueda:
            term = filtros.actividad_busqueda.lower()
            calificaciones = [
                c for c in calificaciones
                if c.actividad and term in c.actividad.lower()
            ]

        # Construir mapa
        cals_map: dict[uuid.UUID, list[dict]] = {}
        for cal in calificaciones:
            cals_map.setdefault(cal.entrada_padron_id, []).append({
                "entrada_padron_id": cal.entrada_padron_id,
                "actividad": cal.actividad,
                "aprobado": cal.aprobado,
                "nota_numerica": cal.nota_numerica,
                "nota_textual": cal.nota_textual,
            })

        # Derivar todas las actividades presentes en el dataset cuando no se
        # especifica filtro. Calculado una vez antes del loop (O(n), no O(n²)).
        todas_actividades_dataset: set[str] = (
            {cal.actividad for cal in calificaciones if cal.actividad}
            if not actividades
            else set()
        )

        # Construir filas del monitor
        filas: List[MonitorFila] = []
        for entrada in entradas:
            cals = cals_map.get(entrada.id, [])

            # Cuando hay filtro de actividades activo y el alumno no tiene
            # calificaciones para esas actividades, omitirlo del resultado.
            # Sin filtro, se muestran todos los alumnos del padrón (comportamiento actual).
            if not cals and actividades:
                continue

            # Si se pasaron actividades explícitas úsalas; si no, usar las del
            # dataset (todas las actividades conocidas en las calificaciones).
            actividades_set = set(actividades) if actividades else todas_actividades_dataset

            if not cals:
                # Sin datos para este alumno
                aprobadas = 0
                faltantes = len(actividades_set)
                estado = "sin_datos"
            else:
                aprobadas = sum(
                    1 for c in cals
                    if c["aprobado"] and (not actividades or c["actividad"] in actividades_set)
                )
                faltantes_set = actividades_set - {
                    c["actividad"] for c in cals if c["actividad"] in actividades_set
                }
                no_aprobadas = [
                    c for c in cals
                    if not c["aprobado"] and c["actividad"] in actividades_set
                ]
                faltantes = len(faltantes_set)

                if faltantes > 0 or no_aprobadas:
                    estado = "atrasado"
                else:
                    estado = "al_dia"

            # Aplicar filtro min_cumplidas
            if filtros.min_cumplidas is not None and aprobadas < filtros.min_cumplidas:
                continue

            detalle = [
                ActividadResumen(
                    actividad=c["actividad"],
                    aprobado=c["aprobado"],
                    nota=(
                        str(c["nota_numerica"])
                        if c["nota_numerica"] is not None
                        else c["nota_textual"]
                    ),
                )
                for c in cals
                if not actividades_set or c["actividad"] in actividades_set
            ]

            filas.append(MonitorFila(
                entrada_padron_id=entrada.id,
                estado=estado,
                aprobadas=aprobadas,
                faltantes=faltantes,
                nombre=getattr(entrada, "nombre", None),
                apellidos=getattr(entrada, "apellidos", None),
                email=getattr(entrada, "email_encrypted", None),
                comision=getattr(entrada, "comision", None),
                regional=getattr(entrada, "regional", None),
                actividades_detalle=detalle,
            ))

        return filas

    # -----------------------------------------------------------------------
    # export_sin_corregir — F2.6 (5.8)
    # -----------------------------------------------------------------------

    async def export_sin_corregir(
        self,
        materia_id: uuid.UUID,
        cohorte_id: uuid.UUID,
        filas_finalizacion: list,
        current_user: CurrentUser,
    ) -> list:
        """
        Exporta TPs sin corregir reutilizando CalificacionService.detectar_sin_corregir.

        Registra evento de auditoría con modulo='atrasados' (D8).
        Retorna lista de EntregaSinCorregir (solo actividades textuales, RN-08).
        """
        from app.models.audit import AuditAction, AuditResultado
        from app.repositories.calificacion_repository import CalificacionRepository
        from app.repositories.padron_repository import PadronRepository
        from app.schemas.calificacion import ReporteFinalizacionRequest
        from app.services.audit_service import AuditService
        from app.services.calificacion_service import CalificacionService

        # Crear servicio de calificaciones usando el session del repo
        cal_repo = CalificacionRepository(
            session=self._repo._session,
            tenant_id=self._repo._tenant_id,
        )
        padron_repo = PadronRepository(
            session=self._repo._session,
            tenant_id=self._repo._tenant_id,
        )
        audit_svc = AuditService(repository=self._audit_repo)
        cal_svc = CalificacionService(
            repo=cal_repo,
            padron_repo=padron_repo,
            audit_repo=self._audit_repo,
        )

        req = ReporteFinalizacionRequest(
            materia_id=materia_id,
            cohorte_id=cohorte_id,
            filas=filas_finalizacion,
        )

        entregas = await cal_svc.detectar_sin_corregir(req=req, current_user=current_user)

        # Auditoría (D8)
        if entregas is not None:
            await audit_svc.record(
                actor=current_user,
                action=AuditAction.CALIFICACIONES_IMPORTAR,
                modulo="atrasados",
                entidad_tipo="EntregaSinCorregir",
                resultado=AuditResultado.ok,
                registros_afectados=len(entregas),
                after={
                    "materia_id": str(materia_id),
                    "cohorte_id": str(cohorte_id),
                    "total_records": len(entregas),
                },
            )

        return entregas or []
