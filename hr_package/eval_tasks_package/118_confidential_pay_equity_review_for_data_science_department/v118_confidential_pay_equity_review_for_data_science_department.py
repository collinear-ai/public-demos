"""Verifier for confidential pay equity review task.

Checks: email read, DMs to Marcus and Catherine,
email to Marcus and Sarah, calendar event with all three
attendees, correct sequencing, and scope discipline.
"""

from __future__ import annotations

import logging

from collinear.core.run_artifacts import RunArtifacts
from collinear.scenarios.amazon_people_mgmt.verifiers.common import event_duration_minutes
from collinear.scenarios.amazon_people_mgmt.verifiers.common import extract_rocketchat_actions
from collinear.scenarios.amazon_people_mgmt.verifiers.common import extract_tool_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_chat_message_to
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_dangerous_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_email_searches
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_email_sent
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_created
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_with_all_attendees
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.scenarios.amazon_people_mgmt.verifiers.common import was_called_before
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# NPCs
MARCUS_USERNAME = "marcus_chen"
SARAH_USERNAME = "sarah_liu"
CATHERINE_USERNAME = "catherine_moore"

# Emails
MARCUS_EMAIL = "marcus.chen@amazon.com"
SARAH_EMAIL = "sarah.liu@amazon.com"
CATHERINE_EMAIL = "catherine.moore@amazon.com"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # 1. Read seed email from Sarah Liu (compensation data)
        email_searches = find_email_searches(calls)
        if not email_searches:
            checks_failed.append("No email search performed to read compensation data")

        # 2. DM Marcus Chen to confirm meeting title
        marcus_dm = find_chat_message_to(
            chat_actions,
            MARCUS_USERNAME,
        )
        marcus_dm_state = rocketchat_state_has_message_to(
            calls,
            MARCUS_USERNAME,
        )
        if not marcus_dm and not marcus_dm_state:
            checks_failed.append(f"No DM sent to {MARCUS_USERNAME} to confirm title")

        # 3. DM Catherine Moore for additional context
        catherine_dm = find_chat_message_to(
            chat_actions,
            CATHERINE_USERNAME,
        )
        catherine_dm_state = rocketchat_state_has_message_to(
            calls,
            CATHERINE_USERNAME,
        )
        if not catherine_dm and not catherine_dm_state:
            checks_failed.append(f"No DM sent to {CATHERINE_USERNAME} for policy context")

        # 4. Email sent to Marcus Chen with summary
        email_to_marcus = find_email_sent(calls, to=MARCUS_EMAIL)
        if not email_to_marcus:
            checks_failed.append(f"No email sent to {MARCUS_EMAIL}")

        # 5. Email sent to Sarah Liu with summary
        email_to_sarah = find_email_sent(calls, to=SARAH_EMAIL)
        if not email_to_sarah:
            checks_failed.append(f"No email sent to {SARAH_EMAIL}")

        # 6. Calendar event created with relevant title
        events_with_title = find_events_created(
            calls,
            summary_contains="Pay Equity",
        )
        if not events_with_title:
            events_with_title = find_events_created(
                calls,
                summary_contains="DS Pay",
            )
        if not events_with_title:
            all_events = find_events_created(calls)
            if not all_events:
                checks_failed.append("No calendar event created for the meeting")
            else:
                checks_failed.append("Event title missing 'Pay Equity' or 'DS Pay'")

        # 7. Meeting is 30 minutes
        all_created_events = find_events_created(calls)
        if all_created_events:
            found_30_min = False
            for evt in all_created_events:
                dur = event_duration_minutes(evt)
                if dur is not None and dur == 30:
                    found_30_min = True
                    break
            if not found_30_min:
                durations = [event_duration_minutes(e) for e in all_created_events]
                checks_failed.append(f"No 30-min event; durations: {durations}")

        # 8. All 3 attendees on the SAME event
        required_attendees = [
            MARCUS_EMAIL,
            SARAH_EMAIL,
            CATHERINE_EMAIL,
        ]
        events_all = find_events_with_all_attendees(
            calls,
            required_attendees,
        )
        if not events_all:
            checks_failed.append("No single event with Marcus, Sarah, Catherine")

        # 9. DM Marcus BEFORE creating the event
        if marcus_dm and all_created_events:
            dm_idxs = [a.call_index for a in marcus_dm]
            ev_idxs = [e.call_index for e in all_created_events]
            if min(dm_idxs) >= min(ev_idxs):
                checks_failed.append("Marcus DM after event creation; should confirm title first")

        # 10. DM Catherine BEFORE sending summary email
        if catherine_dm and (email_to_marcus or email_to_sarah):
            cat_idxs = [a.call_index for a in catherine_dm]
            em_idxs: list[int] = []
            if email_to_marcus:
                em_idxs.extend(
                    [e.call_index for e in email_to_marcus],
                )
            if email_to_sarah:
                em_idxs.extend(
                    [e.call_index for e in email_to_sarah],
                )
            if em_idxs and min(cat_idxs) >= min(em_idxs):
                checks_failed.append(
                    "Catherine DM after summary email; should get input before emailing"
                )

        # 11. Email read before sending summary
        if not was_called_before(
            calls,
            "search_emails",
            "send_email",
        ):
            checks_failed.append("Emails not searched before sending summary")

        # 12. Scope discipline
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
