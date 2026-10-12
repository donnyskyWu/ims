"""导入全部模型，保证元数据只注册一次。"""
from app.domains.cert.model import CertExpireTask, CertLevelConfig, CertViewLog  # noqa: F401
from app.domains.auth.model import (  # noqa: F401
    AuthEventLog,
    OrgSyncBatch,
    OrgSyncBatchItem,
    OrgSyncDiff,
    OrgSyncEvent,
    OrgSyncEventAttempt,
    PositionRoleExtra,
    PositionRoleRule,
    PositionRuleRole,
    PositionRuleVersion,
    UserMapping,
)
from app.domains.device.model import (  # noqa: F401
    AssetBind,
    AssetEvent,
    AssetLedger,
    AssetPurchaseBatch,
    AssetVerifyBatch,
    AssetVerifyTask,
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
from app.domains.flow.model import FlowCcRecord, FlowInstance, FlowTask, FlowTemplate, FlowTemplateVersion, FlowTrace  # noqa: F401
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
from app.domains.resource.model import CompanyCapacityLog  # noqa: F401
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
    """只收录应用内模型。测试里临时映射的类仍留在 registry，不能参与启动校验。"""
    return [
        mapper.class_
        for mapper in Base.registry.mappers
        if mapper.class_.__module__.startswith("app.")
    ]
