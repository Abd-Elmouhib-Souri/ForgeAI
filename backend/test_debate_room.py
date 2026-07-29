import asyncio
import json

from app.agents.debate_room_graph import DebateRoomGraph


async def main():
    graph = DebateRoomGraph()

    result = await graph.run(
        project_id=13,
        title="MedStock Tunisia",
        description=(
            "Application SaaS pour aider les pharmacies tunisiennes à prévoir "
            "les ruptures de stock de médicaments avec l'intelligence artificielle."
        ),
        industry="HealthTech",
        region="Tunisie",
        analysis_data={
            "startup_score": {
                "innovation": 7,
                "feasibility": 6,
                "profitability": 7,
                "scalability": 6,
                "global_score": 6.5,
            },
            "competitive_analysis": {
                "source_based": True,
                "confidence_level": "high",
                "local_competitors_count": 2,
                "direct_competitors": [
                    "InfoPharma.tn",
                    "PharmaSoft",
                ],
                "market_gap": (
                    "Le gap exploitable est la prédiction intelligente "
                    "des ruptures de stock."
                ),
            },
            "financial_estimation": {
                "mvp_budget_estimate": "45 000 - 75 000 TND",
                "financial_risk_level": "medium",
            },
        },
        max_rounds=3,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())