"""Verifier for coordinating sensitive cross-department leadership training.

Checks that the agent gathered info from Rachel and Victoria,
scheduled two calendar events, sent context to Rachel, and
responded to Robert Kim.
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
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_with_all_attendees
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_with_attendee
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# NPC usernames (from task JSON npcs[].id)
RACHEL_USERNAME = "rachel_foster"
ROBERT_USERNAME = "robert_kim"
VICTORIA_USERNAME = "victoria_wells"
EMMA_USERNAME = "emma_thompson"

# Emails
RACHEL_EMAIL = "rachel.foster@amazon.com"
ROBERT_EMAIL = "robert.kim@amazon.com"
VICTORIA_EMAIL = "victoria.wells@amazon.com"
EMMA_EMAIL = "emma.thompson@amazon.com"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # ---------------------------------------------------------------
        # 1. Read Robert Kim's seed email
        # ---------------------------------------------------------------
        email_searches = find_email_searches(calls)
        if not email_searches:
            checks_failed.append("No email search performed to read Robert Kim's email")

        # ---------------------------------------------------------------
        # 2. Contact Rachel Foster (chat or email) to learn coaching needs
        #    Rachel has a secret → agent MUST have contacted her
        # ---------------------------------------------------------------
        rachel_chat = find_chat_message_to(chat_actions, RACHEL_USERNAME)
        rachel_email = find_email_sent(calls, to=RACHEL_EMAIL)
        rachel_state = rocketchat_state_has_message_to(calls, RACHEL_USERNAME)
        rachel_contacted = bool(rachel_chat) or bool(rachel_email) or rachel_state
        if not rachel_contacted:
            checks_failed.append("No message sent to Rachel Foster to learn coaching needs")

        # ---------------------------------------------------------------
        # 3. Contact Victoria Wells (chat or email) to learn framing
        #    Victoria has a secret → agent MUST have contacted her
        # ---------------------------------------------------------------
        victoria_chat = find_chat_message_to(chat_actions, VICTORIA_USERNAME)
        victoria_email = find_email_sent(calls, to=VICTORIA_EMAIL)
        victoria_state = rocketchat_state_has_message_to(calls, VICTORIA_USERNAME)
        victoria_contacted = bool(victoria_chat) or bool(victoria_email) or victoria_state
        if not victoria_contacted:
            checks_failed.append("No message sent to Victoria Wells to learn framing")

        # ---------------------------------------------------------------
        # 4. Leadership Development Session: Emma + Rachel this week
        # ---------------------------------------------------------------
        leadership_events = find_events_created(calls)
        emma_rachel_events = find_events_with_all_attendees(calls, [EMMA_EMAIL, RACHEL_EMAIL])
        if not emma_rachel_events:
            # Fallback: check individually
            emma_events = find_events_with_attendee(calls, EMMA_EMAIL)
            rachel_events = find_events_with_attendee(calls, RACHEL_EMAIL)
            # Find overlap
            emma_rachel_events = [e for e in emma_events if e in rachel_events]

        if not emma_rachel_events:
            checks_failed.append(
                "No Leadership Development Session created with "
                "both Emma Thompson and Rachel Foster as attendees"
            )

        # ---------------------------------------------------------------
        # 5. Cross-Team Collaboration Alignment: Robert + Victoria, 30 min
        # ---------------------------------------------------------------
        robert_victoria_events = find_events_with_all_attendees(
            calls, [ROBERT_EMAIL, VICTORIA_EMAIL]
        )
        if not robert_victoria_events:
            robert_events = find_events_with_attendee(calls, ROBERT_EMAIL)
            victoria_events = find_events_with_attendee(calls, VICTORIA_EMAIL)
            robert_victoria_events = [e for e in robert_events if e in victoria_events]

        if not robert_victoria_events:
            checks_failed.append(
                "No Cross-Team Collaboration Alignment event created "
                "with both Robert Kim and Victoria Wells as attendees"
            )
        else:
            # Check 30-minute duration
            found_30_min = False
            for ev in robert_victoria_events:
                dur = event_duration_minutes(ev)
                if dur is not None and dur == 30:
                    found_30_min = True
                    break
            if not found_30_min:
                checks_failed.append("Robert/Victoria alignment event is not 30 minutes")

        # ---------------------------------------------------------------
        # 6. Two distinct events were created (not just one)
        # ---------------------------------------------------------------
        total_events = len(leadership_events)
        if total_events < 2:
            checks_failed.append(
                f"Expected at least 2 calendar events created, found {total_events}"
            )

        # ---------------------------------------------------------------
        # 7. Attendee separation: Robert NOT on Emma/Rachel session,
        #    Emma NOT on Robert/Victoria session
        # ---------------------------------------------------------------
        for ev in emma_rachel_events:
            if event_has_attendee(ev, ROBERT_EMAIL):
                checks_failed.append(
                    "Robert Kim should NOT be on the Leadership "
                    "Development Session with Emma and Rachel"
                )
                break

        for ev in robert_victoria_events:
            if event_has_attendee(ev, EMMA_EMAIL):
                checks_failed.append(
                    "Emma Thompson should NOT be on the "
                    "Collaboration Alignment with Robert and Victoria"
                )
                break

        # ---------------------------------------------------------------
        # 8. Circle back to Rachel on chat re: cross-department friction
        #    Must happen (at least one chat msg to Rachel).
        #    We already checked contact above; here we verify chat
        #    specifically (task says "on chat").
        # ---------------------------------------------------------------
        rachel_chat_or_state = bool(rachel_chat) or rachel_state
        if not rachel_chat_or_state:
            checks_failed.append(
                "No chat message to Rachel Foster about cross-department friction context"
            )

        # ---------------------------------------------------------------
        # 9. Circle back to Robert Kim — email or chat acknowledging
        #    concerns and mentioning targeted coaching
        # ---------------------------------------------------------------
        robert_chat = find_chat_message_to(chat_actions, ROBERT_USERNAME)
        robert_email_sent = find_email_sent(calls, to=ROBERT_EMAIL)
        robert_state = rocketchat_state_has_message_to(calls, ROBERT_USERNAME)
        robert_responded = bool(robert_chat) or bool(robert_email_sent) or robert_state
        if not robert_responded:
            checks_failed.append(
                "No response sent to Robert Kim acknowledging "
                "concerns and mentioning targeted coaching"
            )

        # ---------------------------------------------------------------
        # 10. Scope discipline — no dangerous calls
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
