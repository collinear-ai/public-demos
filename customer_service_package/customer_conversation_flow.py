"""Verifier for cs-206-customer-conversation-flow.

Validates multi-customer de-escalation conversation flow:
- Frustrated customer (karen.mitchell) de-escalation over 5+ turns
- Enterprise customer (david.park) premium handling over 3+ turns
- Concurrent handling (interleaved timestamps)
- Knowledge base search usage
"""

from __future__ import annotations

from collinear.core.run_artifacts import RunArtifacts
from collinear.core.verifier import VerifierResult

from .common import call_tool
from .common import normalize_text


KAREN_USERNAME = "karen.mitchell"
DAVID_USERNAME = "david.park"
AGENT_USERNAME = "agent"
MIN_KAREN_TURNS = 5  # total karen messages (initial + responses)
MIN_DAVID_TURNS = 3  # total david messages (initial + responses)


def _get_dm_history(
    rc_url: str, username: str
) -> tuple[str | None, list[dict] | None, str | None]:
    """Return (room_id, history, error_message) for a DM room."""
    try:
        dm = call_tool(rc_url, "rocketchat_get_dm_room", {"username": username})
    except Exception as exc:
        return None, None, f"rocketchat_get_dm_room failed for {username}: {exc}"
    if not isinstance(dm, dict):
        return None, None, f"Could not get DM room for {username} (got {type(dm).__name__})"
    room_id = dm.get("room_id")
    if not isinstance(room_id, str) or not room_id:
        return None, None, f"Missing room_id for {username} (response: {dm})"
    try:
        history = call_tool(
            rc_url, "rocketchat_get_room_history", {"room_id": room_id, "count": 200}
        )
    except Exception as exc:
        return room_id, None, f"rocketchat_get_room_history failed for {username}: {exc}"
    if not isinstance(history, list):
        return room_id, None, f"Could not get history for {username} (got {type(history).__name__})"
    return room_id, history, None


def _count_user_messages(history: list[dict], username: str) -> int:
    """Count messages from a specific user."""
    count = 0
    for msg in history:
        if not isinstance(msg, dict):
            continue
        u = msg.get("username")
        if isinstance(u, str) and normalize_text(u) == normalize_text(username):
            count += 1
    return count


def _count_agent_messages(history: list[dict]) -> int:
    """Count messages from the agent."""
    return _count_user_messages(history, AGENT_USERNAME)


def _get_timestamps(history: list[dict], username: str) -> list[str]:
    """Get sorted timestamps for a user's messages."""
    timestamps = []
    for msg in history:
        if not isinstance(msg, dict):
            continue
        u = msg.get("username")
        ts = msg.get("ts") or msg.get("timestamp")
        if isinstance(u, str) and normalize_text(u) == normalize_text(username) and ts:
            timestamps.append(str(ts))
    return sorted(timestamps)


def _check_empathy_keywords(history: list[dict]) -> bool:
    """Check if agent used empathy/de-escalation language with Karen."""
    empathy_words = [
        "understand", "frustrat", "apologize", "sorry", "apolog",
        "acknowledge", "hear you", "appreciate your patience",
        "take ownership", "my responsibility", "resolve this",
    ]
    for msg in history:
        if not isinstance(msg, dict):
            continue
        u = msg.get("username")
        text = msg.get("text")
        if (
            isinstance(u, str)
            and normalize_text(u) == AGENT_USERNAME
            and isinstance(text, str)
        ):
            text_lower = normalize_text(text)
            if any(word in text_lower for word in empathy_words):
                return True
    return False


def _check_enterprise_urgency(history: list[dict]) -> bool:
    """Check if agent used enterprise-appropriate urgency language with David."""
    urgency_words = [
        "priority", "urgent", "immediately", "escalat", "team",
        "enterprise", "critical", "expedit", "top priority",
    ]
    for msg in history:
        if not isinstance(msg, dict):
            continue
        u = msg.get("username")
        text = msg.get("text")
        if (
            isinstance(u, str)
            and normalize_text(u) == AGENT_USERNAME
            and isinstance(text, str)
        ):
            text_lower = normalize_text(text)
            if any(word in text_lower for word in urgency_words):
                return True
    return False


