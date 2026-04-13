from typing import Any

from pydantic import BaseModel

BILLING_ACTION_TYPES: frozenset[str] = frozenset({
    "org_user_account_type_change",
    "org_user_account_type_upgrade_requested",
    "org_user_account_type_upgrade_approved",
    "org_user_account_type_upgrade_denied",
    "org_default_license_type_change",
    "license_group_membership_change",
    "provisional_access_start",
    "seats_renew",
    "workspace_member_add",
    "workspace_member_remove",
})

USER_MGMT_ACTION_TYPES: frozenset[str] = frozenset({
    "org_user_create",
    "org_user_delete",
    "org_user_permission_change",
    "idp_user_create",
    "idp_user_update",
    "idp_user_delete",
})


class ActivityLogEntry(BaseModel):
    id: str
    timestamp: str
    action_type: str
    actor: dict[str, Any] = {}
    details: dict[str, Any] = {}
