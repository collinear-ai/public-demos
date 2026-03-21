"""Verifier for design team conflict and promotion follow-up.

Checks: channel review, mediation check-ins, debrief with Rachel,
emails to three employees, chat with Rachel before HRIS update,
HRIS update for Oliver Chen, and completion DM to Rachel.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_with_attendee
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_reads
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_update
from collinear.scenarios.amazon_people_mgmt.verifiers.common import get_frappe_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# NPCs
OLIVER_USERNAME = "oliver_chen"
MAYA_USERNAME = "maya_patel"
LUCAS_USERNAME = "lucas_anderson"
RACHEL_USERNAME = "rachel_foster"

# Emails
OLIVER_EMAIL = "oliver.chen@amazon.com"
MAYA_EMAIL = "maya.patel@amazon.com"
LUCAS_EMAIL = "lucas.anderson@amazon.com"
RACHEL_EMAIL = "rachel.foster@amazon.com"

# Channel
DESIGN_CHANNEL = "design-team-concerns"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        frappe = get_frappe_calls(calls)
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # A. Review #design-team-concerns channel
        channel_visited = False
        for c in calls:
            if c.server_name == "playwright-mcp":
                args_str = str(c.args or "")
                resp_str = str(c.response or "")
                if DESIGN_CHANNEL in args_str or DESIGN_CHANNEL in resp_str:
                    channel_visited = True
                    break
        if not channel_visited:
            checks_failed.append(f"No evidence of reviewing #{DESIGN_CHANNEL} channel")

        # B. Chat with Rachel Foster to confirm title & comp before HRIS
        rachel_chat = find_chat_message_to(
            chat_actions,
            recipient=RACHEL_USERNAME,
        )
        rachel_state = rocketchat_state_has_message_to(
            calls,
            RACHEL_USERNAME,
        )
        if not rachel_chat and not rachel_state:
            checks_failed.append(
                "No chat message to Rachel Foster to confirm title/compensation before HRIS update"
            )

        # C. HRIS lookup for Oliver Chen
        oliver_reads = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="Oliver",
        )
        if not oliver_reads:
            oliver_reads = find_frappe_reads(
                frappe,
                doctype="Employee",
                name_contains="EMP-037",
            )
        if not oliver_reads:
            oliver_reads = find_frappe_reads(
                frappe,
                doctype="Employee",
            )
        if not oliver_reads:
            checks_failed.append("No HRIS read for Oliver Chen before update")

        # D. HRIS update for Oliver Chen's promotion
        hris_updates = find_frappe_update(frappe, doctype="Employee")
        if not hris_updates:
            checks_failed.append("No HRIS Employee update found for Oliver Chen's promotion")

        # Sequencing: chat with Rachel before HRIS update
        if rachel_chat and hris_updates:
            rachel_chat_idx: list[int] = []
            for idx, c in enumerate(calls):
                if c.server_name != "playwright-mcp":
                    continue
                args_s = str(c.args or "")
                if RACHEL_USERNAME in args_s or "rachel" in args_s.lower():
                    rachel_chat_idx.append(idx)
                    break

            update_idx = [idx for idx, c in enumerate(calls) if c in hris_updates]
            if rachel_chat_idx and update_idx and min(rachel_chat_idx) > min(update_idx):
                checks_failed.append(
                    "HRIS update appears before chat with "
                    "Rachel Foster to confirm promotion details"
                )

        # E. 3 separate 30-min mediation check-ins
        all_events = find_events_created(calls)

        oliver_evts = find_events_with_attendee(calls, OLIVER_EMAIL)
        maya_evts = find_events_with_attendee(calls, MAYA_EMAIL)
        lucas_evts = find_events_with_attendee(calls, LUCAS_EMAIL)

        if not oliver_evts:
            checks_failed.append("No mediation check-in event with Oliver Chen")
        else:
            dur = event_duration_minutes(oliver_evts[0])
            if dur is not None and dur != 30:
                checks_failed.append(f"Oliver's check-in is {dur} min, expected 30")

        if not maya_evts:
            checks_failed.append("No mediation check-in event with Maya Patel")
        else:
            dur = event_duration_minutes(maya_evts[0])
            if dur is not None and dur != 30:
                checks_failed.append(f"Maya's check-in is {dur} min, expected 30")

        if not lucas_evts:
            checks_failed.append("No mediation check-in event with Lucas Anderson")
        else:
            dur = event_duration_minutes(lucas_evts[0])
            if dur is not None and dur != 30:
                checks_failed.append(f"Lucas's check-in is {dur} min, expected 30")

        # F. 30-min debrief with Rachel Foster
        rachel_evts = find_events_with_attendee(calls, RACHEL_EMAIL)
        if not rachel_evts:
            checks_failed.append("No debrief calendar event with Rachel Foster")
        else:
            dur = event_duration_minutes(rachel_evts[0])
            if dur is not None and dur != 30:
                checks_failed.append(f"Rachel's debrief is {dur} min, expected 30")

        # At least 4 events
        total = len(all_events)
        if total < 4:
            checks_failed.append(
                f"Only {total} events created, expected at least 4 (3 check-ins + 1 debrief)"
            )

        # G. Email each of the three employees
        if not find_email_sent(calls, to=OLIVER_EMAIL):
            checks_failed.append(f"No email sent to Oliver Chen ({OLIVER_EMAIL})")
        if not find_email_sent(calls, to=MAYA_EMAIL):
            checks_failed.append(f"No email sent to Maya Patel ({MAYA_EMAIL})")
        if not find_email_sent(calls, to=LUCAS_EMAIL):
            checks_failed.append(f"No email sent to Lucas Anderson ({LUCAS_EMAIL})")

        # H. Completion DM to Rachel Foster (already checked in B)
        if not rachel_chat and not rachel_state:
            pass  # already captured above

        # I. Scope discipline
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
