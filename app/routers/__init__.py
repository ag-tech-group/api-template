# SPDX-FileCopyrightText: 2026 AG Technology Group LLC
# SPDX-License-Identifier: Apache-2.0

from app.routers.admin import router as admin_router
from app.routers.notes import router as notes_router

__all__ = ["admin_router", "notes_router"]
