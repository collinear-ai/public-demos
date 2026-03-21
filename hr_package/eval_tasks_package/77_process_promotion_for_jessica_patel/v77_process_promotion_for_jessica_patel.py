"""Verifier for processing Jessica Patel's promotion.

Checks: email read, chat with Robert Kim and Sarah Johnson
before HRIS update, HRIS update, chat notification to Robert,
celebration meeting scheduled, congratulatory email sent.
"""

from __future__ import annotations

import logging

from collinear.core.run_artifacts import RunArtifacts
from collinear.scenarios.amazon_people_mgmt.verifiers.common import event_duration_minutes
from collinear.scenarios.amazon_people_mgmt.verifiers.common import event_has_attendee
from collinear.scenarios.amazon_people_mgmt.verifiers.common import extract_rocketchat_actions
from collinear.scenarios.amazon_people_mgmt.verifiers.common import extract_tool_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_chat_message_to
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_dangerous_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_email_searches
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_email_sent
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_created
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_reads
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_update
from collinear.scenarios.amazon_people_mgmt.verifiers.common import get_frappe_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

EMPLOYEE_NAME = "Jessica Patel"
EMPLOYEE_EMAIL = "jessica.patel@amazon.com"
ROBERT_KIM_USERNAME = "robert_kim"
ROBERT_KIM_EMAIL = "robert.kim@amazon.com"
SARAH_JOHNSON_USERNAME = "sarah_johnson"
SARAH_JOHNSON_EMAIL = "sarah.johnson@amazon.com"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        frappe = get_frappe_calls(calls)
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # 1. Agent read the seed email from Sarah Johnson
        email_reads = find_email_searches(calls)
        if not email_reads:
            checks_failed.append(
                "No email search found — agent should have read Sarah Johnson's promotion email"
            )

        # 2. Agent contacted Robert Kim via chat to confirm designation
        robert_chat = find_chat_message_to(
            chat_actions,
            recipient=ROBERT_KIM_USERNAME,
        )
        robert_state = rocketchat_state_has_message_to(
            calls,
            ROBERT_KIM_USERNAME,
        )
        if not robert_chat and not robert_state:
            checks_failed.append(f"No chat message to {ROBERT_KIM_USERNAME} to confirm designation")

        # 3. Agent contacted Sarah Johnson via chat for subject line
        sarah_chat = find_chat_message_to(
            chat_actions,
            recipient=SARAH_JOHNSON_USERNAME,
        )
        sarah_state = rocketchat_state_has_message_to(
            calls,
            SARAH_JOHNSON_USERNAME,
        )
        if not sarah_chat and not sarah_state:
            checks_failed.append(
                f"No chat message to {SARAH_JOHNSON_USERNAME} to get email subject"
            )

        # 4. HRIS lookup for Jessica Patel before updating
        emp_reads = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="Jessica",
        )
        if not emp_reads:
            emp_reads_any = find_frappe_reads(
                frappe,
                doctype="Employee",
            )
            if not emp_reads_any:
                checks_failed.append("No HRIS Employee lookup for Jessica Patel")

        # 5. HRIS update (promotion processed)
        hris_updates = find_frappe_update(frappe, doctype="Employee")
        if not hris_updates:
            checks_failed.append("No HRIS Employee update — promotion not processed")

        # 6. Sequencing: chat with Robert before HRIS update
        if robert_chat and hris_updates:
            robert_idx = min(a.call_index for a in robert_chat)
            update_idx = min(c.call_index for c in hris_updates)
            if robert_idx > update_idx:
                checks_failed.append("HRIS update before confirming with Robert Kim")

        # 7. Sequencing: chat with Sarah before sending email
        congrats_emails = find_email_sent(calls, to=EMPLOYEE_EMAIL)
        if sarah_chat and congrats_emails:
            sarah_idx = min(a.call_index for a in sarah_chat)
            email_idx = min(c.call_index for c in congrats_emails)
            if sarah_idx > email_idx:
                checks_failed.append("Email sent before confirming subject with Sarah")

        # 8. Congratulatory email sent to Jessica Patel
        if not congrats_emails:
            checks_failed.append(f"No congratulatory email sent to {EMPLOYEE_EMAIL}")

        # 9. Celebration meeting (30 min) with Jessica, Robert, Sarah
        events = find_events_created(calls)
        if not events:
            checks_failed.append("No calendar event created for celebration meeting")
        else:
            found_valid = False
            for ev in events:
                dur = event_duration_minutes(ev)
                dur_ok = dur is not None and dur == 30
                all_att = (
                    event_has_attendee(ev, EMPLOYEE_EMAIL)
                    and event_has_attendee(ev, ROBERT_KIM_EMAIL)
                    and event_has_attendee(ev, SARAH_JOHNSON_EMAIL)
                )
                if dur_ok and all_att:
                    found_valid = True
                    break

            if not found_valid:
                has_30 = any(event_duration_minutes(e) == 30 for e in events)
                has_att = any(
                    event_has_attendee(e, EMPLOYEE_EMAIL)
                    and event_has_attendee(e, ROBERT_KIM_EMAIL)
                    and event_has_attendee(e, SARAH_JOHNSON_EMAIL)
                    for e in events
                )
                if not has_30:
                    checks_failed.append("No 30-minute celebration event found")
                if not has_att:
                    checks_failed.append(
                        "Celebration event missing required attendees (Jessica, Robert, Sarah)"
                    )

        # 10. Scope discipline
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
