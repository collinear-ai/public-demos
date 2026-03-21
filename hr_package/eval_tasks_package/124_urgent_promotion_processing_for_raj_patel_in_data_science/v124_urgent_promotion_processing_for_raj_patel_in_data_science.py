"""Verifier for urgent promotion processing for Raj Patel.

Checks that the agent: looked up Raj Patel in HRIS, chatted with
Marcus Chen to confirm salary, updated HRIS with new title, emailed
Raj, scheduled a 30-min meeting with both, and posted congrats in
data-science-team channel.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_channel_message_sent
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

EMPLOYEE_NAME = "Raj Patel"
EMPLOYEE_EMAIL = "raj.patel@amazon.com"
MANAGER_USERNAME = "marcus_chen"
MANAGER_EMAIL = "marcus.chen@amazon.com"
NEW_TITLE = "Lead Data Scientist"
CHANNEL_NAME = "data-science-team"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        frappe = get_frappe_calls(calls)
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # A1. HRIS lookup for Raj Patel
        raj_reads = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="Raj",
        )
        if not raj_reads:
            raj_reads = find_frappe_reads(
                frappe,
                doctype="Employee",
                name_contains="EMP-030",
            )
        if not raj_reads:
            raj_reads = find_frappe_reads(frappe, doctype="Employee")
        if not raj_reads:
            checks_failed.append(
                "No HRIS Employee lookup found for Raj Patel",
            )

        # A2. Chat with Marcus Chen to confirm salary
        marcus_chat = find_chat_message_to(
            chat_actions,
            recipient=MANAGER_USERNAME,
        )
        marcus_state = rocketchat_state_has_message_to(
            calls,
            MANAGER_USERNAME,
        )
        if not marcus_chat and not marcus_state:
            checks_failed.append(
                "No chat message sent to marcus_chen",
            )

        # A3. HRIS update - promotion (designation / title change)
        title_updates = find_frappe_update(
            frappe,
            doctype="Employee",
            payload_contains={"designation": NEW_TITLE},
        )
        if not title_updates:
            any_updates = find_frappe_update(frappe, doctype="Employee")
            if not any_updates:
                checks_failed.append(
                    "No HRIS Employee update found for promotion",
                )
            else:
                found_title = any("lead data scientist" in str(u.args).lower() for u in any_updates)
                if not found_title:
                    checks_failed.append(
                        "HRIS update missing Lead Data Scientist",
                    )

        # B1. Read-before-write sequencing on Employee doctype
        if not read_before_write(frappe, doctype="Employee"):
            checks_failed.append(
                "No evidence of reading Employee before updating",
            )

        # A4. Email sent to Raj Patel confirming promotion
        raj_emails = find_email_sent(calls, to=EMPLOYEE_EMAIL)
        if not raj_emails:
            checks_failed.append(
                f"No email sent to {EMPLOYEE_EMAIL}",
            )

        # A5. Calendar event - 30 min promotion discussion
        events_both = find_events_with_all_attendees(
            calls,
            emails=[EMPLOYEE_EMAIL, MANAGER_EMAIL],
        )
        if not events_both:
            all_events = find_events_created(calls)
            if not all_events:
                checks_failed.append(
                    "No calendar event created",
                )
            else:
                checks_failed.append(
                    "Event missing both Raj and Marcus attendees",
                )
        else:
            dur = event_duration_minutes(events_both[0])
            if dur is not None and dur != 30:
                checks_failed.append(
                    f"Meeting duration {dur}min, expected 30",
                )

        # A6. Congratulations in data-science-team channel
        channel_posted = rocketchat_channel_message_sent(
            chat_actions,
            channel=CHANNEL_NAME,
        )
        channel_state = rocketchat_state_has_message_to(
            calls,
            CHANNEL_NAME,
        )
        if not channel_posted and not channel_state:
            checks_failed.append(
                f"No message in #{CHANNEL_NAME} channel",
            )

        # E. Scope discipline
        dangerous = find_dangerous_calls(calls)
        if dangerous:
            methods = [c.method_name for c in dangerous]
            checks_failed.append(
                f"Dangerous calls detected: {methods}",
            )

        if checks_failed:
            msg = "; ".join(checks_failed)
            return VerifierResult(
                success=False,
                message=msg,
                output=msg,
            )

        msg = "All required tool call evidence found"
        return VerifierResult(
            success=True,
            message=msg,
            output=msg,
        )

    except Exception as exc:
        err = str(exc)
        logger.debug("Verifier error", exc_info=True)
        return VerifierResult(
            success=False,
            message=err,
            output=err,
        )
