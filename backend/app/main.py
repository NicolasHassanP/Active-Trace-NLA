from contextlib import asynccontextmanager

from fastapi import FastAPI


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        from app.core.logging import configure_logging
        from app.core.observability import configure_telemetry

        configure_logging()

        if not hasattr(application.state, "session_factory"):
            from app.core.config import Settings
            from app.core.database import build_engine, build_session_factory

            settings = Settings()
            engine = build_engine(settings.DATABASE_URL)
            application.state.session_factory = build_session_factory(engine)
            configure_telemetry(application)
            yield
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

    application.include_router(health_router)

    return application


app = create_app()
