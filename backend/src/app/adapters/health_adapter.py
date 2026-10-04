from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..factory import ApplicationServiceFactory


class HealthAdapter:
    def __init__(self, services: ApplicationServiceFactory):
        self.services = services

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self.services.pipeline_loaded else "configuration_error",
            # The schema is loaded as part of the pipeline, so they start or fail together
            "schema_loaded": self.services.pipeline_loaded,
            "chat_store_loaded": self.services.chat_repo_loaded,
            "error": self.services.startup_error,
        }
