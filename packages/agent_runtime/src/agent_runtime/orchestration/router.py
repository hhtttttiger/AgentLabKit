"""AgentRouter — resolves a handoff reason to a structured HandoffRouteTarget.

The router reads ``handoff_policy_json`` routes and applies keyword/regex
matching against the handoff reason string.  All logic is deterministic and
pure (no I/O) so it can be unit-tested without stubs.

Route precedence (first match wins):
1. Exact substring match (case-insensitive) against ``route.match``
2. Regex match when ``route.match`` looks like a pattern (contains ``|`` or ``^``)
3. Fallback to ``default_target`` (``"human"`` unless overridden)

Schema for ``handoff_policy_json``::

    {
      "default_target": "human",          # or an agent_key string
      "routes": [
        {
          "match": "refund|退款",
          "target_type": "agent",
          "target_agent_key": "refund-specialist"
        },
        ...
      ],
      "allow_llm_routing": true,
      "max_chain_depth": 3
    }
"""

from __future__ import annotations

import logging
import re
from typing import Any, Literal

from .contracts import HandoffRouteTarget

logger = logging.getLogger(__name__)


class AgentRouter:
    """Resolves a handoff reason to a :class:`HandoffRouteTarget`.

    Instantiate once per agent definition and reuse across turns.

    Example::

        policy = {
            "routes": [{"match": "refund", "target_type": "agent",
                         "target_agent_key": "refund-agent"}]
        }
        router = AgentRouter(policy)
        target = router.resolve("I need a refund")
        # HandoffRouteTarget(target_type="agent", target_agent_key="refund-agent")
    """

    def __init__(self, handoff_policy: dict[str, Any]) -> None:
        self._policy = handoff_policy
        self._routes: list[dict[str, Any]] = handoff_policy.get("routes", [])
        self._default: str = handoff_policy.get("default_target", "human")
        self._allow_llm_routing: bool = bool(handoff_policy.get("allow_llm_routing", False))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(
        self,
        handoff_reason: str | None,
        *,
        llm_target_type: Literal["human", "agent"] | None = None,
        llm_target_agent: str | None = None,
        available_agents: list[str] | None = None,
    ) -> HandoffRouteTarget:
        """Resolve a handoff to a concrete target.

        Args:
            handoff_reason: Free-text reason emitted by the LLM.
            llm_target_type: Explicit ``handoff_target_type`` from the LLM
                (when ``allow_llm_routing`` is enabled).
            llm_target_agent: Explicit ``handoff_target_agent`` from the LLM.
            available_agents: Optional allowlist; agent targets not in this
                list are rejected and fall back to the default.

        Returns:
            A :class:`HandoffRouteTarget` — never raises.
        """
        # 1. LLM-specified routing (when explicitly enabled)
        if self._allow_llm_routing and llm_target_type == "agent" and llm_target_agent:
            if available_agents is None or llm_target_agent in available_agents:
                logger.debug(
                    "agent_router llm_routing agent_key=%s", llm_target_agent
                )
                return HandoffRouteTarget(
                    target_type="agent",
                    target_agent_key=llm_target_agent,
                    reason=handoff_reason,
                )
            logger.warning(
                "agent_router llm_routing rejected unknown agent_key=%s",
                llm_target_agent,
            )

        # 2. Static route matching
        if handoff_reason and self._routes:
            matched = self._match_routes(handoff_reason, available_agents)
            if matched is not None:
                return matched

        # 3. Default fallback
        return self._build_default(handoff_reason)

    def build_handoff_instructions(self) -> str:
        """Return a system-prompt snippet describing available agent routes.

        Returns an empty string when no agent routes are configured.
        """
        agent_routes = [
            r for r in self._routes if r.get("target_type") == "agent"
        ]
        if not agent_routes:
            return ""
        lines = ["You can hand off to the following specialist agents:"]
        for route in agent_routes:
            lines.append(
                f"- {route['target_agent_key']}: handles topics matching '{route['match']}'"
            )
        if self._allow_llm_routing:
            lines.append(
                "Set handoff_target_type='agent' and handoff_target_agent to the agent key."
            )
        lines.append("Only hand off to a human if no specialist agent matches.")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _match_routes(
        self,
        reason: str,
        available_agents: list[str] | None,
    ) -> HandoffRouteTarget | None:
        reason_lower = reason.lower()
        for route in self._routes:
            pattern: str = route.get("match", "")
            if not pattern:
                continue
            if self._matches_pattern(reason_lower, pattern.lower()):
                target_type: str = route.get("target_type", "human")
                target_key: str | None = route.get("target_agent_key")
                if target_type == "agent":
                    if target_key is None:
                        logger.warning("agent_router route missing target_agent_key")
                        continue
                    if available_agents is not None and target_key not in available_agents:
                        logger.warning(
                            "agent_router route target_agent_key=%s not in available_agents",
                            target_key,
                        )
                        continue
                logger.debug(
                    "agent_router matched pattern=%s → target_type=%s target_key=%s",
                    pattern,
                    target_type,
                    target_key,
                )
                return HandoffRouteTarget(
                    target_type=target_type,  # type: ignore[arg-type]
                    target_agent_key=target_key,
                    reason=reason,
                )
        return None

    @staticmethod
    def _matches_pattern(text: str, pattern: str) -> bool:
        """Match text against a keyword/regex pattern."""
        try:
            return bool(re.search(pattern, text))
        except re.error:
            # Pattern is not valid regex; fall back to substring
            return pattern in text

    def _build_default(self, reason: str | None) -> HandoffRouteTarget:
        if self._default == "human":
            return HandoffRouteTarget(target_type="human", reason=reason)
        # Non-human default means route to a specific agent key
        return HandoffRouteTarget(
            target_type="agent",
            target_agent_key=self._default,
            reason=reason,
        )
