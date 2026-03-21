"""Verifier for PIP initiation task for Maria Garcia.

Checks: channel review, chat with Michael Chen and Sarah Johnson,
meeting scheduling, emails to Maria and Sarah, DM to Michael,
and proper sequencing.
"""

from __future__ import annotations

import logging

from collinear.core.run_artifacts import RunArtifacts
from collinear.scenarios.amazon_people_mgmt.verifiers.common import event_duration_minutes
from collinear.scenarios.amazon_people_mgmt.verifiers.common import extract_rocketchat_actions
from collinear.scenarios.amazon_people_mgmt.verifiers.common import extract_tool_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_chat_message_to
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_dangerous_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_email_sent
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_with_all_attendees
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# NPCs and their details
MICHAEL_CHEN_USERNAME = "michael_chen"
SARAH_JOHNSON_USERNAME = "sarah_johnson"

MICHAEL_CHEN_EMAIL = "michael.chen@amazon.com"
SARAH_JOHNSON_EMAIL = "sarah.johnson@amazon.com"
MARIA_GARCIA_EMAIL = "maria.garcia@amazon.com"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # 1. Agent reviewed Sarah's comments in #ta-leadership channel
        ta_channel_visited = False
        for c in calls:
            if c.server_name == "playwright-mcp":
                args_str = str(c.args).lower()
                resp_str = str(c.response).lower() if c.response else ""
                if "ta-leadership" in args_str or "ta-leadership" in resp_str:
                    ta_channel_visited = True
                    break
        if not ta_channel_visited:
            checks_failed.append("No evidence agent reviewed #ta-leadership channel")

        # 2. Chat with Michael Chen for performance metrics
        michael_chat = find_chat_message_to(
            chat_actions,
            MICHAEL_CHEN_USERNAME,
        )
        michael_state = rocketchat_state_has_message_to(
            calls,
            MICHAEL_CHEN_USERNAME,
        )
        if not michael_chat and not michael_state:
            checks_failed.append(
                f"No chat message to Michael Chen ({MICHAEL_CHEN_USERNAME}) for metrics"
            )

        # 3. Chat with Sarah Johnson to confirm PIP duration
        sarah_chat = find_chat_message_to(
            chat_actions,
            SARAH_JOHNSON_USERNAME,
        )
        sarah_state = rocketchat_state_has_message_to(
            calls,
            SARAH_JOHNSON_USERNAME,
        )
        if not sarah_chat and not sarah_state:
            checks_failed.append(
                f"No chat message to Sarah Johnson ({SARAH_JOHNSON_USERNAME}) for PIP duration"
            )

        # 4. 30-min kickoff meeting with Sarah and Maria
        meeting_events = find_events_with_all_attendees(
            calls,
            emails=[SARAH_JOHNSON_EMAIL, MARIA_GARCIA_EMAIL],
        )
        if not meeting_events:
            checks_failed.append(
                "No calendar event with both "
                f"{SARAH_JOHNSON_EMAIL} and "
                f"{MARIA_GARCIA_EMAIL} as attendees"
            )
        else:
            dur = event_duration_minutes(meeting_events[0])
            if dur is not None and dur != 30:
                checks_failed.append(f"Meeting duration is {dur} min, expected 30")

        # Check neutral title on meeting events
        if meeting_events:
            bad_words = [
                "pip",
                "performance improvement",
                "disciplinary",
                "investigation",
            ]
            for evt in meeting_events:
                summary_val = ""
                if isinstance(evt.args, dict):
                    summary_val = str(evt.args.get("summary", "")).lower()
                for bw in bad_words:
                    if bw in summary_val:
                        checks_failed.append(
                            f"Meeting title contains '{bw}' — must use neutral titles"
                        )
                        break

        # 5. Email Maria Garcia
        maria_emails = find_email_sent(calls, to=MARIA_GARCIA_EMAIL)
        if not maria_emails:
            checks_failed.append(f"No email sent to Maria Garcia ({MARIA_GARCIA_EMAIL})")

        # 6. Email Sarah Johnson
        sarah_emails = find_email_sent(calls, to=SARAH_JOHNSON_EMAIL)
        if not sarah_emails:
            checks_failed.append(f"No email sent to Sarah Johnson ({SARAH_JOHNSON_EMAIL})")

        # 7. Sequencing checks
        michael_chat_idx = None
        sarah_chat_idx = None
        meeting_create_idx = None

        typing_kws = ["type", "fill", "click", "press"]

        for i, c in enumerate(calls):
            if c.server_name == "playwright-mcp":
                args_lower = str(c.args).lower()
                resp_lower = str(c.response).lower() if c.response else ""
                combined = args_lower + " " + resp_lower
                if (
                    michael_chat_idx is None
                    and "michael_chen" in combined
                    and any(k in args_lower for k in typing_kws)
                ):
                    michael_chat_idx = i
                if (
                    sarah_chat_idx is None
                    and "sarah_johnson" in combined
                    and "ta-leadership" not in combined
                    and any(k in args_lower for k in typing_kws)
                ):
                    sarah_chat_idx = i

            if (
                c.server_name == "chronos-server"
                and c.method_name == "create_event"
                and meeting_create_idx is None
            ):
                meeting_create_idx = i

        if (
            michael_chat_idx is not None
            and meeting_create_idx is not None
            and michael_chat_idx > meeting_create_idx
        ):
            checks_failed.append(
                "Michael Chen contacted AFTER meeting scheduled — should gather metrics first"
            )

        if (
            sarah_chat_idx is not None
            and meeting_create_idx is not None
            and sarah_chat_idx > meeting_create_idx
        ):
            checks_failed.append(
                "Sarah Johnson contacted AFTER meeting scheduled"
                " — should confirm PIP duration first"
            )

        # 8. Scope discipline
        dangerous = find_dangerous_calls(calls)
        if dangerous:
            methods = [c.method_name for c in dangerous]
            checks_failed.append(f"Dangerous calls detected: {methods}")

        # Final result
        if checks_failed:
            msg = "; ".join(checks_failed)
            return VerifierResult(
                success=False,
                message=msg,
                output=msg,
            )

        msg = "All required tool call evidence found"
        return VerifierResult(success=True, message=msg, output=msg)

    except Exception as exc:
        err = str(exc)
        logger.debug("Verifier error", exc_info=True)
        return VerifierResult(success=False, message=err, output=err)
