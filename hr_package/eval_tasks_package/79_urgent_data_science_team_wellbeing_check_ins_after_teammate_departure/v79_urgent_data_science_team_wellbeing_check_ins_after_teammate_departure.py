"""Verifier for urgent Finance team wellbeing check-ins.

Verify agent consulted Catherine Moore and Thomas Reed via chat,
created check-in events, emailed Finance employees and Marcus,
and notified Sarah Johnson via chat.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_created
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.scenarios.amazon_people_mgmt.verifiers.common import was_called_before
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# NPC usernames (from task JSON npcs[].id)
CATHERINE_MOORE_USERNAME = "catherine_moore"
THOMAS_REED_USERNAME = "thomas_reed"
MARCUS_CHEN_USERNAME = "marcus_chen"
SARAH_JOHNSON_USERNAME = "sarah_johnson"
JASON_MITCHELL_USERNAME = "jason_mitchell"
AMANDA_WRIGHT_USERNAME = "amanda_wright"

# Emails
CATHERINE_MOORE_EMAIL = "catherine.moore@amazon.com"
THOMAS_REED_EMAIL = "thomas.reed@amazon.com"
MARCUS_CHEN_EMAIL = "marcus.chen@amazon.com"
JASON_MITCHELL_EMAIL = "jason.mitchell@amazon.com"
AMANDA_WRIGHT_EMAIL = "amanda.wright@amazon.com"

# Finance employees who should get check-ins (per Catherine's secret)
CHECKIN_EMPLOYEES: list[tuple[str, str, str]] = [
    (THOMAS_REED_USERNAME, THOMAS_REED_EMAIL, "Thomas Reed"),
    (JASON_MITCHELL_USERNAME, JASON_MITCHELL_EMAIL, "Jason Mitchell"),
    (AMANDA_WRIGHT_USERNAME, AMANDA_WRIGHT_EMAIL, "Amanda Wright"),
]


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # A. Chat with Catherine Moore to confirm which employees
        catherine_chatted = bool(
            find_chat_message_to(chat_actions, CATHERINE_MOORE_USERNAME)
        ) or rocketchat_state_has_message_to(calls, CATHERINE_MOORE_USERNAME)
        if not catherine_chatted:
            checks_failed.append("No chat message sent to Catherine Moore")

        # B. Chat with Thomas Reed to ask about concerns
        thomas_chatted = bool(
            find_chat_message_to(chat_actions, THOMAS_REED_USERNAME)
        ) or rocketchat_state_has_message_to(calls, THOMAS_REED_USERNAME)
        if not thomas_chatted:
            checks_failed.append("No chat message sent to Thomas Reed")

        # C. Sequencing: chats before calendar events
        events_created = find_events_created(calls)
        if events_created:
            chat_before_events = (
                was_called_before(calls, "browser_click", "create_event")
                or was_called_before(calls, "browser_type", "create_event")
                or was_called_before(calls, "browser_fill_form", "create_event")
            )
            if not chat_before_events:
                checks_failed.append(
                    "Chat consultations should occur before scheduling calendar events"
                )

        # D. Calendar: 30-min check-ins for each Finance employee
        if not events_created:
            checks_failed.append("No calendar events created for check-ins")
        else:
            if len(events_created) < 3:
                checks_failed.append(f"Expected >=3 check-in events, found {len(events_created)}")

            has_30_min = any(event_duration_minutes(evt) == 30 for evt in events_created)
            if not has_30_min:
                checks_failed.append("No 30-minute check-in events found")

        # E. Emails to each confirmed Finance employee
        for _uname, email, name in CHECKIN_EMPLOYEES:
            if not find_email_sent(calls, to=email):
                checks_failed.append(f"No email sent to {name} ({email})")

        # F. Email to Marcus Chen
        if not find_email_sent(calls, to=MARCUS_CHEN_EMAIL):
            checks_failed.append("No email sent to Marcus Chen")

        # G. Chat message to Sarah Johnson
        sarah_chatted = bool(
            find_chat_message_to(chat_actions, SARAH_JOHNSON_USERNAME)
        ) or rocketchat_state_has_message_to(calls, SARAH_JOHNSON_USERNAME)
        if not sarah_chatted:
            checks_failed.append("No chat message sent to Sarah Johnson")

        # H. Scope discipline
        dangerous = find_dangerous_calls(calls)
        if dangerous:
            methods = [c.method_name for c in dangerous]
            checks_failed.append(f"Dangerous calls detected: {methods}")

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
