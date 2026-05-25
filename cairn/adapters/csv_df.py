# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
CAIRN CSV/DataFrame Adapter.

Converts pandas DataFrames and CSV files into FM-2 EventCollections.
Column names are auto-detected using common naming conventions.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

from cairn.core.allen import TimeInterval
from cairn.core.event import EventCollection, FMEvent
from cairn.core.type_dag import TypeNode

# Column name aliases for auto-detection
CODE_ALIASES     = {"code", "icd", "loinc", "snomed", "atc", "ops", "code_value"}
SYSTEM_ALIASES   = {"system", "code_system", "terminology"}
START_ALIASES    = {"start", "start_dt", "onset", "admission", "date", "datetime", "recorded_date"}
END_ALIASES      = {"end", "end_dt", "discharge", "abatement", "end_date", "end_datetime"}
TYPE_ALIASES     = {"type", "event_type", "resource_type", "category"}
SITE_ALIASES     = {"site", "hospital", "organization", "facility", "haus"}
SYSTEM_SRC_ALIASES = {"source_system", "kis", "emr", "system_name"}


def _detect_col(df: pd.DataFrame, aliases: set[str]) -> Optional[str]:
    """Return the first column in df matching any alias (case-insensitive)."""
    cols_lower = {c.lower(): c for c in df.columns}
    for alias in aliases:
        if alias.lower() in cols_lower:
            return cols_lower[alias.lower()]
    return None


def _parse_dt(val) -> Optional[datetime]:
    if pd.isna(val):
        return None
    if isinstance(val, datetime):
        return val.replace(tzinfo=timezone.utc) if val.tzinfo is None else val
    try:
        dt = pd.to_datetime(val, utc=True).to_pydatetime()
        return dt
    except Exception:
        return None


class CSVAdapter:
    """
    Converts CSV files / pandas DataFrames to FM-2 EventCollections.

    Columns are auto-detected by common naming conventions.
    Minimum required column: a code column.
    """

    SOURCE_LABEL = "CSV"

    def load_csv(self, path: str | Path, **kwargs) -> EventCollection:
        df = pd.read_csv(path, **kwargs)
        return self.load_dataframe(df, source_label=str(path))

    def load_dataframe(
        self,
        df: pd.DataFrame,
        source_label: str = "DataFrame",
    ) -> EventCollection:
        collection = EventCollection(source_label=source_label)

        col_code    = _detect_col(df, CODE_ALIASES)
        col_system  = _detect_col(df, SYSTEM_ALIASES)
        col_start   = _detect_col(df, START_ALIASES)
        col_end     = _detect_col(df, END_ALIASES)
        col_type    = _detect_col(df, TYPE_ALIASES)
        col_site    = _detect_col(df, SITE_ALIASES)
        col_src_sys = _detect_col(df, SYSTEM_SRC_ALIASES)

        for _, row in df.iterrows():
            code = str(row[col_code]) if col_code and not pd.isna(row[col_code]) else None
            if not code:
                continue

            system = str(row[col_system]) if col_system else "local"
            type_code = str(row[col_type]) if col_type else "Observation"
            site = str(row[col_site]) if col_site else None
            src_sys = str(row[col_src_sys]) if col_src_sys else None

            # Temporal
            start = _parse_dt(row[col_start]) if col_start else None
            end   = _parse_dt(row[col_end])   if col_end   else None
            interval: Optional[TimeInterval] = None
            if start and end and start < end:
                interval = TimeInterval(start=start, end=end)
            elif start:
                interval = TimeInterval(start=start, end=start + timedelta(seconds=1))

            # Value set: all remaining columns
            value_set = {"code": code, "system": system}
            skip_cols = {col_code, col_system, col_start, col_end, col_type, col_site, col_src_sys}
            for col in df.columns:
                if col not in skip_cols and not pd.isna(row[col]):
                    value_set[col] = row[col]

            collection.add(FMEvent(
                event_type=TypeNode(type_code, system="cairn"),
                temporal=interval,
                value_set=value_set,
                context={"site": site} if site else {},
                provenance={"source": "CSV", "source_system": src_sys},
            ))

        return collection
