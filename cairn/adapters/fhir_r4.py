# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
CAIRN FHIR R4 Adapter.

Converts FHIR R4 Bundles and individual resources into FM-2 EventCollections.

Supported resource types:
    - Observation       (lab results, vital signs)
    - Condition         (diagnoses, problems)
    - Procedure         (surgical, anaesthesia)
    - MedicationRequest (prescriptions)
    - AllergyIntolerance (allergies, intolerances)
    - Encounter         (with Condition.use roles and diagnosis certainty)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from cairn.core.allen import TimeInterval
from cairn.core.event import EventCollection, FMEvent
from cairn.core.type_dag import TypeNode


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    """Parse FHIR datetime string to Python datetime."""
    if not s:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(s[:25], fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def _make_interval(start_str: Optional[str], end_str: Optional[str]) -> Optional[TimeInterval]:
    """
    Build a TimeInterval from FHIR date strings.
    Returns None if dates are missing or interval would be non-positive.
    """
    start = _parse_dt(start_str)
    end = _parse_dt(end_str)
    if start is None or end is None:
        return None
    if start >= end:
        return None
    try:
        return TimeInterval(start=start, end=end)
    except ValueError:
        return None


def _extract_code(coding_list: list[dict]) -> tuple[Optional[str], Optional[str]]:
    """Extract (code, system) from a FHIR coding array."""
    for c in coding_list:
        if c.get("code"):
            return c.get("code"), c.get("system")
    return None, None


class FHIRAdapter:
    """
    Converts FHIR R4 resources/bundles to FM-2 EventCollections.

    Usage:
        adapter = FHIRAdapter()
        events = adapter.load_bundle_file("bundle.json")
        # or
        events = adapter.load_bundle(bundle_dict)
    """

    SOURCE_LABEL = "FHIR-R4"

    def load_bundle_file(self, path: str | Path) -> EventCollection:
        """Load a FHIR Bundle from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return self.load_bundle(data)

    def load_bundle(self, bundle: dict[str, Any]) -> EventCollection:
        """Convert a FHIR Bundle dict to an EventCollection."""
        collection = EventCollection(source_label=self.SOURCE_LABEL)
        entries = bundle.get("entry", [])
        for entry in entries:
            resource = entry.get("resource", {})
            event = self._convert_resource(resource)
            if event:
                collection.add(event)
        return collection

    def _convert_resource(self, resource: dict[str, Any]) -> Optional[FMEvent]:
        rt = resource.get("resourceType", "")
        dispatch = {
            "Observation":        self._from_observation,
            "Condition":          self._from_condition,
            "Procedure":          self._from_procedure,
            "MedicationRequest":  self._from_medication_request,
            "AllergyIntolerance": self._from_allergy,
            "Encounter":          self._from_encounter,
        }
        handler = dispatch.get(rt)
        if handler:
            return handler(resource)
        return None

    # ── Resource converters ────────────────────────────────────────────────

    def _from_observation(self, r: dict) -> Optional[FMEvent]:
        coding = r.get("code", {}).get("coding", [])
        code, system = _extract_code(coding)
        if not code:
            return None

        value_set: dict[str, Any] = {"code": code, "system": system}

        # Value
        if "valueQuantity" in r:
            vq = r["valueQuantity"]
            value_set["value"] = vq.get("value")
            value_set["unit"] = vq.get("unit")

        # Reference range
        ref_ranges = r.get("referenceRange", [])
        if ref_ranges:
            rr = ref_ranges[0]
            low = rr.get("low", {}).get("value")
            high = rr.get("high", {}).get("value")
            value_set["referenceRange"] = f"{low}–{high}" if low and high else str(rr)

        # Interpretation (H/L/N flag)
        interp = r.get("interpretation", [])
        if interp:
            interp_coding = interp[0].get("coding", [])
            if interp_coding:
                value_set["interpretation"] = interp_coding[0].get("code")

        # Category (lab / vital-sign)
        cat = r.get("category", [{}])[0].get("coding", [{}])[0].get("code", "")
        type_code = "LabResult" if cat == "laboratory" else "VitalSign" if cat == "vital-signs" else "Observation"

        # Temporal
        eff = r.get("effectivePeriod", {})
        interval = _make_interval(
            eff.get("start") or r.get("effectiveDateTime"),
            eff.get("end") or r.get("effectiveDateTime"),
        )

        return FMEvent(
            event_type=TypeNode(type_code, system="cairn"),
            temporal=interval,
            value_set=value_set,
            context={"subject": r.get("subject", {}).get("reference")},
            provenance={"resourceType": "Observation", "id": r.get("id")},
        )

    def _from_condition(self, r: dict) -> Optional[FMEvent]:
        coding = r.get("code", {}).get("coding", [])
        code, system = _extract_code(coding)
        if not code:
            return None

        value_set: dict[str, Any] = {
            "code": code,
            "system": system,
            "certainty": r.get("verificationStatus", {})
                          .get("coding", [{}])[0].get("code"),
        }

        # Body site (laterality)
        body_sites = r.get("bodySite", [])
        if body_sites:
            bs_coding = body_sites[0].get("coding", [])
            if bs_coding:
                value_set["laterality"] = bs_coding[0].get("code")

        # Temporal: onset / abatement
        interval = _make_interval(
            r.get("onsetDateTime") or r.get("recordedDate"),
            r.get("abatementDateTime") or r.get("recordedDate"),
        )

        return FMEvent(
            event_type=TypeNode("Condition", system="cairn"),
            temporal=interval,
            value_set=value_set,
            context={"subject": r.get("subject", {}).get("reference")},
            provenance={"resourceType": "Condition", "id": r.get("id")},
        )

    def _from_procedure(self, r: dict) -> Optional[FMEvent]:
        coding = r.get("code", {}).get("coding", [])
        code, system = _extract_code(coding)
        if not code:
            return None

        value_set: dict[str, Any] = {"code": code, "system": system}

        period = r.get("performedPeriod", {})
        interval = _make_interval(period.get("start"), period.get("end"))

        type_code = "Anaesthesia" if "anaesth" in (r.get("code", {}).get("text", "") or "").lower() \
            else "SurgicalProcedure" if code.startswith("5-") \
            else "Procedure"

        return FMEvent(
            event_type=TypeNode(type_code, system="cairn"),
            temporal=interval,
            value_set=value_set,
            context={"subject": r.get("subject", {}).get("reference")},
            provenance={"resourceType": "Procedure", "id": r.get("id")},
        )

    def _from_medication_request(self, r: dict) -> Optional[FMEvent]:
        coding = r.get("medicationCodeableConcept", {}).get("coding", [])
        code, system = _extract_code(coding)
        if not code:
            return None

        authored = r.get("authoredOn")
        start = _parse_dt(authored)
        interval = None
        if start:
            from datetime import timedelta
            end = start + timedelta(seconds=1)
            interval = TimeInterval(start=start, end=end)

        return FMEvent(
            event_type=TypeNode("MedicationRequest", system="cairn"),
            temporal=interval,
            value_set={"code": code, "system": system, "status": r.get("status")},
            context={"subject": r.get("subject", {}).get("reference")},
            provenance={"resourceType": "MedicationRequest", "id": r.get("id")},
        )

    def _from_allergy(self, r: dict) -> Optional[FMEvent]:
        coding = r.get("code", {}).get("coding", [])
        code, system = _extract_code(coding)
        if not code:
            return None

        # FHIR AllergyIntolerance cannot represent explicit negation.
        # Absence of this resource ≠ "no known allergy" — a key SILD detection point.
        value_set: dict[str, Any] = {
            "code": code,
            "system": system,
            "clinicalStatus": r.get("clinicalStatus", {})
                               .get("coding", [{}])[0].get("code"),
            "verificationStatus": r.get("verificationStatus", {})
                                   .get("coding", [{}])[0].get("code"),
            # Note: negation=True cannot be encoded in AllergyIntolerance
            # Use Observation with SNOMED 716186003 (no known allergy) instead
        }

        recorded = r.get("recordedDate")
        start = _parse_dt(recorded)
        interval = None
        if start:
            from datetime import timedelta
            interval = TimeInterval(start=start, end=start + timedelta(seconds=1))

        return FMEvent(
            event_type=TypeNode("AllergyIntolerance", system="cairn"),
            temporal=interval,
            value_set=value_set,
            context={"subject": r.get("patient", {}).get("reference")},
            provenance={"resourceType": "AllergyIntolerance", "id": r.get("id")},
        )

    def _from_encounter(self, r: dict) -> Optional[FMEvent]:
        period = r.get("period", {})
        interval = _make_interval(period.get("start"), period.get("end"))

        diagnoses = []
        for d in r.get("diagnosis", []):
            use_coding = d.get("use", {}).get("coding", [{}])
            diagnoses.append({
                "reference": d.get("condition", {}).get("reference"),
                "use": use_coding[0].get("code") if use_coding else None,
                "rank": d.get("rank"),
            })

        return FMEvent(
            event_type=TypeNode("Encounter", system="cairn"),
            temporal=interval,
            value_set={
                "code": r.get("id", "encounter"),
                "class": r.get("class", {}).get("code"),
                "diagnoses": diagnoses,
                "diagnosisCount": len(diagnoses),
            },
            context={"subject": r.get("subject", {}).get("reference")},
            provenance={"resourceType": "Encounter", "id": r.get("id")},
        )
