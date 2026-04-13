from enum import Enum

from pydantic import BaseModel


class ResourceType(str, Enum):
    PLUGIN = "PLUGIN"
    WIDGET = "WIDGET"
    COMMUNITY_FILE = "COMMUNITY_FILE"


class PaymentStatusValue(str, Enum):
    UNPAID = "UNPAID"
    PAID = "PAID"
    TRIAL = "TRIAL"


class PaymentStatus(BaseModel):
    status: PaymentStatusValue


class PaymentInformation(BaseModel):
    user_id: str
    resource_id: str
    resource_type: ResourceType
    payment_status: PaymentStatus
    date_of_purchase: str | None = None
