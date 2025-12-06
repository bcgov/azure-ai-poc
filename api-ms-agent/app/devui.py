"""Agent Framework DevUI integration helpers.

Starts DevUI in a background thread so the main FastAPI app stays responsive.
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from typing import Callable, Optional

from agent_framework.devui import serve

from app.logger import get_logger
from app.services.chat_agent import get_chat_agent_service
from app.services.orchestrator_agent import get_orchestrator_agent
from app.services.research_agent import get_deep_research_service

logger = get_logger(__name__)


def _collect_entities() -> list[object]:
    """Collect agents to expose in DevUI.

    Currently exposes:
    - Chat agent (MAF ChatAgent)
    - Orchestrator agent (MAF ChatAgent with MCP tools)
    """

    entities: list[object] = []

    try:
        chat_agent = get_chat_agent_service()._get_agent()  # noqa: SLF001 - intentional internal use
        entities.append(chat_agent)
        logger.info("devui_entity_added", entity=getattr(chat_agent, "name", "chat_agent"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("devui_chat_agent_init_failed", error=str(exc))

    try:
        orchestrator_agent = get_orchestrator_agent()._get_agent()  # noqa: SLF001
        entities.append(orchestrator_agent)
        logger.info(
            "devui_entity_added", entity=getattr(orchestrator_agent, "name", "orchestrator_agent")
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("devui_orchestrator_agent_init_failed", error=str(exc))
    try:
        research_agent = get_deep_research_service()._create_research_agent()  # noqa: SLF001
        entities.append(research_agent)
        logger.info(
            "devui_entity_added", entity=getattr(research_agent, "name", "research_agent")
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("devui_research_agent_init_failed", error=str(exc))
    return entities


class DevUIServer:
    """Manage DevUI lifecycle in a background thread."""

    def __init__(
        self,
        host: str,
        port: int,
        auto_open: bool = False,
        mode: str = "developer",
        cors_origins: Iterable[str] | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.auto_open = auto_open
        self.mode = mode
        self.cors_origins = list(cors_origins) if cors_origins else None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        """Start DevUI in a daemon thread."""

        entities = _collect_entities()

        def _run() -> None:
            try:
                serve(
                    entities=entities,
                    host=self.host,
                    port=self.port,
                    auto_open=self.auto_open,
                    cors_origins=self.cors_origins,
                    mode=self.mode,
                    stop_event=self._stop_event,
                    tracing_enabled=True,
                )
            except TypeError:
                # Older versions may not support stop_event; fall back to blocking serve
                serve(
                    entities=entities,
                    host=self.host,
                    port=self.port,
                    auto_open=self.auto_open,
                    cors_origins=self.cors_origins,
                    mode=self.mode,
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("devui_start_failed", error=str(exc))

        self._thread = threading.Thread(target=_run, name="devui-server", daemon=True)
        self._thread.start()
        logger.info("devui_thread_started", host=self.host, port=self.port, mode=self.mode)

    def stop(self) -> None:
        """Signal DevUI to stop and join the thread if running."""
        if self._stop_event.is_set():
            return

        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
            logger.info("devui_thread_stopped", host=self.host, port=self.port)


def start_devui_async(
    host: str,
    port: int,
    auto_open: bool = False,
    mode: str = "developer",
    cors_origins: Iterable[str] | None = None,
) -> DevUIServer:
    """Create and start DevUI; return the server handle for later shutdown."""

    server = DevUIServer(
        host=host,
        port=port,
        auto_open=auto_open,
        mode=mode,
        cors_origins=cors_origins,
    )
    server.start()
    return server
