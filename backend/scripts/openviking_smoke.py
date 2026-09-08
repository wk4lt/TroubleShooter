"""Exercise the official OpenViking HTTP SDK against a running service.

Run after `openviking-server init` and `openviking-server`:
    PYTHONPATH=backend backend/.venv/bin/python backend/scripts/openviking_smoke.py
"""

import argparse
import asyncio
import os
import tempfile
from pathlib import Path

from openviking import AsyncHTTPClient


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=os.getenv("OPENVIKING_URL", "http://127.0.0.1:1933"))
    parser.add_argument("--api-key", default=os.getenv("OPENVIKING_API_KEY", ""))
    parser.add_argument(
        "--resource-uri",
        default=os.getenv("OPENVIKING_RESOURCE_URI", "viking://resources/troubleshooter"),
    )
    args = parser.parse_args()

    client = AsyncHTTPClient(url=args.url, api_key=args.api_key or None)
    temporary_path = ""
    try:
        await client.initialize()
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", encoding="utf-8", delete=False
        ) as document:
            document.write("# OpenViking smoke document\n\nOfficial SDK resource import test.")
            temporary_path = document.name

        imported = await client.add_resource(temporary_path, to=args.resource_uri, wait=True)
        found = await client.find(
            "official SDK resource import test", target_uri=args.resource_uri, limit=1
        )
        session = await client.create_session()
        session_id = session["session_id"]
        await client.add_message(session_id, role="user", content="Run OpenViking session smoke test")
        await client.add_message(session_id, role="assistant", content="Session message recorded")
        committed = await client.commit_session(session_id)
        print({"resource": imported, "find": found, "session": session, "commit": committed})
    finally:
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
