"""Roles, portals, permissions and data scope.

Each role belongs to exactly one portal and can sign in only there. Permissions say what a role may do; the scope says
which entries (and people) it sees. The designation hierarchy, low to high: Sales Officer, Branch Manager, Cluster
Manager (RTM, not every branch has one), Region Manager (RBH), Product Manager, Business Manager. The call centre,
HR and MIS roles sit outside that ladder.
"""
from dataclasses import dataclass

PORTALS: dict[str, str] = {
    "mobile": "Sales Officer app",
    "manage": "Management portal",
    "callcentre": "Call-centre portal",
    "admin": "HR & Admin portal",
}


@dataclass(frozen=True)
class RoleDef:
    label: str
    portal: str
    level: int  # place in the designation hierarchy (0 = outside it)
    scope: str  # own | branch | cluster | region | company | allocated
    placement: str | None  # what the user must be attached to: branch | cluster | region | None


ROLES: dict[str, RoleDef] = {
    "sales_officer": RoleDef("Sales Officer", "mobile", 1, "own", "branch"),
    "branch_manager": RoleDef("Branch Manager", "manage", 2, "branch", "branch"),
    "cluster_manager": RoleDef("Cluster Manager (RTM)", "manage", 3, "cluster", "cluster"),
    "region_manager": RoleDef("Region Manager (RBH)", "manage", 4, "region", "region"),
    "product_manager": RoleDef("Product Manager", "manage", 5, "company", None),
    "business_manager": RoleDef("Business Manager", "manage", 6, "company", None),
    "caller": RoleDef("Caller", "callcentre", 0, "allocated", None),
    "master_owner": RoleDef("Master owner (call-centre lead)", "callcentre", 0, "company", None),
    "sankalp_monitor": RoleDef("Sankalp monitor (HR)", "admin", 0, "company", None),
    "mis": RoleDef("MIS (Credit / Ops)", "admin", 0, "company", None),
    "admin": RoleDef("System admin", "admin", 0, "company", None),
}

_READ = {"entries.read", "dashboard.read", "compliance.read", "map.read", "team.read"}

PERMISSIONS: dict[str, frozenset[str]] = {
    "sales_officer": frozenset({"entries.create", "entries.read"}),
    # BM answers its leads and corrects numbers; it corrects the SO only when its branch has no cluster (no RTM).
    "branch_manager": frozenset(_READ | {"branch.answer", "correct.number", "correct.so"}),
    "cluster_manager": frozenset(_READ | {"correct.number", "correct.so"}),
    # The RBH answers for branches that have no BM, and corrects numbers where a branch has neither BM nor RTM.
    "region_manager": frozenset(_READ | {"branch.answer", "correct.number"}),
    "product_manager": frozenset(_READ | {"compliance.export"}),
    "business_manager": frozenset(_READ | {"compliance.export"}),
    "caller": frozenset({"entries.read", "calls.work"}),
    "master_owner": frozenset({"entries.read", "dashboard.read", "compliance.read", "map.read",
                               "calls.work", "calls.manage", "login_register.upload"}),
    "sankalp_monitor": frozenset(_READ | {"compliance.export", "correct.so", "category.review",
                                          "reference.import", "takeoff.export", "audit.read"}),
    "mis": frozenset({"login_register.upload"}),
    "admin": frozenset(_READ | {"compliance.export", "users.manage", "org.manage", "settings.manage",
                                "cp_subtypes.manage", "reference.import", "takeoff.export", "audit.read",
                                "login_register.upload"}),
}

ALL_PERMISSIONS: frozenset[str] = frozenset().union(*PERMISSIONS.values())


def portal_of(role: str) -> str | None:
    r = ROLES.get(role)
    return r.portal if r else None


def has_perm(role: str, perm: str) -> bool:
    return perm in PERMISSIONS.get(role, frozenset())


def roles_for_portal(portal: str) -> list[str]:
    return [k for k, r in ROLES.items() if r.portal == portal]
