# SPDX-FileCopyrightText: 2026 Friedhelm Matten / ISCaD GmbH
# SPDX-License-Identifier: AGPL-3.0-only
"""CAIRN FastAPI REST API."""

from cairn.api.app import app, serve

__all__ = ["app", "serve"]
