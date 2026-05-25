# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""CAIRN Adapters — FHIR R4, HL7 v2, CSV/DataFrame."""

from cairn.adapters.csv_df import CSVAdapter
from cairn.adapters.fhir_r4 import FHIRAdapter
from cairn.adapters.hl7v2 import HL7v2Adapter

__all__ = ["FHIRAdapter", "HL7v2Adapter", "CSVAdapter"]
