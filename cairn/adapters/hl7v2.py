# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
CAIRN HL7 v2 Adapter.

Parses HL7 v2 messages into FM-2 EventCollections.

Supported message types:
    - ORU^R01  (Observation Result — lab reports)
    - ADT^A01  (Admit/Transfer/Discharge — encounters)
    - RXA      (Pharmacy Administration — medications)

Known issues resolved:
    - MSH field indexing: MSH-9 contains message type (field index 8, 0-based)
    - HL7 datetime parsing: variable length 8–14 chars (YYYYMMDDHHMMSS)
    - OBX-7 (reference range) and OBX-8 (abnormal flag) must be explicitly mapped
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

from cairn.core.allen import TimeInterval
from cairn.core.event import EventCollection, FMEvent
from cairn.core.type_dag import TypeNode


def _parse_hl7_dt(hl7_str: str) -> Optional[datetime]:
    """
    Parse HL7 v2 datetime string (variable length: YYYYMMDD to YYYYMMDDHHMMSS).

    HL7 datetime formats:
        YYYYMMDD            (8 chars)
        YYYYMMDDHHMM        (12 chars)
        YYYYMMDDHHMMSS      (14 chars)
        YYYYMMDDHHMMSS.ffff (19 chars)
    """
    s = hl7_str.strip()
    # Remove timezone suffix (+/-HHMM)
    s = re.sub(r"[+-]\d{4}$", "", s)
    # Remove fractional seconds
    s = re.sub(r"\.\d+$", "", s)

    formats = [
        ("%Y%m%d%H%M%S", 14),
        ("%Y%m%d%H%M",   12),
        ("%Y%m%d",        8),
    ]
    for fmt, length in formats:
        if len(s) >= length:
            try:
                return datetime.strptime(s[:length], fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def _field(segment: list[str], index: int) -> str:
    """Safely get a field from a parsed HL7 segment (0-based index)."""
    try:
        return segment[index].strip()
    except IndexError:
        return ""


def _component(field_str: str, index: int) -> str:
    """Get component from a field string (0-based, ^ separated)."""
    parts = field_str.split("^")
    try:
        return parts[index].strip()
    except IndexError:
        return ""


class HL7v2Adapter:
    """
    Parses HL7 v2 messages into FM-2 EventCollections.

    Usage:
        adapter = HL7v2Adapter()
        events = adapter.parse_message(hl7_text)
        events = adapter.parse_file("message.hl7")
    """

    SOURCE_LABEL = "HL7-v2"
    FIELD_SEP = "|"
    SEGMENT_SEP = "\r"

    def parse_file(self, path: str) -> EventCollection:
        import pathlib
        text = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
        return self.parse_message(text)

    def parse_message(self, message: str) -> EventCollection:
        """Parse a complete HL7 v2 message into an EventCollection."""
        collection = EventCollection(source_label=self.SOURCE_LABEL)

        # Normalise line endings
        message = message.replace("\r\n", "\r").replace("\n", "\r")
        segments = [s for s in message.split("\r") if s.strip()]

        msg_type = ""
        msh: list[str] = []

        # Parse MSH first to determine message type
        for seg in segments:
            fields = seg.split(self.FIELD_SEP)
            if fields[0] == "MSH":
                msh = fields
                # MSH-9: Message Type (field index 8, because MSH-1=field sep counts as field 1)
                msg_type = _component(_field(msh, 8), 0)
                break

        if msg_type == "ORU":
            self._parse_oru_r01(segments, collection)
        elif msg_type == "ADT":
            self._parse_adt_a01(segments, collection)
        else:
            # Try to extract RXA segments regardless
            self._parse_rxa(segments, collection)

        return collection

    # ── ORU^R01 — Observation Results ─────────────────────────────────────

    def _parse_oru_r01(self, segments: list[str], collection: EventCollection) -> None:
        """
        Parse ORU^R01 message.

        Key OBX fields:
            OBX-3  : Observation identifier (LOINC code)
            OBX-5  : Observation value
            OBX-6  : Units
            OBX-7  : References range   ← often lost in FHIR mapping!
            OBX-8  : Abnormal flags      ← often lost in FHIR mapping!
            OBX-14 : Date/time of observation
        """
        obr_dt: Optional[str] = None

        for seg in segments:
            fields = seg.split(self.FIELD_SEP)
            seg_id = fields[0]

            if seg_id == "OBR" and len(fields) > 7:
                obr_dt = _field(fields, 7)  # OBR-7: Observation Date/Time

            if seg_id == "OBX" and len(fields) > 5:
                code = _component(_field(fields, 3), 0)   # OBX-3.1: code
                system_name = _component(_field(fields, 3), 2)  # OBX-3.3: system
                system = "http://loinc.org" if "LN" in system_name.upper() else system_name
                value_raw = _field(fields, 5)             # OBX-5
                unit = _component(_field(fields, 6), 1)   # OBX-6.1: unit
                ref_range = _field(fields, 7)             # OBX-7: reference range
                abn_flag = _field(fields, 8)              # OBX-8: H/L/N/etc.
                obs_dt = _field(fields, 14) or obr_dt     # OBX-14 or OBR-7

                if not code:
                    continue

                # Build temporal: observation datetime ±1s (point → micro interval)
                start = _parse_hl7_dt(obs_dt) if obs_dt else None
                interval: Optional[TimeInterval] = None
                if start:
                    from datetime import timedelta
                    interval = TimeInterval(start=start, end=start + timedelta(seconds=1))

                value_set = {
                    "code": code,
                    "system": system,
                    "value": value_raw,
                    "unit": unit,
                }
                # Preserve reference range and abnormal flag — key SILD detection points
                if ref_range:
                    value_set["referenceRange"] = ref_range
                if abn_flag:
                    value_set["interpretation"] = abn_flag

                collection.add(FMEvent(
                    event_type=TypeNode("LabResult", system="cairn"),
                    temporal=interval,
                    value_set=value_set,
                    provenance={"source": "HL7v2-ORU", "segment": "OBX"},
                ))

    # ── ADT^A01 — Admission ───────────────────────────────────────────────

    def _parse_adt_a01(self, segments: list[str], collection: EventCollection) -> None:
        """
        Parse ADT^A01 (Admit) message.

        PV1-44: Admit date/time
        PV1-45: Discharge date/time
        DG1   : Diagnosis segments (can be multiple)
        """
        admit_dt: Optional[str] = None
        discharge_dt: Optional[str] = None
        diagnoses: list[dict] = []

        for seg in segments:
            fields = seg.split(self.FIELD_SEP)
            seg_id = fields[0]

            if seg_id == "PV1":
                admit_dt = _field(fields, 44)     # PV1-44
                discharge_dt = _field(fields, 45)  # PV1-45

            if seg_id == "DG1" and len(fields) > 3:
                code = _component(_field(fields, 3), 0)
                system_raw = _component(_field(fields, 3), 2)
                diag_type = _field(fields, 6)  # DG1-6: diagnosis type (A=Admission)
                certainty = _field(fields, 8)  # DG1-8: diagnosis certainty (if present)
                diagnoses.append({
                    "code": code,
                    "system": system_raw,
                    "role": diag_type,
                    "certainty": certainty,
                })

        interval = None
        if admit_dt:
            start = _parse_hl7_dt(admit_dt)
            end = _parse_hl7_dt(discharge_dt) if discharge_dt else None
            if start and end and start < end:
                interval = TimeInterval(start=start, end=end)

        collection.add(FMEvent(
            event_type=TypeNode("InpatientEncounter", system="cairn"),
            temporal=interval,
            value_set={
                "code": "encounter",
                "diagnoses": diagnoses,
                "diagnosisCount": len(diagnoses),
            },
            provenance={"source": "HL7v2-ADT", "segment": "PV1+DG1"},
        ))

    # ── RXA — Pharmacy Administration ─────────────────────────────────────

    def _parse_rxa(self, segments: list[str], collection: EventCollection) -> None:
        """
        Parse RXA (Pharmacy/Treatment Administration) segments.

        RXA-3: Date/time start of administration
        RXA-4: Date/time end of administration
        RXA-5: Administered code (ATC / local)
        RXA-6: Administered amount
        RXA-7: Administered units
        """
        for seg in segments:
            fields = seg.split(self.FIELD_SEP)
            if fields[0] != "RXA" or len(fields) < 7:
                continue

            start_str = _field(fields, 3)
            end_str = _field(fields, 4)
            code = _component(_field(fields, 5), 0)
            amount = _field(fields, 6)
            unit = _component(_field(fields, 7), 1)

            if not code:
                continue

            start = _parse_hl7_dt(start_str) if start_str else None
            end = _parse_hl7_dt(end_str) if end_str else None
            interval = None
            if start and end and start < end:
                interval = TimeInterval(start=start, end=end)
            elif start:
                from datetime import timedelta
                interval = TimeInterval(start=start, end=start + timedelta(seconds=1))

            collection.add(FMEvent(
                event_type=TypeNode("MedicationAdmin", system="cairn"),
                temporal=interval,
                value_set={"code": code, "amount": amount, "unit": unit},
                provenance={"source": "HL7v2-RXA", "segment": "RXA"},
            ))
