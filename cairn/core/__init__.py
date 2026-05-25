# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""FM-2 Core — Type DAG, Allen Algebra, Event Model, Homomorphism."""

from cairn.core.allen import AllenRelation, TimeInterval, allen_relation, inverse_relation
from cairn.core.event import EventCollection, FMEvent
from cairn.core.homomorphism import HomomorphismChecker, HomomorphismResult, HomomorphismViolation
from cairn.core.type_dag import TypeDAG, TypeNode, build_clinical_type_dag

__all__ = [
    "AllenRelation",
    "TimeInterval",
    "allen_relation",
    "inverse_relation",
    "FMEvent",
    "EventCollection",
    "HomomorphismChecker",
    "HomomorphismResult",
    "HomomorphismViolation",
    "TypeDAG",
    "TypeNode",
    "build_clinical_type_dag",
]
