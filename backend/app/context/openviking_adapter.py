"""Business adapter over the official OpenViking Python HTTP SDK.

OpenViking owns resource ingestion, retrieval, session archival, and memory
extraction.  This module deliberately does not recreate any of those features.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from openviking import AsyncHTTPClient

from app.config import settings


class OpenVikingAdapter:
    """Use the official client while keeping application-specific IDs private."""

    def __init__(self, client: Optional[Any] = None) -> None:
        self._bypass_proxy_for_local_service()
        self._client = client or AsyncHTTPClient(
            url=settings.openviking_url,
            api_key=settings.openviking_api_key or None,
            timeout=settings.openviking_timeout_seconds,
        )
        self._initialized = client is not None

    @staticmethod
    def _bypass_proxy_for_local_service() -> None:
        """Prevent inherited proxy variables from intercepting loopback SDK calls."""
        host = urlparse(settings.openviking_url).hostname
        if host not in {"localhost", "127.0.0.1", "::1"}:
            return
        existing = os.environ.get("NO_PROXY", "")
        entries = {item.strip() for item in existing.split(",") if item.strip()}
        entries.update({"localhost", "127.0.0.1", "::1"})
        os.environ["NO_PROXY"] = ",".join(sorted(entries))

    @property
    def client(self) -> Any:
        return self._client

    async def _initialize(self) -> None:
        if not self._initialized:
            await self._client.initialize()
            self._initialized = True

    @staticmethod
    def session_id(application_session_id: str) -> str:
        """Avoid publishing a browser-controlled session ID to another service."""
        digest = hashlib.sha256(application_session_id.encode("utf-8")).hexdigest()
        return f"troubleshooter-{digest[:32]}"

    async def import_resource(
        self,
        path: Path,
        *,
        target_uri: Optional[str] = None,
        wait: bool = True,
    ) -> Dict[str, Any]:
        """Delegate local file/directory ingestion to OpenViking."""
        await self._initialize()
        return await self._client.add_resource(
            str(path), to=target_uri or settings.openviking_resource_uri, wait=wait
        )

    async def find(self, query: str, *, limit: int = 5) -> Dict[str, Any]:
        """Execute the official semantic ``find`` API against imported resources."""
        await self._initialize()
        return await self._client.find(
            query=query,
            target_uri=settings.openviking_resource_uri,
            limit=limit,
        )

    async def ensure_session(self, application_session_id: str) -> str:
        """Create (or load) the official OpenViking session for this browser session."""
        await self._initialize()
        session_id = self.session_id(application_session_id)
        await self._client.get_session(session_id, auto_create=True)
        return session_id

    async def get_session_context(self, application_session_id: str) -> Dict[str, Any]:
        await self._initialize()
        session_id = await self.ensure_session(application_session_id)
        return await self._client.get_session_context(
            session_id, token_budget=settings.openviking_session_token_budget
        )

    async def add_message(
        self, application_session_id: str, role: str, content: str
    ) -> Dict[str, Any]:
        await self._initialize()
        session_id = await self.ensure_session(application_session_id)
        return await self._client.add_message(session_id, role=role, content=content)

    async def commit(self, application_session_id: str) -> Dict[str, Any]:
        await self._initialize()
        session_id = await self.ensure_session(application_session_id)
        return await self._client.commit_session(session_id)

    async def close(self) -> None:
        if self._initialized:
            await self._client.close()


openviking_adapter = OpenVikingAdapter()