def _check_concurrency(
    karen_agent_ts: list[str], david_agent_ts: list[str]
) -> bool:
    """Check if agent messages to Karen and David are interleaved (concurrent)."""
    if not karen_agent_ts or not david_agent_ts:
        return False
    # If all Karen messages come before all David messages (or vice versa), not concurrent
    karen_first = karen_agent_ts[0]
    karen_last = karen_agent_ts[-1]
    david_first = david_agent_ts[0]
    david_last = david_agent_ts[-1]
    # Interleaved means the ranges overlap
    return not (karen_last < david_first or david_last < karen_first)


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify multi-customer de-escalation conversation flow."""
    rc_url = run_artifacts.server_url("rocketchat-env")
    if not rc_url:
        return VerifierResult(success=False, message="Missing Tool Server URL for rocketchat-env")

    helpdesk_url = run_artifacts.server_url("frappe-helpdesk-env")

    errors: list[str] = []
    checks_passed = 0
    total_checks = 7

    # 1. Karen conversation — check turn count
    _, karen_history, err = _get_dm_history(rc_url, KAREN_USERNAME)
    if err or karen_history is None:
        errors.append(f"Karen DM: {err or 'no history'}")
    else:
        karen_msg_count = _count_user_messages(karen_history, KAREN_USERNAME)
        karen_agent_count = _count_agent_messages(karen_history)
        if karen_msg_count < MIN_KAREN_TURNS:
            errors.append(
                f"Karen turns insufficient: {karen_msg_count} Karen messages "
                f"(need {MIN_KAREN_TURNS}+)"
            )
        else:
            checks_passed += 1

        # 2. Karen de-escalation — empathy keywords
        if _check_empathy_keywords(karen_history):
            checks_passed += 1
        else:
            errors.append(
                "Agent did not use empathy/de-escalation language with Karen "
                "(expected: apologize, understand, frustration, etc.)"
            )

    # 3. David conversation — check turn count
    _, david_history, err = _get_dm_history(rc_url, DAVID_USERNAME)
    if err or david_history is None:
        errors.append(f"David DM: {err or 'no history'}")
    else:
        david_msg_count = _count_user_messages(david_history, DAVID_USERNAME)
        david_agent_count = _count_agent_messages(david_history)
        if david_msg_count < MIN_DAVID_TURNS:
            errors.append(
                f"David turns insufficient: {david_msg_count} David messages "
                f"(need {MIN_DAVID_TURNS}+)"
            )
        else:
            checks_passed += 1

        # 4. Enterprise-tier handling — urgency keywords
        if _check_enterprise_urgency(david_history):
            checks_passed += 1
        else:
            errors.append(
                "Agent did not use enterprise-appropriate urgency language with David "
                "(expected: priority, urgent, escalate, etc.)"
            )

    # 5. Concurrent handling — interleaved timestamps
    if karen_history and david_history:
        karen_agent_ts = _get_timestamps(karen_history, AGENT_USERNAME)
        david_agent_ts = _get_timestamps(david_history, AGENT_USERNAME)
        if _check_concurrency(karen_agent_ts, david_agent_ts):
            checks_passed += 1
        else:
            errors.append(
                "Conversations not concurrent — agent completed one conversation "
                "entirely before starting the other"
            )
    else:
        errors.append("Cannot check concurrency — missing conversation histories")

    # 6. Agent sent messages to both customers
    karen_agent = _count_agent_messages(karen_history) if karen_history else 0
    david_agent = _count_agent_messages(david_history) if david_history else 0
    if karen_agent >= 2 and david_agent >= 2:
        checks_passed += 1
    else:
        errors.append(
            f"Agent message counts too low: Karen={karen_agent}, David={david_agent} "
            f"(need 2+ each)"
        )

    # 7. Knowledge base search — check if agent searched KB
    kb_searched = False
    if helpdesk_url:
        try:
            kb_results = call_tool(
                helpdesk_url, "helpdesk_search_kb", {"query": "billing"}
            )
            # The KB exists; we check if agent's messages reference KB content
            if karen_history:
                for msg in karen_history:
                    if not isinstance(msg, dict):
                        continue
                    u = msg.get("username")
                    text = msg.get("text") or ""
                    if (
                        isinstance(u, str)
                        and normalize_text(u) == AGENT_USERNAME
                        and isinstance(text, str)
                        and ("article" in normalize_text(text)
                             or "knowledge base" in normalize_text(text)
                             or "guide" in normalize_text(text)
                             or "documentation" in normalize_text(text)
                             or "resource" in normalize_text(text)
                             or "faq" in normalize_text(text)
                             or "policy" in normalize_text(text)
                             or "billing" in normalize_text(text))
                    ):
                        kb_searched = True
                        break
            if not kb_searched and david_history:
                for msg in david_history:
                    if not isinstance(msg, dict):
                        continue
                    u = msg.get("username")
                    text = msg.get("text") or ""
                    if (
                        isinstance(u, str)
                        and normalize_text(u) == AGENT_USERNAME
                        and isinstance(text, str)
                        and ("article" in normalize_text(text)
                             or "knowledge base" in normalize_text(text)
                             or "guide" in normalize_text(text)
                             or "troubleshoot" in normalize_text(text)
                             or "performance" in normalize_text(text))
                    ):
                        kb_searched = True
                        break
        except Exception:
            pass

    if kb_searched:
        checks_passed += 1
    else:
        errors.append("No evidence of knowledge base content referenced in agent messages")

    # Final verdict
    success = checks_passed >= 5 and len(errors) <= 2
    if success:
        return VerifierResult(
            success=True,
            message=(
                f"Multi-customer conversation flow verified: {checks_passed}/{total_checks} "
                f"checks passed"
            ),
        )
    return VerifierResult(
        success=False,
        message=(
            f"Conversation flow incomplete: {checks_passed}/{total_checks} checks passed. "
            f"Failures: {'; '.join(errors)}"
        ),
    )
