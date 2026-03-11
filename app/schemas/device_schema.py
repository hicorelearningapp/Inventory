from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from ..utils.timezone import ist_now


class DeviceBase(BaseModel):
    DeviceName: Optional[str]
    DeviceType: Optional[str]
    ConnectionMode: Optional[str]

    Capacity: Optional[float]
    # Weight: Optional[float]

    # LastReading: Optional[float]
    Battery: Optional[int]
    Status: Optional[str]

    # InventoryId: Optional[int]
    Notes: Optional[str]

    LocationName: Optional[str]
    Latitude: Optional[float]
    Longitude: Optional[float]

    class Config:
        from_attributes = True


class DeviceCreate(DeviceBase):
    pass


class DeviceUpdate(DeviceBase):
    pass


class DeviceRead(DeviceBase):
    DeviceId: int
    CreatedAt: datetime
    UpdatedAt: datetime


# -------- Tracking Schemas --------
class DeviceWeightUpdate(BaseModel):
    Weight: float

class BatteryUpdate(BaseModel):
    Battery: int


class LocationUpdate(BaseModel):
    LocationName: Optional[str]
    Latitude: float
    Longitude: float


class TrackingUpdate(BaseModel):
    LastReading: Optional[float]
    Status: Optional[str]


