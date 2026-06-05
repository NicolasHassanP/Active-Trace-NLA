"""
fecha_academica_html.py — Generación de fragmento HTML del calendario LMS.

C-17 Design Decision D6:
    Función pura sin efectos secundarios (sin DB ni red).
    Escapa TODOS los valores de texto con html.escape para prevenir XSS
    al embeber el HTML en el aula virtual del LMS (Moodle).

Patrón idéntico a encuentro_html.generar_bloque_html (C-13 D7).

snake_case; ≤500 LOC.
"""
import html
from typing import List


def generar_fragmento_calendario(fechas: List) -> str:
    """
    Genera un fragmento HTML con el calendario de fechas académicas.

    Cada fecha incluye:
        - Tipo (Parcial | TP | Coloquio | Recuperatorio) — escaped
        - Número de instancia — escaped
        - Fecha del evento — escaped
        - Título descriptivo — escaped

    D6: todos los valores de texto se escapan con html.escape antes de
    emitirlos para prevenir XSS al embeber el fragmento en el LMS.

    Args:
        fechas: Lista de FechaAcademica (o mocks con los mismos campos:
                tipo, numero, fecha, titulo).

    Returns:
        String HTML con el fragmento formateado, listo para embeber en el LMS.
    """
    if not fechas:
        return "<div class='calendario-fechas'></div>"

    parts: List[str] = ['<div class="calendario-fechas">']

    for fa in fechas:
        tipo = html.escape(str(fa.tipo.value if hasattr(fa.tipo, "value") else fa.tipo))
        numero = html.escape(str(fa.numero))
        fecha = html.escape(str(fa.fecha))
        titulo = html.escape(str(fa.titulo))

        parts.append('  <div class="fecha-item">')
        parts.append(f'    <span class="tipo">{tipo} {numero}</span>')
        parts.append(f'    <span class="fecha">{fecha}</span>')
        parts.append(f'    <p class="titulo">{titulo}</p>')
        parts.append('  </div>')

    parts.append('</div>')
    return "\n".join(parts)
