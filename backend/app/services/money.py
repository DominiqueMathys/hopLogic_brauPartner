from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")
PERCENT = Decimal("100")
QTY = Decimal("0.001")


def as_decimal(value: Decimal | int | str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    return Decimal(value)


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def quantity(value: Decimal) -> Decimal:
    return value.quantize(QTY, rounding=ROUND_HALF_UP)


def percent(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def line_amounts(
    qty: Decimal,
    unit_price: Decimal,
    discount_percent: Decimal,
    vat_rate: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return discount, net, VAT and gross, each rounded to one Rappen (0.01 CHF)."""
    base = qty * unit_price
    discount = money(base * discount_percent / PERCENT)
    net = money(base - discount)
    vat = money(net * vat_rate / PERCENT)
    gross = money(net + vat)
    return discount, net, vat, gross
