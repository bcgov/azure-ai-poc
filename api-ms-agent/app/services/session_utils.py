"""Session resolution helpers.

Routers share the same behavior:
- If client provides a session_id, honor it.
- Otherwise reuse the user's most recent session (filtered by prefix).
- If none exists (or Cosmos isn't configured), create a new session.

This keeps session-continuity behavior consistent across agents.
"""

from __future__ import annotations

from typing import Literal

from app.services.cosmos_db_service import CosmosDbService

SessionIdSource = Literal["client", "latest", "new"]


async def resolve_session_id(
    *,
    cosmos: CosmosDbService,
    user_id: str,
    requested_session_id: str | None,
    session_id_prefix: str,
) -> tuple[str | None, SessionIdSource]:
    """Resolve a session id for a request.

    Returns:
        (session_id, session_id_source)

    Notes:
        - Returns (None, "client") if the client provided None; caller can apply
          a final guard if they require a non-null string.
    """

    if requested_session_id:
        return requested_session_id, "client"

    recent_sessions = await cosmos.get_user_sessions(
        user_id,
        limit=1,
        session_id_prefix=session_id_prefix,
    )
    if recent_sessions:
        return recent_sessions[0].session_id, "latest"

    session = await cosmos.create_session(
        user_id,
        session_id_prefix=session_id_prefix,
    )
    return session.session_id, "new"
