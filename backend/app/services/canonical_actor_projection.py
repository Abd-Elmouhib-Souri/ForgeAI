from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any


CONFIRMED_ACTOR_STATUSES = frozenset(
    {
        "explicit",
        "user_provided",
        "provided_by_user",
        "validated",
        "confirmed",
    }
)


DEFAULT_ROLE_ALIASES = {
    "payer": (
        "payer",
        "economic_buyer",
        "budget_owner",
    ),
    "decision_maker": (
        "decision_maker",
        "decision-maker",
    ),
    "technical_maintainer": (
        "technical_maintainer",
        "maintenance_owner",
        "maintainer",
    ),
    "demand_side": (
        "demand_side",
    ),
    "supply_side": (
        "supply_side",
    ),
    "operator_or_partner": (
        "operator_or_partner",
        "platform_operator",
    ),
    "operator": (
        "operator",
    ),
    "user": (
        "user",
        "primary_user",
        "operational_user",
    ),
}


def _mapping(
    value: Any,
) -> Mapping[str, Any]:
    if isinstance(
        value,
        Mapping,
    ):
        return value
    return {}


def _text(
    value: Any,
) -> str:
    if value is None:
        return ""
    return str(
        value
    ).strip()


def _key(
    value: Any,
) -> str:
    text = _text(
        value
    ).casefold()

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        text,
    ).strip(
        "_"
    )


def _unique_texts(
    values: Sequence[Any],
) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()

    for raw in values:
        value = _text(
            raw
        )

        key = value.casefold()

        if (
            not value
            or key in seen
        ):
            continue

        seen.add(
            key
        )
        output.append(
            value
        )

    return output


def canonical_project_context(
    value: Any,
) -> dict[str, Any]:
    """
    Return the canonical ProjectContext packet from either the packet
    itself or one of the approved compatibility containers.

    This function never infers actor roles.
    """
    queue: list[Any] = [
        value
    ]
    seen: set[int] = set()

    while queue:
        current = queue.pop(
            0
        )

        if not isinstance(
            current,
            Mapping,
        ):
            continue

        marker = id(
            current
        )

        if marker in seen:
            continue

        seen.add(
            marker
        )

        actors = current.get(
            "actors"
        )

        looks_canonical = (
            isinstance(
                actors,
                list,
            )
            or "payer_actor_names" in current
            or "decision_maker_actor_names" in current
            or current.get(
                "schema_version"
            )
            == "project_context_v3"
        )

        if looks_canonical:
            return dict(
                current
            )

        for key in (
            "project_context_packet",
            "canonical_context",
            "context_packet",
            "agent_context_packet",
        ):
            nested = current.get(
                key
            )

            if isinstance(
                nested,
                Mapping,
            ):
                queue.append(
                    nested
                )

    return {}


def _empty_record() -> dict[str, Any]:
    return {
        "value": "",
        "candidate": "",
        "status": "to_confirm",
        "values": [],
        "candidates": [],
        "source": "",
    }


def _status_from_value(
    value: Any,
) -> str:
    if isinstance(
        value,
        Mapping,
    ):
        return _text(
            value.get(
                "status"
            )
            or value.get(
                "source"
            )
            or value.get(
                "provenance"
            )
        ).casefold()

    return _text(
        value
    ).casefold()


def _candidate_from_value(
    value: Any,
) -> str:
    if isinstance(
        value,
        Mapping,
    ):
        return _text(
            value.get(
                "value"
            )
            or value.get(
                "name"
            )
            or value.get(
                "actor"
            )
            or value.get(
                "label"
            )
        )

    return _text(
        value
    )


