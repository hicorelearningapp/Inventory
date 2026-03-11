from sqlalchemy import Column, Integer, String, Float, DateTime
from .sql_base import Base
from ..utils.timezone import ist_now


class Item(Base):
    __tablename__ = "Item"

    ItemId = Column(Integer, primary_key=True, index=True)

    ItemName = Column(String(255), nullable=False)
    Category = Column(String(255), nullable=True)
    Description = Column(String(500), nullable=True)

    PerUnitWeight = Column(Float, nullable=False)
    Measurement = Column(String(50), nullable=True)

    MinThreshold = Column(Float, nullable=True)
    MaxThreshold = Column(Float, nullable=True)

    CreatedAt = Column(DateTime, default=ist_now)
    UpdatedAt = Column(DateTime, default=ist_now, onupdate=ist_now)
