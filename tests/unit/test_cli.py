"""
Unit tests — CAIRN CLI commands.

Tests basic CLI invocations using Click's CliRunner.
"""

from __future__ import annotations

import pytest
from click.testing import CliRunner

from cairn.cli.commands import main


class TestVersionCommand:

    def test_version_outputs_version_string(self):
        """cairn version should output a version string."""
        runner = CliRunner()
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "CAIRN" in result.output

    def test_version_contains_licence(self):
        """cairn version should mention the licence."""
        runner = CliRunner()
        result = runner.invoke(main, ["version"])
        assert result.exit_code == 0
        assert "EUPL" in result.output


class TestVerifyCommand:

    def test_verify_help_works(self):
        """cairn verify --help should succeed and describe the command."""
        runner = CliRunner()
        result = runner.invoke(main, ["verify", "--help"])
        assert result.exit_code == 0
        assert "verify" in result.output.lower() or "CDR" in result.output or "source" in result.output.lower()


class TestDriftCommand:

    def test_drift_help_works(self):
        """cairn drift --help should succeed and describe the command."""
        runner = CliRunner()
        result = runner.invoke(main, ["drift", "--help"])
        assert result.exit_code == 0
        assert "drift" in result.output.lower() or "terminology" in result.output.lower() or "source" in result.output.lower()
