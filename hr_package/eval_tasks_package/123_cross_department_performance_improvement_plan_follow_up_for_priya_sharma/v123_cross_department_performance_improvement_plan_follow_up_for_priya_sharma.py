"""Verifier for cross-department PIP follow-up for Priya Sharma.

Checks agent read email, looked up Priya in HRIS, chatted with
James Peterson and Marcus Chen before acting, scheduled the meeting,
updated performance rating, messaged Sarah, and emailed James.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_with_all_attendees
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_reads
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_update
from collinear.scenarios.amazon_people_mgmt.verifiers.common import get_frappe_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import read_before_write
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

EMPLOYEE_NAME = "Priya Sharma"
SARAH_LIU_USERNAME = "sarah_liu"
JAMES_PETERSON_USERNAME = "james_peterson"
MARCUS_CHEN_USERNAME = "marcus_chen"
SARAH_LIU_EMAIL = "sarah.liu@amazon.com"
JAMES_PETERSON_EMAIL = "james.peterson@amazon.com"
MARCUS_CHEN_EMAIL = "marcus.chen@amazon.com"

EXPECTED_MEETING_TITLE = "Cross-Department Performance Review"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        frappe = get_frappe_calls(calls)
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # 1. Read seed email
        email_reads = [
            c
            for c in calls
            if c.server_name == "email-env" and c.method_name in ("search_emails", "get_email")
        ]
        if not email_reads:
            checks_failed.append("No email read/search for Sarah Liu's PIP email")

        # 2. HRIS lookup for Priya Sharma
        priya_reads = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="Priya",
        )
        if not priya_reads:
            priya_reads = find_frappe_reads(
                frappe,
                doctype="Employee",
                name_contains="Sharma",
            )
        if not priya_reads:
            checks_failed.append("No HRIS lookup for Priya Sharma")

        # 3. Chat with James Peterson (performance rating)
        james_chat = find_chat_message_to(
            chat_actions,
            JAMES_PETERSON_USERNAME,
        )
        james_state = rocketchat_state_has_message_to(
            calls,
            JAMES_PETERSON_USERNAME,
        )
        if not james_chat and not james_state:
            checks_failed.append("No chat to James Peterson for rating")

        # 4. Chat with Marcus Chen (meeting title)
        marcus_chat = find_chat_message_to(
            chat_actions,
            MARCUS_CHEN_USERNAME,
        )
        marcus_state = rocketchat_state_has_message_to(
            calls,
            MARCUS_CHEN_USERNAME,
        )
        if not marcus_chat and not marcus_state:
            checks_failed.append("No chat to Marcus Chen for meeting title")

        # 5. Chat with Sarah Liu (confirm path)
        sarah_chat = find_chat_message_to(
            chat_actions,
            SARAH_LIU_USERNAME,
        )
        sarah_state = rocketchat_state_has_message_to(
            calls,
            SARAH_LIU_USERNAME,
        )
        if not sarah_chat and not sarah_state:
            checks_failed.append("No chat to Sarah Liu to confirm path")

        # 6. HRIS update for Priya's performance rating
        perf_updates = find_frappe_update(
            frappe,
            doctype="Employee",
            name_contains="Priya",
        )
        if not perf_updates:
            perf_updates = find_frappe_update(
                frappe,
                doctype="Employee",
                name_contains="Sharma",
            )
        if not perf_updates:
            perf_updates = find_frappe_update(
                frappe,
                doctype="Employee",
            )
        if not perf_updates:
            checks_failed.append("No HRIS update for Priya's performance rating")

        # 7. Read-before-write on Employee
        if not read_before_write(frappe, doctype="Employee"):
            checks_failed.append("Employee record not read before update")

        # 8. James chat before HRIS update
        if james_chat and perf_updates:
            j_idx = [a.call_index for a in james_chat]
            u_idx = [c.call_index for c in perf_updates]
            if min(j_idx) >= min(u_idx):
                checks_failed.append("James not contacted before HRIS update")

        # 9. Marcus chat before calendar event
        events = find_events_created(calls)
        if marcus_chat and events:
            m_idx = [a.call_index for a in marcus_chat]
            e_idx = [c.call_index for c in events]
            if min(m_idx) >= min(e_idx):
                checks_failed.append("Marcus not contacted before scheduling")

        # 10. Calendar event with correct title & 30 min
        if not events:
            checks_failed.append("No calendar event created")
        else:
            title_events = find_events_created(
                calls,
                summary_contains="Cross-Department Performance Review",
            )
            if not title_events:
                title_events = find_events_created(
                    calls,
                    summary_contains="Performance Review",
                )
            if not title_events:
                checks_failed.append("No event with Marcus's preferred title")
            else:
                dur = event_duration_minutes(title_events[0])
                if dur is not None and dur != 30:
                    checks_failed.append(f"Duration {dur} min, expected 30")

        # 11. Attendees: Sarah Liu + James Peterson on same event
        if events:
            required = [SARAH_LIU_EMAIL, JAMES_PETERSON_EMAIL]
            same = find_events_with_all_attendees(calls, required)
            if not same:
                checks_failed.append(
                    "No single event with both Sarah Liu and James Peterson as attendees"
                )

        # 12. Email to James Peterson about the meeting
        if not find_email_sent(calls, to=JAMES_PETERSON_EMAIL):
            checks_failed.append("No email sent to James Peterson")

        # 13. Scope discipline
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
