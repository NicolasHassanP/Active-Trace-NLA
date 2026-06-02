from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency que abre una sesión async por request y la cierra en finally."""
    session_factory = request.app.state.session_factory
    session: AsyncSession = session_factory()
    try:
        yield session
    finally:
        await session.close()


# RESERVADO → C-03: dependency que extrae y verifica el JWT del header Authorization
# async def get_current_user(...): ...

# RESERVADO → C-02: dependency que resuelve el tenant a partir del usuario autenticado
# async def get_tenant(...): ...

# RESERVADO → C-04: dependency que verifica que el usuario tiene un permiso modulo:accion
# async def require_permission(...): ...
