"""Verifier for coordinating sensitive role transition training.

Checks: email to David Thompson, calendar meeting with both David
and Michael, chat with Sarah Johnson and Michael Chen before
emailing Lisa the combined training list, and scope discipline.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_reads
from collinear.scenarios.amazon_people_mgmt.verifiers.common import get_frappe_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# NPCs and emails
DAVID_EMAIL = "david.thompson@amazon.com"
MICHAEL_EMAIL = "michael.chen@amazon.com"
LISA_EMAIL = "lisa.anderson@amazon.com"

DAVID_USERNAME = "david_thompson"
MICHAEL_USERNAME = "michael_chen"
SARAH_USERNAME = "sarah_johnson"

REQUIRED_ATTENDEES = [DAVID_EMAIL, MICHAEL_EMAIL]


def _call_has_recipient(call: object, email: str) -> bool:
    """Check if a send_email call targets a specific recipient."""
    args = getattr(call, "args", {}) or {}
    to_val = args.get("to", "")
    if isinstance(to_val, str):
        return email.lower() in to_val.lower()
    if isinstance(to_val, list):
        return any(email.lower() in t.lower() for t in to_val)
    return False


def _is_rocketchat_to(call: object, username: str) -> bool:
    """Check if a Playwright call navigates to a DM with username."""
    args = getattr(call, "args", {}) or {}
    server = getattr(call, "server_name", "")
    if server != "playwright-mcp":
        return False
    url = args.get("url", "")
    if isinstance(url, str) and f"/direct/{username}" in url:
        return True
    return any(isinstance(val, str) and username in val for val in args.values())


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        frappe = get_frappe_calls(calls)
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # A. Read seed email from David Thompson
        email_reads = [
            c
            for c in calls
            if c.server_name == "email-env" and c.method_name in ("search_emails", "get_email")
        ]
        if not email_reads:
            checks_failed.append("No email search/read to discover David's email")

        # B. Email to David Thompson (empathetic acknowledgment)
        david_emails = find_email_sent(calls, to=DAVID_EMAIL)
        if not david_emails:
            checks_failed.append(f"No email sent to David Thompson ({DAVID_EMAIL})")

        # C. Calendar: 30-min transition planning meeting
        joint_events = find_events_with_all_attendees(
            calls,
            emails=REQUIRED_ATTENDEES,
        )
        if not joint_events:
            checks_failed.append("No calendar event with both David and Michael")
        else:
            dur = event_duration_minutes(joint_events[0])
            if dur is not None and dur != 30:
                checks_failed.append(f"Meeting duration is {dur} min, expected 30")

        # D. Chat with Sarah Johnson (training modules)
        sarah_chat = find_chat_message_to(
            chat_actions,
            recipient=SARAH_USERNAME,
        )
        sarah_state = rocketchat_state_has_message_to(
            calls,
            SARAH_USERNAME,
        )
        if not sarah_chat and not sarah_state:
            checks_failed.append("No chat message to Sarah Johnson")

        # E. Chat with Michael Chen (additional requirements)
        michael_chat = find_chat_message_to(
            chat_actions,
            recipient=MICHAEL_USERNAME,
        )
        michael_state = rocketchat_state_has_message_to(
            calls,
            MICHAEL_USERNAME,
        )
        if not michael_chat and not michael_state:
            checks_failed.append("No chat message to Michael Chen")

        # F. Email to Lisa Anderson with combined training list
        lisa_emails = find_email_sent(calls, to=LISA_EMAIL)
        if not lisa_emails:
            checks_failed.append(f"No email sent to Lisa Anderson ({LISA_EMAIL})")

        # G. Sequencing: chats before Lisa's email
        if lisa_emails and (sarah_chat or michael_chat):
            lisa_idx = [
                i
                for i, c in enumerate(calls)
                if c.server_name == "email-env"
                and c.method_name == "send_email"
                and _call_has_recipient(c, LISA_EMAIL)
            ]
            sarah_idx = [i for i, c in enumerate(calls) if _is_rocketchat_to(c, SARAH_USERNAME)]
            michael_idx = [i for i, c in enumerate(calls) if _is_rocketchat_to(c, MICHAEL_USERNAME)]

            if lisa_idx:
                first_lisa = min(lisa_idx)
                if sarah_idx and min(sarah_idx) >= first_lisa:
                    checks_failed.append("Chat with Sarah was not before Lisa email")
                if michael_idx and min(michael_idx) >= first_lisa:
                    checks_failed.append("Chat with Michael was not before Lisa email")

        # H. HRIS lookup for employee info
        lisa_reads = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="Lisa",
        )
        if not lisa_reads:
            any_reads = find_frappe_reads(frappe, doctype="Employee")
            if not any_reads:
                checks_failed.append("No HRIS Employee lookup performed")

        # I. Scope discipline
        dangerous = find_dangerous_calls(calls)
        if dangerous:
            methods = [c.method_name for c in dangerous]
            checks_failed.append(f"Dangerous calls detected: {methods}")

        # Return result
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
