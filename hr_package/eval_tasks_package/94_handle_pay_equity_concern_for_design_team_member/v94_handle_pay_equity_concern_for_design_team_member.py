"""Verifier for pay equity concern handling task.

Verify agent looked up Oliver Chen's compensation, messaged Rachel
and Emma on Chat, updated HRIS compensation, sent follow-up email,
and scheduled a 30-min meeting with both Rachel and Emma.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import hris_lookup_before_chat
from collinear.scenarios.amazon_people_mgmt.verifiers.common import read_before_write
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.scenarios.amazon_people_mgmt.verifiers.common import was_called_before
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# Key entities
EMPLOYEE_NAME = "Oliver Chen"
RACHEL_USERNAME = "rachel_foster"
EMMA_USERNAME = "emma_thompson"
RACHEL_EMAIL = "rachel.foster@amazon.com"
EMMA_EMAIL = "emma.thompson@amazon.com"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        frappe = get_frappe_calls(calls)
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # A1. HRIS lookup for Oliver Chen's compensation
        oliver_reads = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="Oliver",
        )
        if not oliver_reads:
            oliver_reads = find_frappe_reads(
                frappe,
                doctype="Employee",
            )
        if not oliver_reads:
            checks_failed.append("No HRIS Employee lookup found for Oliver Chen")

        # A2. Chat message to Rachel Foster (share comp findings)
        rachel_chat = find_chat_message_to(
            chat_actions,
            RACHEL_USERNAME,
        )
        rachel_state = rocketchat_state_has_message_to(
            calls,
            RACHEL_USERNAME,
        )
        if not rachel_chat and not rachel_state:
            checks_failed.append(f"No chat message sent to {RACHEL_USERNAME}")

        # A3. Chat message to Emma Thompson (get approved salary)
        emma_chat = find_chat_message_to(
            chat_actions,
            EMMA_USERNAME,
        )
        emma_state = rocketchat_state_has_message_to(
            calls,
            EMMA_USERNAME,
        )
        if not emma_chat and not emma_state:
            checks_failed.append(f"No chat message sent to {EMMA_USERNAME}")

        # B1. HRIS read before write
        if not read_before_write(frappe, doctype="Employee"):
            checks_failed.append("No HRIS read-before-write sequence for Employee")

        # B2. HRIS lookup before chatting Rachel
        if not hris_lookup_before_chat(frappe, chat_actions):
            checks_failed.append("HRIS lookup did not occur before chat messages")

        # B3. Emma contacted before HRIS compensation update
        emma_before_update = was_called_before(
            calls,
            "browser_click",
            "frappe_update_resource",
        ) or was_called_before(
            calls,
            "browser_type",
            "frappe_update_resource",
        )
        if not emma_before_update:
            checks_failed.append("Emma should be contacted before HRIS update")

        # A4. HRIS compensation update for Oliver Chen
        comp_updates = find_frappe_update(frappe, doctype="Employee")
        if not comp_updates:
            checks_failed.append("No HRIS Employee update found for compensation")

        # A5. Follow-up email to Rachel confirming adjustment
        rachel_emails = find_email_sent(calls, to=RACHEL_EMAIL)
        if not rachel_emails:
            checks_failed.append(f"No follow-up email sent to {RACHEL_EMAIL}")

        # A6. Calendar event: 30-min meeting with Rachel and Emma
        equity_events = find_events_created(
            calls,
            summary_contains="Pay Equity",
        )
        if not equity_events:
            equity_events = find_events_created(
                calls,
                summary_contains="Equity",
            )
        if not equity_events:
            equity_events = find_events_created(calls)

        if not equity_events:
            checks_failed.append("No calendar event created for follow-up")
        else:
            dur = event_duration_minutes(equity_events[0])
            if dur is not None and dur != 30:
                checks_failed.append(f"Meeting duration is {dur} min, expected 30")

            both = find_events_with_all_attendees(
                calls,
                emails=[RACHEL_EMAIL, EMMA_EMAIL],
            )
            if not both:
                checks_failed.append("No single event has both Rachel and Emma")

        # C. Sequencing: email sent after HRIS update
        if not was_called_before(
            calls,
            "frappe_update_resource",
            "send_email",
        ):
            checks_failed.append("Follow-up email should be sent after HRIS update")

        # E. Scope discipline: no dangerous calls
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
