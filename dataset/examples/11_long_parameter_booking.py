"""Bad smell: Long Parameter List - esperado: Builder/Parameter Object."""


def reserve_room(
    guest_name: str,
    guest_email: str,
    guest_phone: str,
    check_in: str,
    check_out: str,
    room_type: str,
    adults: int,
    children: int,
    breakfast_included: bool,
    airport_transfer: bool,
    late_checkout: bool,
    payment_method: str,
    coupon_code: str | None,
    notes: str,
) -> dict:
    extras = []
    if breakfast_included:
        extras.append("breakfast")
    if airport_transfer:
        extras.append("airport_transfer")
    if late_checkout:
        extras.append("late_checkout")

    return {
        "guest": {"name": guest_name, "email": guest_email, "phone": guest_phone},
        "stay": {"check_in": check_in, "check_out": check_out, "room_type": room_type},
        "party": {"adults": adults, "children": children},
        "extras": extras,
        "payment_method": payment_method,
        "coupon_code": coupon_code,
        "notes": notes,
        "status": "reserved",
    }
