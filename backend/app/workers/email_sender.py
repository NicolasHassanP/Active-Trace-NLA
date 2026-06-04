"""
email_sender.py — EmailSender Protocol + TestSender.

C-12 Design Decisions:
    D1 — OQ-3: EmailSender como Protocol (contrato formal, no ABC).
    D2 — TestSender: cumple el Protocol, registra in-memory, soporta modo fallo.
    D3 — Sin SMTP real: el proveedor real es Non-Goal para C-12.

snake_case; ≤500 LOC.
"""
from typing import List, Optional, Protocol, Dict, Any


# ---------------------------------------------------------------------------
# EmailSender — Protocol (contrato formal del sender)
# ---------------------------------------------------------------------------

class EmailSender(Protocol):
    """
    Protocolo de envío de emails.

    Implementaciones deben ser async-callable.
    El worker solo depende de este protocolo — el proveedor real (SMTP, SES, etc.)
    es un detalle de implementación fuera del scope de C-12.
    """

    async def send(
        self,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> None:
        """
        Envía el email.

        Args:
            destinatario: dirección de email del receptor (PII — no loguear).
            asunto: asunto del mensaje.
            cuerpo: cuerpo del mensaje.

        Raises:
            Exception: cualquier error de envío (SMTP timeout, auth, etc.).
        """
        ...


# ---------------------------------------------------------------------------
# TestSender / FakeSender — implementación de prueba in-memory
# ---------------------------------------------------------------------------

class FakeEmailSender:  # noqa: N801 — intentionally not prefixed with 'Test' to avoid pytest collection
    """
    Implementación de prueba de EmailSender.

    Registra todos los envíos en memoria para inspección en tests.
    Soporta modo 'forzar fallo' para testear la rama de error del worker.

    Usage::

        sender = TestSender()
        await sender.send("user@test.edu", "Asunto", "Cuerpo")
        assert len(sender.enviados) == 1

        sender_fallo = TestSender(forzar_fallo=True, mensaje_error="SMTP timeout")
        with pytest.raises(Exception, match="SMTP timeout"):
            await sender_fallo.send("user@test.edu", "Asunto", "Cuerpo")
    """

    def __init__(
        self,
        forzar_fallo: bool = False,
        mensaje_error: str = "TestSender: envío forzado a fallar",
    ) -> None:
        self.forzar_fallo = forzar_fallo
        self.mensaje_error = mensaje_error
        self.enviados: List[Dict[str, Any]] = []

    async def send(
        self,
        destinatario: str,
        asunto: str,
        cuerpo: str,
    ) -> None:
        """
        Simula el envío de un email.

        Si forzar_fallo=True, lanza RuntimeError con mensaje_error.
        Si no, registra el envío en self.enviados.
        """
        if self.forzar_fallo:
            raise RuntimeError(self.mensaje_error)

        self.enviados.append({
            "destinatario": destinatario,
            "asunto": asunto,
            "cuerpo": cuerpo,
        })


# Alias: TestSender kept for backward compatibility (tests import it by this name).
# The class is named FakeEmailSender to avoid pytest auto-collection.
TestSender = FakeEmailSender
