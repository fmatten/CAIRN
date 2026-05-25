# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""
CAIRN FastAPI REST API.

Endpoints:
    POST /verify      — Compare CDR and FHIR bundles, return SILD report
    POST /drift       — Run terminology drift analysis
    GET  /health      — Health check
    GET  /version     — Version info
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import cairn
from cairn.adapters import FHIRAdapter
from cairn.verification import SILDAnalyzer

app = FastAPI(
    title="CAIRN",
    description="Clinical interoperability reference architecture. Built on FM-2.",
    version=cairn.__version__,
    license_info={"name": "EUPL-1.2", "url": "https://eupl.eu/1.2/en/"},
)


class VerifyRequest(BaseModel):
    cdr_bundle: dict[str, Any]
    fhir_bundle: dict[str, Any]
    mapping_version: str = "1.0.0"
    source_label: str = "CDR"
    target_label: str = "FHIR"


class HealthResponse(BaseModel):
    status: str
    version: str
    licence: str


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=cairn.__version__,
        licence=cairn.__licence__,
    )


@app.get("/version")
async def version() -> dict:
    return {
        "version": cairn.__version__,
        "licence": cairn.__licence__,
        "repository": cairn.__repository__,
        "not_a_medical_device": True,
    }


@app.post("/verify")
async def verify(request: VerifyRequest) -> dict:
    """
    Compare a CDR bundle and a FHIR bundle.
    Returns a SILD report classifying all detected information losses.
    """
    try:
        adapter = FHIRAdapter()
        cdr_events = adapter.load_bundle(request.cdr_bundle)
        fhir_events = adapter.load_bundle(request.fhir_bundle)
        cdr_events.source_label = request.source_label
        fhir_events.source_label = request.target_label

        analyzer = SILDAnalyzer()
        report = analyzer.compare(cdr_events, fhir_events, request.mapping_version)
        return report.to_dict()

    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def serve() -> None:
    """Entry point for cairn-api CLI command."""
    import uvicorn
    uvicorn.run("cairn.api.app:app", host="0.0.0.0", port=8080, reload=False)
