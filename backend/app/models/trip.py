import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from geoalchemy2 import Geography

from app.database import Base


class VehicleClassEnum(str, enum.Enum):
    TWO_WHEELER = "2W"
    THREE_WHEELER = "3W"
    FOUR_WHEELER = "4W"


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    vehicle_class = Column(Enum(VehicleClassEnum), default=VehicleClassEnum.TWO_WHEELER)
    vehicle_range_km = Column(Float, default=80.0)
    trust_score = Column(Float, default=0.5)  
    created_at = Column(DateTime, default=datetime.utcnow)


class Trip(Base):
    __tablename__ = "trips"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    origin = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    destination = Column(Geography(geometry_type="POINT", srid=4326), nullable=False)
    vehicle_class = Column(Enum(VehicleClassEnum), default=VehicleClassEnum.TWO_WHEELER)
    vehicle_range_km = Column(Float, nullable=False)

    planned_route = Column(JSONB, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trip_id = Column(UUID(as_uuid=True), ForeignKey("trips.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    charger_id = Column(UUID(as_uuid=True), ForeignKey("chargers.id"), nullable=False)

    slot_start = Column(DateTime, nullable=False)
    slot_end = Column(DateTime, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.PENDING)

    beckn_transaction_id = Column(String, nullable=True) 
    is_grid_aware_recommended = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
