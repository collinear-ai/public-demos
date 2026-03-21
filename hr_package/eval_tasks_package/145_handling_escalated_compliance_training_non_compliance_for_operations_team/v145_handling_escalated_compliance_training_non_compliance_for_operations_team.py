"""Verifier for escalated compliance training non-compliance task.

Verify agent reviewed channel, contacted NPCs, emailed employees
and Nancy, and scheduled follow-up meeting.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_dm_sent
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# NPCs and their details
NANCY_USERNAME = "nancy_cooper"
NANCY_EMAIL = "nancy.cooper@amazon.com"
CHRISTOPHER_USERNAME = "christopher_taylor"
CHRISTOPHER_EMAIL = "christopher.taylor@amazon.com"
RYAN_USERNAME = "ryan_oconnor"
RYAN_EMAIL = "ryan.oconnor@amazon.com"
AMANDA_USERNAME = "amanda_wright"
AMANDA_EMAIL = "amanda.wright@amazon.com"

# All attendee emails for the follow-up meeting
ALL_MEETING_ATTENDEES = [
    NANCY_EMAIL,
    CHRISTOPHER_EMAIL,
    RYAN_EMAIL,
    AMANDA_EMAIL,
]


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # A. Agent reviewed the #ops-compliance-escalation channel
        channel_evidence = any(
            c.server_name == "playwright-mcp"
            and (
                "ops-compliance-escalation" in str(c.args).lower()
                or "ops-compliance-escalation" in str(getattr(c, "response", "")).lower()
            )
            for c in calls
        )
        if not channel_evidence:
            checks_failed.append("No evidence of reviewing #ops-compliance-escalation channel")

        # B. DM to Nancy Cooper to confirm manager-specific trainings
        nancy_dm = rocketchat_dm_sent(
            chat_actions,
            NANCY_USERNAME,
        ) or rocketchat_state_has_message_to(calls, NANCY_USERNAME)
        if not nancy_dm:
            checks_failed.append(
                "No DM sent to nancy_cooper to confirm manager-specific trainings for Ryan"
            )

        # C. DM to Christopher Taylor to confirm completion status
        christopher_dm = rocketchat_dm_sent(
            chat_actions,
            CHRISTOPHER_USERNAME,
        ) or rocketchat_state_has_message_to(
            calls,
            CHRISTOPHER_USERNAME,
        )
        if not christopher_dm:
            checks_failed.append(
                "No DM sent to christopher_taylor to confirm "
                "whether he completed any overdue trainings"
            )

        # D. Sequencing: DM to Christopher BEFORE email to Christopher
        christopher_dm_actions = find_chat_message_to(
            chat_actions,
            CHRISTOPHER_USERNAME,
        )
        christopher_emails = find_email_sent(
            calls,
            to=CHRISTOPHER_EMAIL,
        )
        if christopher_dm_actions and christopher_emails:
            dm_idx = [a.call_index for a in christopher_dm_actions if hasattr(a, "call_index")]
            em_idx = [c.call_index for c in christopher_emails if hasattr(c, "call_index")]
            if dm_idx and em_idx and min(dm_idx) > min(em_idx):
                checks_failed.append("Christopher DM should happen BEFORE sending him the email")

        # D2. Sequencing: DM to Nancy BEFORE email to Ryan
        nancy_dm_actions = find_chat_message_to(
            chat_actions,
            NANCY_USERNAME,
        )
        ryan_emails = find_email_sent(calls, to=RYAN_EMAIL)
        if nancy_dm_actions and ryan_emails:
            n_idx = [a.call_index for a in nancy_dm_actions if hasattr(a, "call_index")]
            r_idx = [c.call_index for c in ryan_emails if hasattr(c, "call_index")]
            if n_idx and r_idx and min(n_idx) > min(r_idx):
                checks_failed.append(
                    "Nancy DM should happen BEFORE sending Ryan his compliance email"
                )

        # E. Email each non-compliant employee
        if not find_email_sent(calls, to=CHRISTOPHER_EMAIL):
            checks_failed.append("No email sent to Christopher Taylor")
        if not find_email_sent(calls, to=RYAN_EMAIL):
            checks_failed.append("No email sent to Ryan O'Connor")
        if not find_email_sent(calls, to=AMANDA_EMAIL):
            checks_failed.append("No email sent to Amanda Wright")

        # F. Email Nancy Cooper a summary
        if not find_email_sent(calls, to=NANCY_EMAIL):
            checks_failed.append("No summary email sent to Nancy Cooper")

        # G. Schedule 30-min follow-up meeting with all attendees
        compliance_events = find_events_created(
            calls,
            summary_contains="Compliance",
        )
        if not compliance_events:
            compliance_events = find_events_created(
                calls,
                summary_contains="Follow",
            )
        if not compliance_events:
            compliance_events = find_events_created(calls)

        if not compliance_events:
            checks_failed.append("No calendar event created for follow-up")
        else:
            dur = event_duration_minutes(compliance_events[0])
            if dur is not None and dur != 30:
                checks_failed.append(f"Meeting duration is {dur} min, expected 30")
            events_with_all = find_events_with_all_attendees(
                calls,
                ALL_MEETING_ATTENDEES,
            )
            if not events_with_all:
                checks_failed.append("No single event includes all four required attendees")

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
