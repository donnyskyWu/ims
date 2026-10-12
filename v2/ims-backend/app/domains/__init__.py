"""导入全部模型，保证元数据只注册一次。"""
from app.domains.auth.model import (  # noqa: F401
    AuthEventLog,
    OrgSyncBatch,
    OrgSyncDiff,
    OrgSyncEvent,
    PositionRoleExtra,
    PositionRoleRule,
    UserMapping,
)
from app.domains.demo.model import (  # noqa: F401
    DemoDeptOnly,
    DemoDoc,
    DemoNote,
    DemoOrder,
    DemoOrderItem,
    DemoShare,
)
from app.domains.file.model import StoredFile  # noqa: F401
from app.domains.flow.model import FlowInstance, FlowTask, FlowTemplate, FlowTemplateVersion  # noqa: F401
from app.domains.master.model import (  # noqa: F401
    Author,
    Cert,
    CompAccount,
    Company,
    IpGroup,
    IpMember,
    LiveSession,
    PersonalAccount,
    Phone,
    PlatformAccount,
    Realname,
    SimCard,
)
from app.domains.message.model import Message, NotifyRecord  # noqa: F401
from app.domains.system.model import (  # noqa: F401
    ChangeLog,
    Dept,
    DictData,
    DictType,
    ExportTask,
    IntegrityIssue,
    IntegrityScan,
    JobLog,
    LeaveRecord,
    LoginLog,
    Menu,
    MigrationPending,
    OperateLog,
    Outbox,
    Param,
    Role,
    RoleMenu,
    RolePermDetail,
    SensitiveViewLog,
    Sequence,
    SyncState,
    Tenant,
    TenantPackage,
    TenantPackageMenu,
    Timeline,
    TrainAiCallLog,
    User,
    UserDept,
    UserRole,
    WorkCalendar,
)
from app.domains.todo.model import Todo, TodoAssignee  # noqa: F401
from app.db.base import Base


def all_models():
    return [mapper.class_ for mapper in Base.registry.mappers]
