"""
encuentro_html.py — Generación de bloque HTML del aula virtual.

C-13 Design Decision D7:
    Escapar TODOS los valores de texto con html.escape para evitar XSS
    al embeber el HTML generado en el LMS (Moodle).

Función pura: sin efectos secundarios, sin dependencias de red/DB.
snake_case; ≤500 LOC.
"""
import html
from typing import List


def generar_bloque_html(instancias: List) -> str:
    """
    Genera un bloque HTML con la lista de instancias de encuentro.

    Cada instancia incluye:
        - Título (escaped)
        - Fecha y hora (escaped)
        - Link de meet (si presente, escaped)
        - Link de grabación (si presente, escaped)

    D7: todos los valores de texto se escapan con html.escape antes
    de emitirlos para prevenir XSS.

    Args:
        instancias: Lista de InstanciaEncuentro (o mocks con los mismos campos).

    Returns:
        String HTML con el bloque formateado, listo para embeber en el LMS.
    """
    if not instancias:
        return "<div class='encuentros'></div>"

    parts: List[str] = ['<div class="encuentros">']

    for inst in instancias:
        titulo = html.escape(str(inst.titulo))
        fecha = html.escape(str(inst.fecha))
        hora = html.escape(str(inst.hora))

        parts.append('  <div class="encuentro-item">')
        parts.append(f'    <h4>{titulo}</h4>')
        parts.append(f'    <p class="fecha">{fecha} {hora}</p>')

        if inst.meet_url:
            meet_url_esc = html.escape(str(inst.meet_url))
            parts.append(
                f'    <p class="meet">'
                f'<a href="{meet_url_esc}">Ingresar al encuentro</a>'
                f'</p>'
            )

        if inst.video_url:
            video_url_esc = html.escape(str(inst.video_url))
            parts.append(
                f'    <p class="grabacion">'
                f'<a href="{video_url_esc}">Ver grabación</a>'
                f'</p>'
            )

        parts.append('  </div>')

    parts.append('</div>')
    return "\n".join(parts)
