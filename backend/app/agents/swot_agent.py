from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List

from app.services.domain_integrity_guard import normalize_output_language


class SWOTAgent:
    """Deterministic SWOT that separates internal and external factors."""

    FORMAT = "swot_v6_archetype_aware"

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        language = normalize_output_language(state.get("output_language", "fr"))
        try:
            context = self._context(state)
            if context["project_archetype"] == "two_sided_marketplace":
                result = self._marketplace_swot(context, language)
            elif context["project_archetype"] == "hardware_iot":
                result = self._hardware_swot(context, language)
            else:
                result = self._digital_swot(context, language)
            return self._finalize(result, context, language)
        except Exception:
            return self._fallback(language)

    def _hardware_swot(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        title = context["title"]
        region = context["region"]
        workflow = self._core_action(context, language)
        users = context["target_users"]
        metrics = context["success_metrics"]
        constraints = context["constraints"]
        solution = context["solution"]
        sector = context["sector"].lower()

        if language == "en":
            strengths = self._unique([
                f"A focused field use case is defined: {workflow}.",
                f"The proposed mechanism combines a physical device and an operational result: {solution}.",
                "The MVP can be evaluated with explicit field metrics rather than feature completion.",
                f"The first deployment is constrained to a concrete environment in {region or 'the launch market'}.",
                "Operational alerts and collected data can create a feedback loop that improves the product over time.",
            ] + [f"Explicit success criterion: {item}." for item in metrics[:3]])
            weaknesses = self._unique([
                "Hardware iteration, integration and repair are slower and more expensive than software-only changes.",
                "Bill of materials, assembly, installation and maintenance costs are not yet verified by quotes.",
                "Battery life, connectivity, environmental resistance and recovery after failure require field proof.",
                "The product may depend on a domain-specific dataset and repeated annotation work.",
                "A working prototype does not yet prove repeatable deployment or support capacity.",
            ] + constraints[:5])
            opportunities = self._unique([
                f"A successful pilot with {users or 'the target operators'} can create defensible field data and operating know-how.",
                "Leasing, maintenance and recurring analytics can combine one-off and recurring revenue.",
                "Technical, agricultural or industrial partners can reduce installation, validation and maintenance friction.",
                "A modular architecture can support additional environments or detection categories after the first workflow is proven.",
                "Measured reduction in manual inspections, delays or losses can support a value-based commercial offer.",
            ])
            threats = self._unique([
                "Manual labour or existing inspection routines may remain cheaper or easier for small customers.",
                "Fixed cameras, simple sensors or established monitoring systems may solve enough of the problem at lower cost.",
                "Dust, humidity, heat, uneven ground or unstable connectivity can reduce field reliability.",
                "Imported components, logistics or exchange-rate exposure can increase deployed cost and replacement time.",
                "Customers may reject the price if avoided losses or labour savings are not demonstrated.",
                "Safety, certification or liability requirements may delay deployment when applicable.",
            ])
            if any(term in sector for term in ("agri", "farm", "agriculture")):
                threats.append("Seasonality and differences between crops or greenhouses can reduce transferability of the first model.")
            recommendations = [
                f"Freeze the first workflow around: {workflow}.",
                "Create a bill of materials and obtain current supplier quotes.",
                "Test accuracy, coverage, autonomy, availability, recovery and maintenance in the real environment.",
                "Compare the robot against manual inspection and lower-cost fixed sensing alternatives.",
                "Predefine GO, PIVOT and NO-GO thresholds before the pilot.",
            ]
            summary = f"{title} has a credible hardware hypothesis, but the opportunity depends on proving field performance and total deployed cost together."
            position = f"Position {title} as a reliable solution for {workflow}, not as a broad robotics platform."
            go_no_go = "Proceed only when the pilot meets field-performance, safety, maintenance and cost thresholds."
        else:
            strengths = self._unique([
                f"Un cas d’usage terrain ciblé est défini : {workflow}.",
                f"Le mécanisme proposé combine un dispositif physique et un résultat opérationnel : {solution}.",
                "Le MVP peut être évalué par des métriques terrain explicites et non par le nombre de fonctionnalités.",
                f"Le premier déploiement est limité à un environnement concret en {region or 'marché de lancement'}.",
                "Les alertes et données collectées peuvent créer une boucle d’amélioration du produit.",
            ] + [f"Critère de réussite explicite : {item}." for item in metrics[:3]])
            weaknesses = self._unique([
                "L’itération, l’intégration et la réparation matérielles sont plus lentes et coûteuses que des modifications logicielles.",
                "La nomenclature, l’assemblage, l’installation et la maintenance ne sont pas encore validés par des devis.",
                "L’autonomie, la connectivité, la résistance à l’environnement et la reprise après panne exigent des preuves terrain.",
                "Le produit peut dépendre d’un jeu de données métier et d’un effort répété d’annotation.",
                "Un prototype fonctionnel ne prouve pas encore un déploiement et un support répétables.",
            ] + constraints[:5])
            opportunities = self._unique([
                f"Un pilote réussi avec {users or 'les opérateurs ciblés'} peut créer des données terrain et un savoir-faire défendables.",
                "La location, la maintenance et l’analyse récurrente peuvent combiner revenus ponctuels et récurrents.",
                "Des partenaires techniques, agricoles ou industriels peuvent réduire la friction d’installation, validation et maintenance.",
                "Une architecture modulaire peut couvrir d’autres environnements ou catégories après validation du premier workflow.",
                "Une réduction mesurée des inspections manuelles, délais ou pertes peut soutenir une tarification fondée sur la valeur.",
            ])
            threats = self._unique([
                "La main-d’œuvre ou les routines d’inspection existantes peuvent rester moins coûteuses ou plus simples pour les petits clients.",
                "Des caméras fixes, capteurs simples ou systèmes de monitoring établis peuvent résoudre une partie suffisante du problème à moindre coût.",
                "La poussière, l’humidité, la chaleur, le sol irrégulier ou une connectivité instable peuvent réduire la fiabilité terrain.",
                "Les composants importés, la logistique ou le change peuvent augmenter le coût déployé et le délai de remplacement.",
                "Les clients peuvent refuser le prix si les pertes évitées ou le temps économisé ne sont pas démontrés.",
                "Les exigences de sécurité, certification ou responsabilité peuvent retarder le déploiement lorsqu’elles s’appliquent.",
            ])
            if any(term in sector for term in ("agri", "agriculture")):
                threats.append("La saisonnalité et les différences entre cultures ou serres peuvent limiter la transférabilité du premier modèle.")
            recommendations = [
                f"Figer le premier workflow autour de : {workflow}.",
                "Construire la nomenclature et obtenir des devis fournisseurs actuels.",
                "Tester précision, couverture, autonomie, disponibilité, reprise et maintenance dans l’environnement réel.",
                "Comparer le robot à l’inspection manuelle et aux alternatives fixes moins coûteuses.",
                "Définir les seuils GO, PIVOT et NO-GO avant le pilote.",
            ]
            summary = f"{title} possède une hypothèse matérielle crédible, mais l’opportunité dépend de la preuve simultanée de la performance terrain et du coût total déployé."
            position = f"Positionner {title} comme une solution fiable pour {workflow}, et non comme une plateforme robotique générale."
            go_no_go = "Continuer seulement lorsque le pilote respecte les seuils de performance, sécurité, maintenance et coût."

        return self._result(strengths, weaknesses, opportunities, threats, recommendations, summary, position, go_no_go, "high")

    def _marketplace_swot(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        title = context["title"]; region = context["region"]; core = self._core_action(context, language)
        actors = context["actors"]; demand = actors.get("demand_side") or actors.get("primary_user") or context["target_users"]
        supply = actors.get("supply_side") or ("prestataires" if language != "en" else "providers")
        risks = context["risk_dimensions"]
        if language == "en":
            strengths = [f"A clear demand side ({demand}) and supply side ({supply}) can be tested around {core}.", "A constrained launch can measure liquidity and completion before scale.", "Transactions, repeat use and contribution provide objective validation metrics."]
            weaknesses = ["Both sides must be available in the same geography and time window.", "Repeat transactions and provider retention are not yet proven.", "Trust, support, cancellation and compliance create operational complexity.", "Early incentives can hide negative unit economics."]
            opportunities = [f"Concentrate the first launch in one zone or segment in {region or 'the target market'}.", "Differentiate through reliability, local operations and trust.", "Use transaction data to improve matching and repeat use.", "Build partnerships that reduce supply acquisition or compliance friction."]
            threats = risks or ["Established marketplaces or manual networks already own both sides.", "High cancellations or incidents destroy trust.", "Acquisition and incentives exceed the take rate.", "Regulatory constraints block the operating model."]
            recommendations = ["Define one completed transaction and one constrained launch market.", "Measure demand attempts, available supply, matches, completion and repeat use.", "Validate provider economics and contribution before scaling incentives.", "Predefine safety and incident responsibilities."]
            summary = f"{title} is a credible marketplace hypothesis, but success depends on liquidity, trust and positive transaction economics."
            position = f"Position {title} around reliable completion of {core} for one launch segment."
            go = "Proceed only if both sides activate, transactions repeat and contribution remains viable."
        else:
            strengths = [f"Une demande identifiable ({demand}) et une offre identifiable ({supply}) peuvent être testées autour de {core}.", "Un lancement limité permet de mesurer liquidité et réalisation avant expansion.", "Transactions, répétition et contribution fournissent des métriques objectives."]
            weaknesses = ["Les deux côtés doivent être disponibles dans la même zone et au même moment.", "Les transactions répétées et la rétention des prestataires ne sont pas prouvées.", "Confiance, support, annulations et conformité ajoutent une complexité opérationnelle.", "Les incitations initiales peuvent masquer une économie unitaire négative."]
            opportunities = [f"Concentrer le lancement sur une zone ou un segment en {region or 'marché cible'}.", "Se différencier par la fiabilité, les opérations locales et la confiance.", "Utiliser les données transactionnelles pour améliorer mise en relation et réutilisation.", "Construire des partenariats qui réduisent acquisition de l’offre ou friction réglementaire."]
            threats = risks or ["Des marketplaces établies ou réseaux manuels contrôlent déjà les deux côtés.", "Des annulations ou incidents élevés détruisent la confiance.", "Acquisition et incitations dépassent la commission.", "Des contraintes réglementaires bloquent le modèle opérationnel."]
            recommendations = ["Définir une transaction terminée et un marché de lancement limité.", "Mesurer demandes, offre disponible, mises en relation, réalisation et répétition.", "Valider l’économie des prestataires et la contribution avant d’augmenter les incitations.", "Définir à l’avance les responsabilités de sécurité et incident."]
            summary = f"{title} est une hypothèse de marketplace crédible, mais le succès dépend de la liquidité, de la confiance et d’une économie transactionnelle positive."
            position = f"Positionner {title} sur la réalisation fiable de {core} pour un seul segment de lancement."
            go = "Continuer seulement si les deux côtés s’activent, les transactions se répètent et la contribution reste viable."
        return self._result(strengths, weaknesses, opportunities, threats, recommendations, summary, position, go, "high")

    def _digital_swot(self, context: Dict[str, Any], language: str) -> Dict[str, Any]:
        title = context["title"]; core = self._core_action(context, language); region = context["region"]
        risks = context["risk_dimensions"]; users = context["target_users"]
        regulated = context["project_archetype"] == "regulated_service"
        if language == "en":
            strengths = [f"A concrete user action can be tested: {core}.", f"The value proposition is tied to a stated problem for {users or 'the target users'}.", "Activation, completion and repeat use can be measured quickly.", "A focused MVP can be iterated without building the full product."]
            weaknesses = ["User acquisition, retention and willingness to pay are not proven.", "The payer and purchasing process may remain unclear.", "A simple feature set may be copied by established products.", "Operational delivery, support or data quality may limit value."]
            if regulated: weaknesses.append("Compliance, consent and professional responsibility add cost and implementation constraints.")
            opportunities = [f"Test one audience and one repeated outcome in {region or 'the launch market'}.", "Run fast experiments to identify activation and retention drivers.", "Use partnerships to reduce distribution or fulfilment cost.", "Convert measured workflow improvement into a clearer paid offer."]
            threats = risks or ["Existing free or manual alternatives remain sufficient.", "Acquisition cost exceeds lifetime contribution.", "Trust, privacy or service failures damage adoption.", "Established products bundle the same feature."]
            recommendations = ["Test the complete core action, not only interest.", "Measure activation, repeat use, paid conversion and contribution.", "Compare against the real current alternative.", "Validate the payer with a concrete offer."]
            summary = f"{title} is testable, but value must appear in successful and repeated completion of {core}."
            position = f"Position {title} for one audience and one repeated result in {region or 'the launch market'}."
            go = "Proceed only if users complete, repeat and value the core action at viable acquisition and delivery cost."
        else:
            strengths = [f"Une action utilisateur concrète peut être testée : {core}.", f"La proposition de valeur est liée à un problème déclaré pour {users or 'les utilisateurs ciblés'}.", "Activation, réalisation et usage répété peuvent être mesurés rapidement.", "Un MVP ciblé peut être itéré sans construire le produit complet."]
            weaknesses = ["L’acquisition, la rétention et la volonté de payer ne sont pas prouvées.", "Le payeur et le processus d’achat peuvent rester flous.", "Un ensemble simple de fonctionnalités peut être copié par des produits établis.", "La réalisation opérationnelle, le support ou la qualité des données peuvent limiter la valeur."]
            if regulated: weaknesses.append("La conformité, le consentement et la responsabilité professionnelle ajoutent des coûts et contraintes.")
            opportunities = [f"Tester une audience et un résultat répété en {region or 'marché de lancement'}.", "Mener des expériences rapides sur l’activation et la rétention.", "Utiliser des partenariats pour réduire distribution ou réalisation.", "Transformer l’amélioration mesurée du workflow en offre payante plus claire."]
            threats = risks or ["Les alternatives gratuites ou manuelles restent suffisantes.", "Le coût d’acquisition dépasse la contribution vie client.", "Des échecs de confiance, confidentialité ou service réduisent l’adoption.", "Des produits établis intègrent la même fonctionnalité."]
            recommendations = ["Tester l’action principale complète, pas seulement l’intérêt.", "Mesurer activation, usage répété, conversion payante et contribution.", "Comparer avec l’alternative réellement utilisée.", "Valider le payeur avec une offre concrète."]
            summary = f"{title} est testable, mais la valeur doit apparaître dans la réalisation réussie et répétée de {core}."
            position = f"Positionner {title} pour une audience et un résultat répété en {region or 'marché de lancement'}.",
            position = position[0]
            go = "Continuer seulement si les utilisateurs réalisent, répètent et valorisent l’action principale à des coûts viables."
        return self._result(strengths, weaknesses, opportunities, threats, recommendations, summary, position, go, "high" if regulated else "medium")

    def _result(self, strengths: List[str], weaknesses: List[str], opportunities: List[str], threats: List[str], recommendations: List[str], summary: str, position: str, go_no_go: str, risk: str) -> Dict[str, Any]:
        strengths = self._unique(strengths); weaknesses = self._unique(weaknesses); opportunities = self._unique(opportunities); threats = self._unique(threats); recommendations = self._unique(recommendations)
        return {
            "format": self.FORMAT,
            "status": "completed",
            "summary": summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "threats": threats,
            "strategic_recommendations": recommendations,
            "swot_matrix": {"strengths": strengths, "weaknesses": weaknesses, "opportunities": opportunities, "threats": threats},
            "strategic_position": position,
            "go_no_go_note": go_no_go,
            "risk_level": risk,
            "confidence_level": "medium",
            "manual_review_required": True,
            "fallback_used": False,
            "error_handled": False,
            "context_locked": True,
        }

    def _finalize(self, result: Dict[str, Any], context: Dict[str, Any], language: str) -> Dict[str, Any]:
        result["output_language"] = language
        result["project_context_used"] = {key: context.get(key) for key in ("title", "sector", "region", "target_users", "problem", "solution", "business_model", "mvp_scope", "project_archetype", "validation_unit", "priority_workflows", "success_metrics", "constraints")}
        return self._clean_object(result)

    def _context(self, state: Dict[str, Any]) -> Dict[str, Any]:
        analysis = state.get("analysis_data") or {}; project_context = state.get("project_context") or {}
        intelligence = state.get("project_intelligence") or analysis.get("project_intelligence") or project_context.get("project_intelligence") or {}
        structured = state.get("structured_project_context") or analysis.get("structured_project_context") or project_context.get("structured_project_context") or intelligence.get("structured_project_context") or {}
        canonical = self._canonical_packet(state, analysis, project_context)
        users = self._list(structured.get("target_users") or canonical.get("actors") or project_context.get("target_users"))
        actors = structured.get("actors") or project_context.get("actors") or {}
        if not isinstance(actors, dict): actors = {}
        return {
            "title": self._text(structured.get("project_name") or structured.get("title") or canonical.get("project_name") or project_context.get("title") or state.get("title"), "Project"),
            "sector": self._text(structured.get("sector") or structured.get("industry") or canonical.get("domain_label") or project_context.get("industry") or state.get("industry")),
            "region": self._text(structured.get("target_region") or structured.get("market_region") or canonical.get("target_region") or project_context.get("market_region") or state.get("region")),
            "target_users": ", ".join(users),
            "target_user_list": users,
            "problem": self._packet_text(structured.get("problem") or structured.get("core_problem") or canonical.get("problem") or project_context.get("problem"), "the identified problem"),
            "solution": self._packet_text(structured.get("solution") or canonical.get("solution") or project_context.get("solution"), "the proposed solution"),
            "business_model": self._text(structured.get("business_model") or self._first(self._list(canonical.get("business_model_hypotheses"))) or project_context.get("business_model"), "Business model to validate"),
            "mvp_scope": ", ".join(self._list(structured.get("mvp_scope") or canonical.get("mvp_scope") or project_context.get("mvp_scope"))),
            "project_archetype": self._text(structured.get("project_archetype") or canonical.get("project_archetype") or project_context.get("project_archetype"), "generic_digital_product"),
            "validation_unit": self._packet_text(structured.get("validation_unit") or canonical.get("validation_unit")),
            "actors": actors,
            "priority_workflows": self._list(structured.get("priority_workflows") or structured.get("priority_workflow") or canonical.get("priority_workflow")),
            "success_metrics": self._list(structured.get("success_metrics") or canonical.get("success_metrics")),
            "constraints": self._list(structured.get("constraints") or canonical.get("constraints")),
            "risk_dimensions": self._list(structured.get("risk_dimensions") or project_context.get("risk_dimensions")),
        }

    def _canonical_packet(self, state: Dict[str, Any], analysis: Dict[str, Any], project_context: Dict[str, Any]) -> Dict[str, Any]:
        readiness = analysis.get("idea_readiness") or {}
        for value in (state.get("project_context_packet"), state.get("canonical_context"), analysis.get("project_context_packet"), analysis.get("canonical_context"), analysis.get("context_packet"), readiness.get("context_packet"), readiness.get("project_context_packet"), project_context.get("canonical_context")):
            if isinstance(value, dict): return value
        return {}

    def _core_action(self, context: Dict[str, Any], language: str) -> str:
        generic = {"core action", "core workflow", "réaliser l’opération terrain principale", "main field operation"}
        for value in context["priority_workflows"]:
            if value and value.lower() not in generic: return value
        if context["validation_unit"]: return context["validation_unit"]
        if context["mvp_scope"]: return context["mvp_scope"]
        return "réaliser l’action principale" if language != "en" else "complete the core action"

    def _packet_text(self, value: Any, fallback: str = "") -> str:
        if isinstance(value, dict):
            for key in ("pain", "mechanism", "core_value", "action", "result", "output", "value"):
                if value.get(key): return self._text(value[key], fallback)
            return fallback
        return self._text(value, fallback)

    def _clean_object(self, value: Any) -> Any:
        if isinstance(value, dict): return {str(k): self._clean_object(v) for k, v in value.items() if v not in (None, "", [], {})}
        if isinstance(value, list): return [self._clean_object(v) for v in value if v not in (None, "", [], {})]
        if isinstance(value, str): return re.sub(r"\s+", " ", value).strip()
        return value

    def _fallback(self, language: str) -> Dict[str, Any]:
        fr = language != "en"
        result = self._result(
            ["Le projet possède un périmètre testable." if fr else "The project has a testable scope."],
            ["Les preuves terrain restent insuffisantes." if fr else "Field evidence remains insufficient."],
            ["Un pilote limité peut produire les premières preuves." if fr else "A limited pilot can produce initial evidence."],
            ["Les alternatives actuelles peuvent rester préférées." if fr else "Current alternatives may remain preferred."],
            ["Définir les critères du pilote." if fr else "Define pilot criteria."],
            "SWOT prudente à compléter avec le contexte." if fr else "Cautious SWOT to complete with context.",
            "Positionnement à préciser." if fr else "Positioning to clarify.",
            "Continuer uniquement vers un pilote limité." if fr else "Proceed only to a limited pilot.",
            "medium",
        )
        result.update({"output_language": language, "fallback_used": True, "error_handled": True, "confidence_level": "low"})
        return result

    def _text(self, value: Any, fallback: str = "") -> str:
        if value is None: return fallback
        clean = re.sub(r"\s+", " ", str(value)).strip()
        return clean or fallback

    def _list(self, value: Any) -> List[str]:
        if value is None: return []
        if isinstance(value, dict):
            if any(key in value for key in ("action", "pain", "mechanism", "value", "name")): return [self._packet_text(value)]
            result: List[str] = []
            for item in value.values(): result.extend(self._list(item))
            return self._unique(result)
        if isinstance(value, (list, tuple, set)):
            result: List[str] = []
            for item in value: result.extend(self._list(item))
            return self._unique(result)
        text = self._text(value)
        return [text] if text else []

    def _first(self, values: Any) -> str:
        items = self._list(values)
        return items[0] if items else ""

    def _unique(self, values: Iterable[Any]) -> List[str]:
        result: List[str] = []; seen = set()
        for value in values:
            clean = self._text(value)
            if not clean: continue
            key = clean.casefold()
            if key in seen: continue
            seen.add(key); result.append(clean)
        return result