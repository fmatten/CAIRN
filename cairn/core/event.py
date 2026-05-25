# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
FM-2 Universal Event Model — 6-Tuple.

Every clinical event is modelled as:

    e = (id, type, temporal, value_set, context, provenance)

where:
    id          : unique event identifier
    type        : TypeNode in the type DAG
    temporal    : TimeInterval (Allen algebra)
    value_set   : dict of clinical attribute key→value pairs
    context     : dict of contextual metadata (encounter, patient, etc.)
    provenance  : dict of source system information
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from cairn.core.allen import TimeInterval
from cairn.core.type_dag import TypeNode


@dataclass
class FMEvent:
    """
    FM-2 Universal Event — 6-Tuple.

    The canonical representation of any clinical event in CAIRN.
    Used as the common intermediate format for all adapters.
    """

    # 1. Identity
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # 2. Type (position in type DAG)
    event_type: TypeNode = field(default_factory=lambda: TypeNode("Unknown"))

    # 3. Temporal (Allen interval)
    temporal: Optional[TimeInterval] = None

    # 4. Value set (clinical attributes)
    value_set: dict[str, Any] = field(default_factory=dict)

    # 5. Context (encounter, patient, site)
    context: dict[str, Any] = field(default_factory=dict)

    # 6. Provenance (source system, adapter, mapping version)
    provenance: dict[str, Any] = field(default_factory=dict)

    def has_temporal(self) -> bool:
        return self.temporal is not None

    def get_code(self) -> Optional[str]:
        """Convenience: return primary clinical code from value_set."""
        return self.value_set.get("code")

    def get_system(self) -> Optional[str]:
        """Convenience: return terminology system from value_set."""
        return self.value_set.get("system")

    def get_laterality(self) -> Optional[str]:
        return self.value_set.get("laterality")

    def get_certainty(self) -> Optional[str]:
        return self.value_set.get("certainty") or self.value_set.get("verificationStatus")

    def get_negation(self) -> bool:
        return bool(self.value_set.get("negation", False))

    def get_site(self) -> Optional[str]:
        """Return care site / hospital identifier from context."""
        return self.context.get("site") or self.context.get("organization")

    def get_source_system(self) -> Optional[str]:
        """Return source KIS/system identifier from provenance."""
        return self.provenance.get("source_system")

    def __str__(self) -> str:
        temporal_str = str(self.temporal) if self.temporal else "no temporal"
        code = self.get_code() or "no-code"
        return f"FMEvent({self.event_type.code}|{code}|{temporal_str})"


@dataclass
class EventCollection:
    """
    An ordered collection of FMEvents from a single source.

    Represents either a CDR export or a FHIR Bundle after adapter processing.
    """

    events: list[FMEvent] = field(default_factory=list)
    source_label: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, event: FMEvent) -> None:
        self.events.append(event)

    def filter_by_type(self, type_code: str) -> "EventCollection":
        filtered = [e for e in self.events if e.event_type.code == type_code]
        return EventCollection(events=filtered, source_label=self.source_label)

    def filter_by_code(self, code: str) -> "EventCollection":
        filtered = [e for e in self.events if e.get_code() == code]
        return EventCollection(events=filtered, source_label=self.source_label)

    def filter_by_site(self, site: str) -> "EventCollection":
        filtered = [e for e in self.events if e.get_site() == site]
        return EventCollection(events=filtered, source_label=self.source_label)

    def with_temporal(self) -> "EventCollection":
        """Return only events that have a temporal component."""
        filtered = [e for e in self.events if e.has_temporal()]
        return EventCollection(events=filtered, source_label=self.source_label)

    def without_negation(self) -> "EventCollection":
        """Return only events that are NOT negated."""
        filtered = [e for e in self.events if not e.get_negation()]
        return EventCollection(events=filtered, source_label=self.source_label)

    def __len__(self) -> int:
        return len(self.events)

    def __iter__(self):  # type: ignore[override]
        return iter(self.events)

    def __repr__(self) -> str:
        return f"EventCollection(n={len(self)}, source={self.source_label!r})"
