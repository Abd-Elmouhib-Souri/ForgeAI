# ============================================================
# Classe parente commune à tous les agents IA de ForgeAI.
# Chaque agent spécifique (BusinessAnalyst, ProductOwner, etc.)
# hérite de cette classe et implémente sa propre méthode run().
# ============================================================
import json
import logging
from abc import ABC, abstractmethod

from app.llm.provider import LLMProvider

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    def __init__(self) -> None:
        self.llm = LLMProvider()
        logger.info(f"[{self.__class__.__name__}] Agent initialisé.")

    @abstractmethod
    async def run(self, input_data: dict) -> dict:
        pass

    def _parse_json_response(self, raw_response: str) -> dict:
        """Parse la réponse JSON du LLM. Gère le cas fréquent où le LLM
        encadre sa réponse en bloc Markdown (```json ... ```) malgré la
        consigne du prompt de ne retourner que du JSON brut."""
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            cleaned = raw_response.strip()

            # Le LLM encadre parfois sa réponse avec des backticks Markdown
            # (```  ou ```json), pas des triples quotes Python.
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = lines[1:]  # retire la ligne d'ouverture ``` ou ```json
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]  # retire la ligne de fermeture ```
                cleaned = "\n".join(lines)

            try:
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                logger.error(
                    f"[{self.__class__.__name__}] "
                    f"Impossible de parser la réponse JSON : {e}\n"
                    f"Réponse brute : {raw_response[:200]}"
                )
                return {
                    "error": "json_parse_failed",
                    "raw": raw_response[:500],
                }