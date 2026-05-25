"""
Unit tests — CAIRN FastAPI REST API.

Tests basic API endpoints using FastAPI's TestClient.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cairn.api.app import app

client = TestClient(app)

# Minimal valid FHIR Bundle for testing
MINIMAL_BUNDLE: dict = {
    "resourceType": "Bundle",
    "type": "collection",
    "entry": [],
}


class TestHealthEndpoint:

    def test_get_health_returns_200(self):
        """GET /health should return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_get_health_returns_ok_status(self):
        """GET /health body should contain status=ok."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_get_health_includes_version(self):
        """GET /health should include version info."""
        response = client.get("/health")
        data = response.json()
        assert "version" in data


class TestVerifyEndpoint:

    def test_post_verify_with_empty_bundles_returns_200(self):
        """POST /verify with minimal valid JSON body should return 200."""
        payload = {
            "cdr_bundle": MINIMAL_BUNDLE,
            "fhir_bundle": MINIMAL_BUNDLE,
            "mapping_version": "1.0.0",
        }
        response = client.post("/verify", json=payload)
        assert response.status_code == 200

    def test_post_verify_returns_report_structure(self):
        """POST /verify should return a report with expected keys."""
        payload = {
            "cdr_bundle": MINIMAL_BUNDLE,
            "fhir_bundle": MINIMAL_BUNDLE,
        }
        response = client.post("/verify", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "findings" in data
        assert "summary" in data
