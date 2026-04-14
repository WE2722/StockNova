from datetime import timedelta
from statistics import mean

from django.utils import timezone

from apps.inventory.models import Product, StockMovement


def _estimate_daily_consumption(product: Product, lookback: int = 30) -> tuple[float, int]:
    since = timezone.now() - timedelta(days=lookback)
    movements = list(product.movements.filter(created_at__gte=since)[:200])
    if not movements:
        return 0.0, 0

    grouped = {}
    for m in movements:
        day = m.created_at.date()
        delta = -m.quantity if m.movement_type == StockMovement.MovementType.DECREASE else m.quantity
        grouped.setdefault(day, 0)
        grouped[day] += delta

    daily_outflows = [abs(v) for v in grouped.values() if v < 0]
    if not daily_outflows:
        return 0.0, len(movements)

    return mean(daily_outflows), len(movements)


def _fallback_daily_consumption(product: Product) -> float:
    # Heuristic baseline when movement history is sparse.
    return max(0.25, round(product.low_stock_threshold / 21, 2))


def _risk_from_days(days_to_stockout: float) -> str:
    if days_to_stockout <= 7:
        return "high"
    if days_to_stockout <= 14:
        return "medium"
    return "low"


def predict_product_stock(product: Product) -> dict:
    observed_daily_consumption, sample_size = _estimate_daily_consumption(product)

    if product.stock <= 0:
        avg_daily_consumption = max(observed_daily_consumption, _fallback_daily_consumption(product))
        days_to_stockout = 0.0
        risk_level = "high"
    else:
        avg_daily_consumption = observed_daily_consumption if observed_daily_consumption > 0 else _fallback_daily_consumption(product)
        days_to_stockout = round(product.stock / avg_daily_consumption, 1)

        if observed_daily_consumption <= 0:
            # Boost urgency when stock already around threshold.
            if product.stock <= max(2, int(product.low_stock_threshold * 0.4)):
                risk_level = "high"
                days_to_stockout = min(days_to_stockout, 7.0)
            elif product.stock <= product.low_stock_threshold:
                risk_level = "medium"
                days_to_stockout = min(days_to_stockout, 14.0)
            else:
                risk_level = _risk_from_days(days_to_stockout)
        else:
            risk_level = _risk_from_days(days_to_stockout)

    projected_14d_usage = int(round(avg_daily_consumption * 14))
    recommended_reorder = max((product.low_stock_threshold * 2 + projected_14d_usage) - product.stock, 0)
    confidence = min(0.97, round(0.52 + (sample_size * 0.015), 2)) if sample_size else 0.55
    urgency_score = round((1 / (days_to_stockout + 1)) * 100, 2) if days_to_stockout is not None else 0.0

    return {
        "product_id": product.id,
        "sku": product.sku,
        "name": product.name,
        "current_stock": product.stock,
        "avg_daily_consumption": round(avg_daily_consumption, 2),
        "days_to_stockout": days_to_stockout,
        "risk_level": risk_level,
        "recommended_reorder": int(recommended_reorder),
        "confidence": confidence,
        "urgency_score": urgency_score,
    }


def top_risk_predictions(
    limit: int = 6,
    *,
    horizon_days: float = 21,
    include_low_risk: bool = False,
) -> list[dict]:
    predictions = [predict_product_stock(p) for p in Product.objects.select_related("category").all()]

    filtered = []
    for item in predictions:
        is_within_horizon = item["days_to_stockout"] is not None and item["days_to_stockout"] <= horizon_days
        is_risky = item["risk_level"] in {"high", "medium"}

        if include_low_risk:
            filtered.append(item)
        elif is_risky or is_within_horizon:
            filtered.append(item)

    def rank(item):
        risk_rank = {"high": 0, "medium": 1, "low": 2}.get(item["risk_level"], 3)
        days = item["days_to_stockout"] if item["days_to_stockout"] is not None else 9999
        return (risk_rank, days, -item.get("urgency_score", 0))

    return sorted(filtered, key=rank)[:limit]
