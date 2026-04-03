"""Market Intelligence Service — Price-Quality Frontier & Opportunity Discovery.

Combines price, rating, risk, liquidity and compliance to trace
an efficient price-quality curve and identify opportunities.
"""
from typing import Optional
from app.modules.rating.service import GRADE_DISCOUNT_FACTORS


def calculate_frontier(credits: list[dict]) -> dict:
    """Calculate the efficient price-quality frontier.

    Args:
        credits: list of dicts with keys:
            project_id, project_name, project_type, grade, price_eur,
            rating_score, liquidity_score, volume

    Returns:
        dict with frontier points, opportunities, and stats
    """
    if not credits:
        return {"frontier": [], "opportunities": [], "stats": {}}

    # Sort by rating score descending
    sorted_credits = sorted(credits, key=lambda x: x.get("rating_score", 0), reverse=True)

    # Build the efficient frontier (convex hull upper boundary)
    frontier_points = []
    best_price_for_quality = {}

    for c in sorted_credits:
        score = c.get("rating_score", 0)
        price = c.get("price_eur", 0)
        if price <= 0:
            continue

        # Bucket by grade for frontier
        grade = c.get("grade", "D")
        if grade not in best_price_for_quality or price < best_price_for_quality[grade]["price_eur"]:
            best_price_for_quality[grade] = c

    # Frontier: best price for each quality level
    grade_order = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
    for grade in grade_order:
        if grade in best_price_for_quality:
            point = best_price_for_quality[grade]
            frontier_points.append({
                "grade": grade,
                "price_eur": point["price_eur"],
                "rating_score": point["rating_score"],
                "project_id": point.get("project_id"),
                "project_name": point.get("project_name"),
                "is_frontier": True,
            })

    # Identify opportunities: credits below the frontier price for their grade
    opportunities = []
    grade_median_prices = _calculate_grade_medians(credits)

    for c in credits:
        grade = c.get("grade", "D")
        price = c.get("price_eur", 0)
        score = c.get("rating_score", 0)
        median_price = grade_median_prices.get(grade, price)

        if price > 0 and price < median_price * 0.85 and score >= 50:
            discount_pct = (1 - price / median_price) * 100
            risk_adjusted_cost = price / GRADE_DISCOUNT_FACTORS.get(grade, 0.5)

            opportunities.append({
                "project_id": c.get("project_id"),
                "project_name": c.get("project_name"),
                "project_type": c.get("project_type"),
                "grade": grade,
                "price_eur": price,
                "median_price_eur": round(median_price, 2),
                "discount_pct": round(discount_pct, 1),
                "rating_score": score,
                "risk_adjusted_cost_eur": round(risk_adjusted_cost, 2),
                "liquidity_score": c.get("liquidity_score", 0.5),
                "opportunity_score": round(discount_pct * score / 100, 2),
                "is_opportunity": True,
            })

    # Sort opportunities by opportunity_score descending
    opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

    # Stats
    all_prices = [c["price_eur"] for c in credits if c.get("price_eur", 0) > 0]
    stats = {
        "total_credits_analyzed": len(credits),
        "frontier_points": len(frontier_points),
        "opportunities_found": len(opportunities),
        "avg_price": round(sum(all_prices) / len(all_prices), 2) if all_prices else 0,
        "min_price": min(all_prices) if all_prices else 0,
        "max_price": max(all_prices) if all_prices else 0,
        "grade_medians": grade_median_prices,
    }

    return {
        "frontier": frontier_points,
        "opportunities": opportunities[:20],  # Top 20
        "all_points": [
            {
                "project_id": c.get("project_id"),
                "project_name": c.get("project_name"),
                "project_type": c.get("project_type"),
                "grade": c.get("grade", "D"),
                "price_eur": c.get("price_eur", 0),
                "rating_score": c.get("rating_score", 0),
                "is_frontier": c.get("project_id") in {fp.get("project_id") for fp in frontier_points},
                "is_opportunity": c.get("project_id") in {op.get("project_id") for op in opportunities},
            }
            for c in credits if c.get("price_eur", 0) > 0
        ],
        "stats": stats,
    }


def suggest_rebalance(
    current_positions: list[dict],
    opportunities: list[dict],
    target_improvement: float = 10.0,
) -> list[dict]:
    """Suggest portfolio rebalancing based on frontier analysis.

    Args:
        current_positions: list of current portfolio positions with grade, price, qty
        opportunities: list of identified opportunities
        target_improvement: target score improvement percentage

    Returns:
        list of rebalancing suggestions
    """
    suggestions = []
    priority = 1

    # Find sell candidates: low-grade, expensive positions
    sell_candidates = sorted(
        [p for p in current_positions if _grade_rank(p.get("grade", "D")) >= 5],
        key=lambda x: x.get("price_eur", 0),
        reverse=True,
    )

    # Find buy candidates from opportunities
    buy_candidates = sorted(
        opportunities,
        key=lambda x: x.get("opportunity_score", 0),
        reverse=True,
    )

    for sell in sell_candidates[:5]:
        for buy in buy_candidates[:5]:
            sell_grade = sell.get("grade", "D")
            buy_grade = buy.get("grade", "D")

            if _grade_rank(buy_grade) < _grade_rank(sell_grade):
                sell_price = sell.get("price_eur", 0)
                buy_price = buy.get("price_eur", 0)

                if buy_price > 0 and sell_price > 0:
                    savings = (sell_price - buy_price) * sell.get("quantity", 1)
                    risk_adj_sell = sell_price / GRADE_DISCOUNT_FACTORS.get(sell_grade, 0.5)
                    risk_adj_buy = buy_price / GRADE_DISCOUNT_FACTORS.get(buy_grade, 0.5)

                    suggestions.append({
                        "action": "swap",
                        "sell_project_id": sell.get("project_id"),
                        "sell_project_name": sell.get("project_name"),
                        "sell_grade": sell_grade,
                        "sell_price": sell_price,
                        "buy_project_id": buy.get("project_id"),
                        "buy_project_name": buy.get("project_name"),
                        "buy_grade": buy_grade,
                        "buy_price": buy_price,
                        "quantity": sell.get("quantity", 1),
                        "reason": f"Trocar {sell_grade} (€{sell_price:.2f}) por {buy_grade} (€{buy_price:.2f}) — economia de €{savings:.2f}",
                        "risk_adjusted_savings_eur": round(risk_adj_sell - risk_adj_buy, 2),
                        "priority": priority,
                    })
                    priority += 1

    return suggestions[:10]


def _calculate_grade_medians(credits: list[dict]) -> dict:
    """Calculate median price per grade."""
    grade_prices = {}
    for c in credits:
        grade = c.get("grade", "D")
        price = c.get("price_eur", 0)
        if price > 0:
            grade_prices.setdefault(grade, []).append(price)

    medians = {}
    for grade, prices in grade_prices.items():
        sorted_prices = sorted(prices)
        n = len(sorted_prices)
        medians[grade] = sorted_prices[n // 2] if n > 0 else 0

    return medians


def _grade_rank(grade: str) -> int:
    """Return numeric rank for grade (0=AAA best, 9=D worst)."""
    order = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]
    try:
        return order.index(grade)
    except ValueError:
        return 9
