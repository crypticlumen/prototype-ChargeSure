from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Charger, User
from app.schemas.trip import BookingCreate, BookingOut
from app.services.beckn_adapter import beckn_adapter
from app.utils.security import get_current_user

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=201)
async def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    charger = db.query(Charger).filter(Charger.id == payload.charger_id).first()
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")

    overlapping = (
        db.query(Booking)
        .filter(
            Booking.charger_id == payload.charger_id,
            Booking.status == "confirmed",
            Booking.slot_start < payload.slot_end,
            Booking.slot_end > payload.slot_start,
        )
        .first()
    )
    if overlapping:
        raise HTTPException(status_code=409, detail="Slot already booked for this charger")

    booking = Booking(
        trip_id=payload.trip_id,
        user_id=current_user.id,
        charger_id=payload.charger_id,
        slot_start=payload.slot_start,
        slot_end=payload.slot_end,
        status="pending",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    if charger.cpo and charger.cpo.beckn_bpp_id:
        ubc_response = await beckn_adapter.confirm(
            transaction_id=str(booking.id),
            order_payload={
                "provider": {"id": charger.cpo.beckn_bpp_id},
                "items": [{"id": str(charger.id)}],
                "fulfillment": {
                    "start": {"time": {"timestamp": payload.slot_start.isoformat()}},
                    "end": {"time": {"timestamp": payload.slot_end.isoformat()}},
                },
            },
        )
        if ubc_response.get("message", {}).get("ack", {}).get("status") == "ACK":
            booking.beckn_transaction_id = str(booking.id)

    booking.status = "confirmed"
    db.commit()
    db.refresh(booking)

    return booking


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(booking_id: UUID, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking


@router.delete("/{booking_id}", status_code=204)
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.user_id == current_user.id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = "cancelled"
    db.commit()
