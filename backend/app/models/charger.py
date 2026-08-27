import uuid
import enum
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, DateTime, Enum, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography

from app.database import Base


class ConnectorType(str, enum.Enum):
    TYPE2 = "TYPE2"
    CCS2 = "CCS2"
    CHADEMO = "CHADEMO"
    GB_T = "GB_T"
    BHARAT_AC001 = "BHARAT_AC001"
    BHARAT_DC001 = "BHARAT_DC001"


class VehicleClass(str, enum.Enum):
    TWO_WHEELER = "2W"
    THREE_WHEELER = "3W"
    FOUR_WHEELER = "4W"


class CPO(Base):
    """Charge Point Operator — the entity that owns/operates a station."""
    __tablename__ = "cpos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    operator_reliability_index = Column(Float, default=0.5)  # 0-1, updated nightly
    ocpi_party_id = Column(String, nullable=True)
    beckn_bpp_id = Column(String, nullable=True)  # populated once UBC integration is live
    created_at = Column(DateTime, default=datetime.utcnow)

    chargers = relationship("Charger", back_populates="cpo")


class Charger(Base):
    __tablename__ = "chargers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_id = Column(String, index=True, nullable=True)  # OpenChargeMap / OCPI id
    cpo_id = Column(UUID(as_uuid=True), ForeignKey("cpos.id"), nullable=True)

    name = Column(String, nullable=False)
    address = Column(String, nullable=True)
    location = Column(Geography(geometry_type="POINT", srid=4326), nullable=False, index=True)

    connector_types = Column(String, nullable=False, default=ConnectorType.TYPE2.value)  # CSV
    supports_2w = Column(Boolean, default=True)
    supports_3w = Column(Boolean, default=True)
    supports_4w = Column(Boolean, default=True)

    max_power_kw = Column(Float, nullable=True)
    installed_at = Column(DateTime, nullable=True)
    last_verified_at = Column(DateTime, nullable=True)  # last confirmed-working timestamp

    is_active = Column(Boolean, default=True)

    cpo = relationship("CPO", back_populates="chargers")
    sessions = relationship("ChargingSession", back_populates="charger")
    crowd_reports = relationship("CrowdReport", back_populates="charger")


class ChargingSession(Base):
    """A completed or simulated charging session — feeds the reliability model."""
    __tablename__ = "charging_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    charger_id = Column(UUID(as_uuid=True), ForeignKey("chargers.id"), nullable=False)

    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)
    energy_kwh = Column(Float, nullable=True)
    was_successful = Column(Boolean, nullable=False)  # False = failed/aborted session
    failure_reason = Column(String, nullable=True)  # e.g. "offline", "queue_timeout", "hardware_fault"
    source = Column(String, default="ocpp")  # ocpp | simulated | crowd_confirmed

    charger = relationship("Charger", back_populates="sessions")


class CrowdReport(Base):
    """Rider-submitted status report, rate-limited and trust-weighted."""
    __tablename__ = "crowd_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    charger_id = Column(UUID(as_uuid=True), ForeignKey("chargers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    reported_status = Column(String, nullable=False)  # working | broken | queued | unknown
    reporter_trust_score = Column(Float, default=0.5)  # 0-1, built from account history
    is_geofenced_confirmed = Column(Boolean, default=False)  # GPS check-in within N meters
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    charger = relationship("Charger", back_populates="crowd_reports")