def project_actor_roles(
    *,
    canonical: Any = None,
    structured: Any = None,
    actors: Any = None,
    provenance: Any = None,
    role_aliases: (
        Mapping[
            str,
            Sequence[str],
        ]
        | None
    ) = None,
) -> dict[str, dict[str, Any]]:
    """
    Project already-established actor authority into consumer roles.

    Authority order:

    1. Canonical ActorContext records.
    2. Explicit legacy role + explicit provenance.
    3. Canonical role-name lists as unconfirmed compatibility data.
    4. Unconfirmed legacy candidates.

    A role-name list alone never creates explicit provenance.
    """
    canonical_packet = (
        canonical_project_context(
            canonical
        )
    )

    structured_map = _mapping(
        structured
    )

    legacy_actors = _mapping(
        actors
    )

    provenance_map = _mapping(
        provenance
    )

    aliases_map: dict[
        str,
        tuple[str, ...],
    ] = {
        role: tuple(
            aliases
        )
        for role, aliases
        in (
            role_aliases
            or DEFAULT_ROLE_ALIASES
        ).items()
    }

    canonical_actors = (
        canonical_packet.get(
            "actors"
        )
        or []
    )

    if not isinstance(
        canonical_actors,
        list,
    ):
        canonical_actors = []

    # Preserve any canonical role not known by historical consumers.
    for actor in canonical_actors:
        if not isinstance(
            actor,
            Mapping,
        ):
            continue

        role = _key(
            actor.get(
                "role"
            )
        )

        if role:
            aliases_map.setdefault(
                role,
                (
                    role,
                ),
            )

    output: dict[
        str,
        dict[str, Any],
    ] = {}

    for role, aliases in aliases_map.items():
        role_key = _key(
            role
        )

        alias_keys = {
            _key(
                role
            ),
            *(
                _key(
                    alias
                )
                for alias in aliases
            ),
        }

        canonical_matches: list[
            tuple[
                str,
                bool,
            ]
        ] = []

        for actor in canonical_actors:
            if not isinstance(
                actor,
                Mapping,
            ):
                continue

            actor_role = _key(
                actor.get(
                    "role"
                )
            )

            if actor_role not in alias_keys:
                continue

            name = _text(
                actor.get(
                    "name"
                )
            )

            if not name:
                continue

            canonical_matches.append(
                (
                    name,
                    actor.get(
                        "is_explicit"
                    )
                    is True,
                )
            )

        if canonical_matches:
            candidates = _unique_texts(
                [
                    name
                    for name, _
                    in canonical_matches
                ]
            )

            explicit_values = _unique_texts(
                [
                    name
                    for name, is_explicit
                    in canonical_matches
                    if is_explicit
                ]
            )

            output[
                role
            ] = {
                "value": (
                    explicit_values[0]
                    if explicit_values
                    else ""
                ),
                "candidate": (
                    explicit_values[0]
                    if explicit_values
                    else candidates[0]
                ),
                "status": (
                    "explicit"
                    if explicit_values
                    else "to_confirm"
                ),
                "values": explicit_values,
                "candidates": candidates,
                "source": (
                    "canonical_actor_context"
                ),
            }

            continue

        raw: Any = None
        raw_key = ""
        legacy_status = ""

        ordered_keys = list(
            dict.fromkeys(
                [
                    role,
                    *aliases,
                ]
            )
        )

        for key in ordered_keys:
            for source in (
                legacy_actors,
                structured_map,
                canonical_packet,
            ):
                if (
                    key in source
                    and source.get(
                        key
                    )
                    not in (
                        None,
                        "",
                    )
                ):
                    raw = source.get(
                        key
                    )
                    raw_key = key
                    break

            if raw is not None:
                break

        candidate = _candidate_from_value(
            raw
        )

        # A scalar legacy actor value is a candidate, not provenance.
        # Inline status/provenance is meaningful only for structured
        # actor records. Explicit scalar provenance is resolved below
        # from actor_provenance / *_status fields.
        legacy_status = (
            _status_from_value(
                raw
            )
            if isinstance(
                raw,
                Mapping,
            )
            else ""
        )

        for provenance_key in (
            role,
            raw_key,
            *aliases,
        ):
            if not provenance_key:
                continue

            provenance_value = (
                provenance_map.get(
                    provenance_key
                )
            )

            legacy_status = (
                legacy_status
                or _status_from_value(
                    provenance_value
                )
            )

        for key in ordered_keys:
            for source in (
                structured_map,
                legacy_actors,
                canonical_packet,
            ):
                legacy_status = (
                    legacy_status
                    or _status_from_value(
                        source.get(
                            f"{key}_status"
                        )
                    )
                )

        if (
            candidate
            and legacy_status
            in CONFIRMED_ACTOR_STATUSES
        ):
            output[
                role
            ] = {
                "value": candidate,
                "candidate": candidate,
                "status": "explicit",
                "values": [
                    candidate
                ],
                "candidates": [
                    candidate
                ],
                "source": (
                    "legacy_confirmed"
                ),
            }

            continue

        canonical_name_values: list[str] = []

        if role_key == "payer":
            canonical_name_values = (
                _unique_texts(
                    canonical_packet.get(
                        "payer_actor_names"
                    )
                    or []
                )
            )

        elif role_key == "decision_maker":
            canonical_name_values = (
                _unique_texts(
                    canonical_packet.get(
                        "decision_maker_actor_names"
                    )
                    or []
                )
            )

        if canonical_name_values:
            output[
                role
            ] = {
                "value": "",
                "candidate": (
                    canonical_name_values[0]
                ),
                "status": "to_confirm",
                "values": [],
                "candidates": (
                    canonical_name_values
                ),
                "source": (
                    "canonical_name_list"
                ),
            }

            continue

        if candidate:
            output[
                role
            ] = {
                "value": "",
                "candidate": candidate,
                "status": "to_confirm",
                "values": [],
                "candidates": [
                    candidate
                ],
                "source": (
                    "legacy_candidate"
                ),
            }

            continue

        output[
            role
        ] = _empty_record()

    return output


def confirmed_actor_map(
    projection: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> dict[str, str]:
    """
    Return compatibility role->value entries for confirmed roles only.
    """
    output: dict[
        str,
        str,
    ] = {}

    for role, record in projection.items():
        value = _text(
            record.get(
                "value"
            )
        )

        if value:
            output[
                role
            ] = value

    return output
