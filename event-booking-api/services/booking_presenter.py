"""Public booking representation; never exposes secret QR verification tokens."""
from datetime import datetime, timezone
import models


def as_utc(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def effective_status(booking):
    if booking.status == models.BOOKING_HELD and booking.expires_at and as_utc(booking.expires_at) <= datetime.now(timezone.utc):
        return models.BOOKING_EXPIRED
    return booking.status


def serialize_booking(booking, *, include_event=False):
    items = []
    for item in booking.items:
        inv = item.inventory
        label = (inv.seat.seat_code if inv and inv.seat else
                 inv.zone.name if inv and inv.zone else
                 inv.ticket_type.name if inv and inv.ticket_type else "Ticket")
        items.append({"id": item.id, "label": label,
                      "inventory_type": inv.inventory_type if inv else "unknown",
                      "quantity": item.quantity, "unit_price": item.price,
                      "subtotal": item.price * item.quantity, "status": item.status})
    issued = []
    for ticket in booking.tickets_rel:
        label = (ticket.seat.seat_code if ticket.seat else
                 ticket.zone.name if ticket.zone else
                 ticket.ticket_type.name if ticket.ticket_type else "Ticket")
        issued.append({"id": ticket.id, "ticket_code": ticket.ticket_code,
                       "label": label, "seat_id": ticket.seat_id,
                       "zone_id": ticket.zone_id, "ticket_type_id": ticket.ticket_type_id,
                       "price_paid": ticket.price_paid, "status": ticket.status})
    result = {"id": booking.id, "event_id": booking.event_id, "tickets": booking.tickets,
              "status": effective_status(booking), "payment_status": booking.payment_status,
              "total_amount": booking.total_amount, "currency": "INR", "expires_at": as_utc(booking.expires_at),
              "booking_time": as_utc(booking.booking_time), "items": items, "ticket_details": issued,
              "payment": ({"id": booking.payment.id, "status": booking.payment.status,
                            "amount": booking.payment.amount, "transaction_id": booking.payment.transaction_id}
                           if booking.payment else None)}
    if include_event:
        e = booking.event
        result["event"] = {"id": e.id, "title": e.title, "date_time": e.date_time,
                           "location": e.location, "category": e.category,
                           "image_url": e.image_url, "inventory_type": e.inventory_type} if e else None
    return result
