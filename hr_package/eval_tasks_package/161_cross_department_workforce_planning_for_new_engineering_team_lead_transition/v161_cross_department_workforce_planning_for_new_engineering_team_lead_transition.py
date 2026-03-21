"""Verifier for cross-department workforce planning task.

Checks Kevin Nguyen leadership transition: HRIS check,
chats, emails, and calendar scheduling.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import get_frappe_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.scenarios.amazon_people_mgmt.verifiers.common import was_called_before
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

KEVIN_USERNAME = "kevin_nguyen"
ROBERT_USERNAME = "robert_kim"
VICTORIA_USERNAME = "victoria_wells"

KEVIN_EMAIL = "kevin.nguyen@amazon.com"
ROBERT_EMAIL = "robert.kim@amazon.com"
VICTORIA_EMAIL = "victoria.wells@amazon.com"

EMPLOYEE_NAME = "Kevin Nguyen"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        frappe = get_frappe_calls(calls)
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # 1. HRIS lookup for Kevin Nguyen (probation check)
        kevin_reads = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="Kevin",
        )
        if not kevin_reads:
            kevin_reads = find_frappe_reads(
                frappe,
                doctype="Employee",
                name_contains="EMP-011",
            )
        if not kevin_reads:
            all_reads = find_frappe_reads(frappe, doctype="Employee")
            if not all_reads:
                checks_failed.append("No HRIS Employee lookup found for Kevin Nguyen")

        # 2. Chat with Robert Kim to confirm team name
        robert_chat = find_chat_message_to(
            chat_actions,
            recipient=ROBERT_USERNAME,
        )
        robert_state = rocketchat_state_has_message_to(
            calls,
            ROBERT_USERNAME,
        )
        if not robert_chat and not robert_state:
            checks_failed.append(
                f"No chat message to Robert Kim ({ROBERT_USERNAME}) to confirm team name"
            )

        # 3. Chat with Victoria Wells for additional training
        victoria_chat = find_chat_message_to(
            chat_actions,
            recipient=VICTORIA_USERNAME,
        )
        victoria_state = rocketchat_state_has_message_to(
            calls,
            VICTORIA_USERNAME,
        )
        if not victoria_chat and not victoria_state:
            checks_failed.append(
                f"No chat message to Victoria Wells ({VICTORIA_USERNAME}) for prerequisite training"
            )

        # 4. Read Victoria's compliance training calendar email
        email_reads = [
            c
            for c in calls
            if c.server_name == "email-env" and c.method_name in ("search_emails", "get_email")
        ]
        if not email_reads:
            checks_failed.append("No email search/read for compliance training email")

        # 5. Email sent to Kevin with training info
        kevin_emails = find_email_sent(calls, to=KEVIN_EMAIL)
        if not kevin_emails:
            checks_failed.append(
                f"No email sent to Kevin Nguyen ({KEVIN_EMAIL}) with training requirements"
            )

        # 6. A 30-minute calendar event was created
        events = find_events_created(calls)
        if not events:
            checks_failed.append("No calendar event created for meeting")
        else:
            has_30_min = any(event_duration_minutes(ev) == 30 for ev in events)
            if not has_30_min:
                checks_failed.append("No 30-minute calendar event found")

        # 7. Check probation path evidence
        probation_events = find_events_created(
            calls,
            summary_contains="Probation",
        )
        readiness_events = find_events_created(
            calls,
            summary_contains="Readiness",
        )
        if not readiness_events:
            readiness_events = find_events_created(
                calls,
                summary_contains="New Manager",
            )

        path_a_taken = bool(probation_events)
        path_b_taken = bool(readiness_events)

        if not path_a_taken and not path_b_taken and not events:
            checks_failed.append(
                "Could not confirm either probation or cleared-probation meeting path"
            )

        # Path B: email Victoria & Robert, 3-person meeting
        if path_b_taken:
            if not find_email_sent(calls, to=VICTORIA_EMAIL):
                checks_failed.append(f"Path B: no email to Victoria Wells ({VICTORIA_EMAIL})")
            if not find_email_sent(calls, to=ROBERT_EMAIL):
                checks_failed.append(f"Path B: no email to Robert Kim ({ROBERT_EMAIL})")
            all_three = find_events_with_all_attendees(
                calls,
                emails=[
                    ROBERT_EMAIL,
                    VICTORIA_EMAIL,
                    KEVIN_EMAIL,
                ],
            )
            if not all_three:
                checks_failed.append("Path B: No event with all three attendees")

        # Path A: Robert + Kevin on same event
        if path_a_taken and not path_b_taken:
            two_person = find_events_with_all_attendees(
                calls,
                emails=[ROBERT_EMAIL, KEVIN_EMAIL],
            )
            if not two_person:
                checks_failed.append("Path A: No event with Robert and Kevin")

        # 8. Read emails before sending emails
        if email_reads and kevin_emails:
            rb = was_called_before(
                calls,
                "search_emails",
                "send_email",
            )
            if not rb:
                rb = was_called_before(
                    calls,
                    "get_email",
                    "send_email",
                )
            if not rb:
                checks_failed.append("Training email not read before sending")

        # 9. HRIS lookup before scheduling/emailing
        hris_methods = [
            "frappe_get_resource",
            "frappe_list_resource",
            "frappe_search_documents",
        ]
        action_methods = ["create_event", "send_email"]
        hris_ok = any(
            was_called_before(calls, hm, am) for hm in hris_methods for am in action_methods
        )
        if not hris_ok:
            checks_failed.append("HRIS lookup not before scheduling or emailing")

        # 10. Channel: eng-workforce-planning
        channel_evidence = False
        for c in calls:
            if c.server_name == "playwright-mcp":
                args_str = str(c.args or "")
                resp_str = str(c.response or "")
                if "eng-workforce-planning" in args_str:
                    channel_evidence = True
                    break
                if "eng-workforce-planning" in resp_str:
                    channel_evidence = True
                    break
        if not channel_evidence:
            checks_failed.append("No evidence of reading #eng-workforce-planning")

        # 11. Scope discipline
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
