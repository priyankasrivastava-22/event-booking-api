from sqlalchemy.orm import Session                               # Database session

from services.inventory_service import InventoryService          # Single source of truth for release logic


def release_expired_inventory(db: Session, batch_size: int = 100) -> int:  # Release all expired inventory holds
    """Sweep every expired booking hold and release it.

    Delegates to InventoryService.release_expired_holds()  -  the same logic
    the API's manual /release-expired endpoint uses  -  instead of duplicating
    the release rules here. That single source of truth is what correctly
    releases seats, zone slots, AND passes (decrementing EventZone/TicketType
    locked_count as needed), rather than only touching raw seat inventory.

    Runs in a loop so a single call sweeps everything currently expired,
    not just one batch  -  safe to call from a scheduler on any interval.
    """
    service = InventoryService(db)
    total_released = 0

    while True:
        released = service.release_expired_holds(batch_size=batch_size)
        total_released += released
        if released < batch_size:
            break

    return total_released