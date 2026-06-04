# Models package — import all models here so Alembic can discover them.
from app.models.mixins import (  # noqa: F401
    SoftDeleteMixin,
    TenantMixin,
    TenantScopedBase,
    TimestampMixin,
    UUIDMixin,
)
from app.models.tenant import Tenant, TenantEstado  # noqa: F401
from app.models.auth import (  # noqa: F401
    AuthIdentity,
    RefreshSession,
    PasswordRecoveryToken,
)
from app.models.rbac import Rol, Permiso, RolPermiso, PermisoScope  # noqa: F401
from app.models.audit import AuditEvent, AuditAction, AuditResultado  # noqa: F401
from app.models.estructura import (  # noqa: F401
    EstadoEstructura,
    Carrera,
    Cohorte,
    Materia,
)
from app.models.usuario import (  # noqa: F401
    RolAsignacion,
    UsuarioEstado,
    Usuario,
    Asignacion,
)
from app.models.vigencia import EstadoVigencia, estado_vigencia  # noqa: F401
from app.models.padron import (  # noqa: F401
    VersionPadron,
    EntradaPadron,
)
from app.models.calificacion import (  # noqa: F401
    CalificacionOrigen,
    Calificacion,
    UmbralMateria,
)
from app.models.comunicacion import (  # noqa: F401
    ComunicacionEstado,
    Comunicacion,
)
from app.models.tenant_config import TenantConfig  # noqa: F401
