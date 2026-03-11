from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from ..utils.timezone import ist_now


class InventoryBase(BaseModel):
    ItemId: int
    DeviceId: Optional[int]
    Weight: Optional[float]

    class Config:
        from_attributes = True


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    ItemId: Optional[int]
    DeviceId: Optional[int]
    Weight: Optional[float]


class InventoryWeightUpdate(BaseModel):
    Weight: float


class InventoryRead(InventoryBase):
    InventoryId: int
    CreatedAt: datetime
    UpdatedAt: datetime




# -------- Weight Tracking Schemas --------
class WeightTrackingCreate(BaseModel):
    Weight: float


class WeightTrackingRead(BaseModel):
    WeightTrackingId: int
    DeviceId: int
    DateTime: datetime
    Weight: float

    class Config:
        from_attributes = True



class ActivityLogCreate(BaseModel):
    Event: str


class ActivityLogRead(BaseModel):
    ActivityLogId: int
    DeviceId: int
    DateTime: datetime
    Event: str

    class Config:
        from_attributes = True



# from pydantic import BaseModel
# from typing import Optional
# from datetime import datetime


# class InventoryBase(BaseModel):
#     ItemCode: Optional[str]
#     ItemName: Optional[str]
#     Category: Optional[str]
#     Description: Optional[str]

#     DeviceId: Optional[int]

#     UnitWeight: Optional[float]
#     Stock: Optional[float]
#     Threshold: Optional[float]
#     StockOut: Optional[float]
#     Consumption: Optional[float]

#     Status: Optional[str]

#     class Config:
#         from_attributes = True


# class InventoryCreate(InventoryBase):
#     pass


# class InventoryUpdate(InventoryBase):
#     pass


# class InventoryRead(InventoryBase):
#     InventoryId: int
#     CreatedAt: datetime
#     UpdatedAt: datetime


# # ---------- Special Updates ----------

# class StockUpdate(BaseModel):
#     Stock: float


# class DeviceAssign(BaseModel):
#     DeviceId: int
