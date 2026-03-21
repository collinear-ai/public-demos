"""Verifier for resolving conflicting DEI training accommodation requests.

Checks that the agent gathered info from Rachel Foster and Sarah Johnson
via chat before sending resolution emails, scheduled a 30-minute alignment
meeting, and sent a final DM to Sarah Johnson.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# NPC usernames (from task JSON npcs[].id)
RACHEL_USERNAME = "rachel_foster"
SARAH_USERNAME = "sarah_johnson"
EMMA_USERNAME = "emma_thompson"

# Email addresses (from seed data context)
RACHEL_EMAIL = "rachel.foster@amazon.com"
SARAH_EMAIL = "sarah.johnson@amazon.com"
EMMA_EMAIL = "emma.thompson@amazon.com"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # ---------------------------------------------------------------
        # 1. Agent read the conflicting seed emails
        # ---------------------------------------------------------------
        email_searches = find_email_searches(calls)
        if not email_searches:
            checks_failed.append(
                "No email search found — agent should read the conflicting"
                " emails from Emma and Rachel before acting"
            )

        # ---------------------------------------------------------------
        # 2. Chat DM to Rachel Foster (confirm directive / get reasoning)
        # ---------------------------------------------------------------
        rachel_chats = find_chat_message_to(chat_actions, recipient=RACHEL_USERNAME)
        rachel_chat_sent = len(rachel_chats) > 0
        if not rachel_chat_sent and not rocketchat_state_has_message_to(calls, RACHEL_USERNAME):
            # fallback: check rocketchat state
            checks_failed.append(
                f"No chat DM sent to Rachel Foster ({RACHEL_USERNAME})"
                " to confirm her directive before resolution"
            )

        # ---------------------------------------------------------------
        # 3. Chat DM to Sarah Johnson (get guidance on tone/framing)
        # ---------------------------------------------------------------
        sarah_chats = find_chat_message_to(chat_actions, recipient=SARAH_USERNAME)
        sarah_chat_sent = len(sarah_chats) > 0
        if not sarah_chat_sent and not rocketchat_state_has_message_to(calls, SARAH_USERNAME):
            checks_failed.append(
                f"No chat DM sent to Sarah Johnson ({SARAH_USERNAME})"
                " to get guidance on cross-departmental communication"
            )

        # ---------------------------------------------------------------
        # 4. Resolution email sent to Emma Thompson
        # ---------------------------------------------------------------
        emails_to_emma = find_email_sent(calls, to=EMMA_EMAIL)
        if not emails_to_emma:
            checks_failed.append(f"No resolution email sent to Emma Thompson ({EMMA_EMAIL})")

        # ---------------------------------------------------------------
        # 5. Resolution email sent to Rachel Foster
        # ---------------------------------------------------------------
        emails_to_rachel = find_email_sent(calls, to=RACHEL_EMAIL)
        if not emails_to_rachel:
            checks_failed.append(f"No resolution email sent to Rachel Foster ({RACHEL_EMAIL})")

        # ---------------------------------------------------------------
        # 6. Sequencing: chats to Rachel & Sarah BEFORE resolution email
        # ---------------------------------------------------------------
        # We check that playwright (chat) calls precede send_email calls.
        # Find indices of first chat to Rachel, first chat to Sarah,
        # and first send_email.
        send_email_calls = [c for c in calls if c.method_name == "send_email"]
        if send_email_calls and calls:
            first_send_idx = min(calls.index(c) for c in send_email_calls)

            # Rachel chat before email
            if rachel_chats:
                # Use the action's underlying call index via chat_actions
                for action in rachel_chats:
                    for _i, c in enumerate(calls):
                        if c.server_name == "playwright-mcp" and hasattr(action, "call_index"):
                            break
                # Simpler approach: find first playwright navigate to
                # rachel_foster before first send_email
                rachel_nav_indices = [
                    i
                    for i, c in enumerate(calls)
                    if c.server_name == "playwright-mcp" and RACHEL_USERNAME in str(c.args).lower()
                ]
                if rachel_nav_indices:
                    first_rachel = min(rachel_nav_indices)
                    if first_rachel >= first_send_idx:
                        checks_failed.append(
                            "Chat to Rachel Foster appears to have"
                            " occurred after the resolution email"
                        )

            # Sarah chat before email
            if sarah_chats:
                sarah_nav_indices = [
                    i
                    for i, c in enumerate(calls)
                    if c.server_name == "playwright-mcp" and SARAH_USERNAME in str(c.args).lower()
                ]
                if sarah_nav_indices:
                    first_sarah = min(sarah_nav_indices)
                    if first_sarah >= first_send_idx:
                        checks_failed.append(
                            "Chat to Sarah Johnson appears to have"
                            " occurred after the resolution email"
                        )

        # ---------------------------------------------------------------
        # 7. Calendar: 30-min DEI Training Format Alignment meeting
        # ---------------------------------------------------------------
        events = find_events_created(calls)
        if not events:
            checks_failed.append(
                "No calendar event created for the DEI Training Format Alignment meeting"
            )
        else:
            # Check for a ~30-minute event
            found_30_min = False
            found_both_attendees = False
            for evt in events:
                dur = event_duration_minutes(evt)
                if dur is not None and dur == 30:
                    found_30_min = True
                has_emma = event_has_attendee(evt, EMMA_EMAIL)
                has_rachel = event_has_attendee(evt, RACHEL_EMAIL)
                if has_emma and has_rachel:
                    found_both_attendees = True

            if not found_30_min:
                # Check if any event is 30 minutes
                durations = [event_duration_minutes(e) for e in events]
                checks_failed.append(f"No 30-minute event found. Durations: {durations}")

            if not found_both_attendees:
                checks_failed.append(
                    f"Calendar event missing one or both attendees: {EMMA_EMAIL} and {RACHEL_EMAIL}"
                )

        # ---------------------------------------------------------------
        # 8. Final DM to Sarah Johnson (after resolution actions)
        # ---------------------------------------------------------------
        # We already checked that at least one message was sent to Sarah.
        # The task requires a FINAL summary DM to Sarah after resolution.
        # Verify that there is at least one chat to Sarah that occurs
        # AFTER the send_email calls (the final summary).
        if send_email_calls and sarah_chats:
            # Check if any playwright call referencing sarah_johnson
            # occurs after the last send_email
            last_send_idx = max(calls.index(c) for c in send_email_calls)
            sarah_post_email = [
                i
                for i, c in enumerate(calls)
                if c.server_name == "playwright-mcp"
                and SARAH_USERNAME in str(c.args).lower()
                and i > last_send_idx
            ]
            if not sarah_post_email:
                # Also check if there's a rocketchat state message
                # after the email (harder to verify ordering, so
                # we just note a softer check)
                sarah_state = rocketchat_state_has_message_to(calls, SARAH_USERNAME)
                if not sarah_state:
                    checks_failed.append(
                        "No final summary DM to Sarah Johnson found after the resolution email"
                    )
        elif not send_email_calls:
            pass  # already flagged missing email
        elif not sarah_chats:
            # Check rocketchat state as fallback
            if not rocketchat_state_has_message_to(calls, SARAH_USERNAME):
                checks_failed.append("No final summary DM to Sarah Johnson found")

        # ---------------------------------------------------------------
        # 9. Scope discipline — no dangerous calls
        # ---------------------------------------------------------------
        dangerous = find_dangerous_calls(calls)
        if dangerous:
            methods = [c.method_name for c in dangerous]
            checks_failed.append(f"Dangerous calls detected: {methods}")

        # ---------------------------------------------------------------
        # Return result
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
