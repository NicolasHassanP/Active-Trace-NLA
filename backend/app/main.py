from contextlib import asynccontextmanager

from fastapi import FastAPI


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        from app.core.logging import configure_logging
        from app.core.observability import configure_telemetry

        configure_logging()

        _nightly_task = None

        if not hasattr(application.state, "session_factory"):
            from app.core.config import Settings
            from app.core.database import build_engine, build_session_factory

            settings = Settings()
            engine = build_engine(settings.DATABASE_URL)
            application.state.session_factory = build_session_factory(engine)
            configure_telemetry(application)

            # C-09: start nightly Moodle sync task if configured (D7)
            if settings.MOODLE_BASE_URL:
                from app.integrations.moodle_sync_task import start_nightly_sync_task
                _nightly_task = start_nightly_sync_task(
                    settings=settings,
                    session_factory=application.state.session_factory,
                )

            yield

            if _nightly_task is not None:
                _nightly_task.cancel()

            await engine.dispose()
        else:
            configure_telemetry(application)
            yield

    application = FastAPI(
        title="activia-trace",
        version="0.1.0",
        lifespan=lifespan,
    )

    from app.api.v1.routers.health import router as health_router
    from app.api.v1.routers.auth import router as auth_router
    from app.api.v1.routers.auditoria import router as auditoria_router
    from app.api.v1.routers.admin_estructura import router as estructura_router
    from app.api.v1.routers.admin_usuarios import router as usuarios_router
    from app.api.v1.routers.asignaciones import router as asignaciones_router
    from app.api.v1.routers.padron import router as padron_router
    from app.api.v1.routers.calificaciones import router as calificaciones_router
    from app.api.v1.routers.analisis import router as analisis_router
    from app.api.v1.routers.comunicaciones import router as comunicaciones_router
    from app.api.v1.routers.equipos import router as equipos_router
    from app.api.v1.routers.encuentros import router as encuentros_router
    from app.api.v1.routers.guardias import router as guardias_router

    application.include_router(health_router)
    application.include_router(auth_router, prefix="/api/v1")
    application.include_router(auditoria_router, prefix="/api/v1")
    application.include_router(estructura_router, prefix="/api/v1")
    application.include_router(usuarios_router, prefix="/api/v1")
    application.include_router(asignaciones_router, prefix="/api/v1")
    application.include_router(padron_router, prefix="/api/v1")
    application.include_router(calificaciones_router, prefix="/api/v1")
    application.include_router(analisis_router, prefix="/api/v1")
    application.include_router(comunicaciones_router, prefix="/api/v1")
    application.include_router(equipos_router, prefix="/api/v1")
    application.include_router(encuentros_router, prefix="/api/v1")
    application.include_router(guardias_router, prefix="/api/v1")

    return application


app = create_app()
