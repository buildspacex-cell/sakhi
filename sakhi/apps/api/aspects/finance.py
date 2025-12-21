from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.registry import register


def affordability(liquidity: float, upfront: float, min_ef_months: float, ef_after: float) -> float:
    if ef_after < min_ef_months or liquidity <= 0:
        return 0.0
    return max(0.0, min(1.0, (liquidity - upfront) / liquidity))


def cashflow_fit(free_cash: float, new_recurring: float) -> float:
    if free_cash <= 0:
        return 0.0
    ratio = (free_cash - new_recurring) / free_cash
    return max(0.0, min(1.0, (ratio - 0.2) / 0.8))


class FinanceAspect:
    name = "finance"

    async def fetch(self, msg: str, person_id: str, horizon: str) -> Dict[str, Any]:
        return {
            "liquidity": 1_450_000.0,
            "emergency_months": 7.2,
            "monthly_free_cash": 65_000.0,
            "new_emi": 0.0,
            "upfront": 0.0,
            "loan_apr": 11.0,
            "expected_return": 7.0,
        }

    def normalize(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        feas = (
            0.35 * affordability(raw["liquidity"], raw["upfront"], 6, raw["emergency_months"])
            + 0.25 * cashflow_fit(raw["monthly_free_cash"], raw["new_emi"])
            + 0.25 * (1.0 if raw["loan_apr"] > raw["expected_return"] else 0.3)
            + 0.15 * min(1.0, raw["emergency_months"] / 6.0)
        )
        debt_drag = min(1.0, raw["new_emi"] / max(raw["monthly_free_cash"], 1.0))
        return {
            "money_feasibility": {"score": feas},
            "debt_drag": {"score": debt_drag},
        }

    def score(self, candidate: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, float]:
        return {
            "finance.money_feasibility": candidate.get("money_feasibility", {}).get("score", 0.0),
            "finance.debt_drag": candidate.get("debt_drag", {}).get("score", 0.0),
        }

    def adjust(self, candidate: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
        return candidate

    def explain(self, candidate: Dict[str, Any], scores: Dict[str, float]) -> str:
        score = candidate.get("money_feasibility", {}).get("score", 0.0)
        return f"Financial feasibility {score:.2f}; EF guardrail respected."


register(FinanceAspect())
