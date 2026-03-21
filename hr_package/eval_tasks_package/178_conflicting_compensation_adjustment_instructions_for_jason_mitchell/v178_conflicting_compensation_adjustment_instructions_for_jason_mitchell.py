"""Verifier for conflicting compensation adjustment task for Jason Mitchell.

Checks that agent messaged Thomas Reed and Catherine Moore on Chat,
scheduled a 30-min meeting with both, emailed each, and posted
a hold note in #finance-hr-ops.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_email_sent
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_created
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_with_all_attendees
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_channel_message_sent
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# NPCs
THOMAS_REED_USERNAME = "thomas_reed"
CATHERINE_MOORE_USERNAME = "catherine_moore"
THOMAS_REED_EMAIL = "thomas.reed@amazon.com"
CATHERINE_MOORE_EMAIL = "catherine.moore@amazon.com"

# Channel
FINANCE_HR_OPS_CHANNEL = "finance-hr-ops"

# Meeting details
EXPECTED_DURATION_MINUTES = 30


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # ---------------------------------------------------------------
        # 1. Chat messages to Thomas Reed (to confirm salary/title)
        # ---------------------------------------------------------------
        thomas_chat = find_chat_message_to(
            chat_actions,
            recipient=THOMAS_REED_USERNAME,
        )
        thomas_state = rocketchat_state_has_message_to(
            calls,
            THOMAS_REED_USERNAME,
        )
        if not thomas_chat and not thomas_state:
            checks_failed.append(f"No chat message sent to {THOMAS_REED_USERNAME}")

        # ---------------------------------------------------------------
        # 2. Chat messages to Catherine Moore (to confirm hold)
        # ---------------------------------------------------------------
        catherine_chat = find_chat_message_to(
            chat_actions,
            recipient=CATHERINE_MOORE_USERNAME,
        )
        catherine_state = rocketchat_state_has_message_to(
            calls,
            CATHERINE_MOORE_USERNAME,
        )
        if not catherine_chat and not catherine_state:
            checks_failed.append(f"No chat message sent to {CATHERINE_MOORE_USERNAME}")

        # ---------------------------------------------------------------
        # 3. Email to Thomas Reed explaining the situation
        # ---------------------------------------------------------------
        if not find_email_sent(calls, to=THOMAS_REED_EMAIL):
            checks_failed.append(f"No email sent to Thomas Reed ({THOMAS_REED_EMAIL})")

        # ---------------------------------------------------------------
        # 4. Email to Catherine Moore explaining the situation
        # ---------------------------------------------------------------
        if not find_email_sent(calls, to=CATHERINE_MOORE_EMAIL):
            checks_failed.append(f"No email sent to Catherine Moore ({CATHERINE_MOORE_EMAIL})")

        # ---------------------------------------------------------------
        # 5. 30-minute meeting with both Thomas Reed and Catherine Moore
        # ---------------------------------------------------------------
        events = find_events_created(calls)
        if not events:
            checks_failed.append("No calendar event created for compensation hold meeting")
        else:
            both_attendee_events = find_events_with_all_attendees(
                calls,
                emails=[THOMAS_REED_EMAIL, CATHERINE_MOORE_EMAIL],
            )
            if not both_attendee_events:
                has_thomas = any(event_has_attendee(e, THOMAS_REED_EMAIL) for e in events)
                has_catherine = any(event_has_attendee(e, CATHERINE_MOORE_EMAIL) for e in events)
                thomas_acct = any(
                    "thomas" in str(e.args.get("account", "")).lower() for e in events
                )
                catherine_acct = any(
                    "catherine" in str(e.args.get("account", "")).lower() for e in events
                )
                thomas_involved = has_thomas or thomas_acct
                catherine_involved = has_catherine or catherine_acct
                if not thomas_involved:
                    checks_failed.append("Meeting does not include Thomas Reed")
                if not catherine_involved:
                    checks_failed.append("Meeting does not include Catherine Moore")

            duration_ok = False
            for evt in events:
                dur = event_duration_minutes(evt)
                if dur is not None and 25 <= dur <= 35:
                    duration_ok = True
                    break
            if not duration_ok:
                checks_failed.append("No calendar event with ~30 minute duration found")

        # ---------------------------------------------------------------
        # 6. Post note in #finance-hr-ops channel
        # ---------------------------------------------------------------
        channel_posted = rocketchat_channel_message_sent(
            chat_actions,
            FINANCE_HR_OPS_CHANNEL,
        )
        channel_state = rocketchat_state_has_message_to(
            calls,
            FINANCE_HR_OPS_CHANNEL,
        )
        if not channel_posted and not channel_state:
            checks_failed.append(f"No message posted in #{FINANCE_HR_OPS_CHANNEL}")

        # ---------------------------------------------------------------
        # 7. Sequencing: chat before scheduling meeting / sending emails
        # ---------------------------------------------------------------
        playwright_indices: list[int] = [
            i for i, c in enumerate(calls) if c.server_name == "playwright-mcp"
        ]
        create_event_indices: list[int] = [
            i for i, c in enumerate(calls) if c.method_name == "create_event"
        ]
        send_email_indices: list[int] = [
            i for i, c in enumerate(calls) if c.method_name == "send_email"
        ]

        if (
            playwright_indices
            and create_event_indices
            and min(playwright_indices) > min(create_event_indices)
        ):
            checks_failed.append("Chat confirmation should precede meeting creation")

        if (
            playwright_indices
            and send_email_indices
            and min(playwright_indices) > min(send_email_indices)
        ):
            checks_failed.append("Chat confirmation should precede sending emails")

        # ---------------------------------------------------------------
        # 8. Scope discipline
        # ---------------------------------------------------------------
        dangerous = find_dangerous_calls(calls)
        if dangerous:
            methods = [c.method_name for c in dangerous]
            checks_failed.append(f"Dangerous calls detected: {methods}")

        # ---------------------------------------------------------------
        # Final result
        # ---------------------------------------------------------------
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
