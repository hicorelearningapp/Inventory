from sqlalchemy import Column, Integer, Float, DateTime, String
from .sql_base import Base
from ..utils.timezone import ist_now


class Inventory(Base):
    __tablename__ = "Inventory"

    InventoryId = Column(Integer, primary_key=True, index=True)

    ItemId = Column(Integer, nullable=False)
    DeviceId = Column(Integer, nullable=True)

    Weight = Column(Float, nullable=True)

    CreatedAt = Column(DateTime, default=ist_now)
    UpdatedAt = Column(DateTime, default=ist_now, onupdate=ist_now)





class WeightTracking(Base):
    __tablename__ = "WeightTracking"

    WeightTrackingId = Column(Integer, primary_key=True, index=True)
    DeviceId = Column(Integer, nullable=False)
    DateTime = Column(DateTime, default=ist_now)
    Weight = Column(Float, nullable=False)



class ActivityLog(Base):
    __tablename__ = "ActivityLog"

    ActivityLogId = Column(Integer, primary_key=True, index=True)
    DeviceId = Column(Integer, nullable=False)
    DateTime = Column(DateTime, default=ist_now)
    Event = Column(String(255), nullable=False)


# from sqlalchemy import Column, Integer, String, Float, DateTime
# from datetime import datetime
# from .sql_base import Base


# # -------------------------------
# #   INVENTORY MODEL
# # -------------------------------
# class Inventory(Base):
#     __tablename__ = "Inventory"

#     InventoryId = Column(Integer, primary_key=True, index=True)

#     ItemCode = Column(String(100), nullable=True)
#     ItemName = Column(String(255), nullable=True)
#     Category = Column(String(100), nullable=True)
#     Description = Column(String(500), nullable=True)

#     DeviceId = Column(Integer, nullable=True)

#     UnitWeight = Column(Float, nullable=True)
#     Stock = Column(Float, nullable=True)
#     Threshold = Column(Float, nullable=True)
#     StockOut = Column(Float, nullable=True)
#     Consumption = Column(Float, nullable=True)

#     Status = Column(String(50), nullable=True)

#     CreatedAt = Column(DateTime, default=datetime.utcnow)
#     UpdatedAt = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



