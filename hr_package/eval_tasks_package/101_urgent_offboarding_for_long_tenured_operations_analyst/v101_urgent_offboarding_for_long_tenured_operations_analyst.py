"""Verifier for urgent offboarding of long-tenured Operations Analyst.

Checks: HRIS lookup, farewell email to Ryan, exit interview
scheduling with Ryan+Nancy, DM to Nancy, chat with Catherine
before email, chat with Nancy for exit interview topics, email
to Catherine (with Thomas Reed CC), and scope discipline.
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

# Key personnel
RYAN_EMAIL = "ryan.oconnor@amazon.com"
RYAN_USERNAME = "ryan_oconnor"
NANCY_EMAIL = "nancy.cooper@amazon.com"
NANCY_USERNAME = "nancy_cooper"
CATHERINE_EMAIL = "catherine.moore@amazon.com"
CATHERINE_USERNAME = "catherine_moore"
THOMAS_REED_EMAIL = "thomas.reed@amazon.com"

EMPLOYEE_NAME = "Ryan O'Connor"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        frappe = get_frappe_calls(calls)
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # 1. HRIS lookup for Ryan O'Connor
        ryan_reads = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="Ryan",
        )
        ryan_reads_alt = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="Connor",
        )
        ryan_reads_alt2 = find_frappe_reads(
            frappe,
            doctype="Employee",
            name_contains="EMP-023",
        )
        if not (ryan_reads or ryan_reads_alt or ryan_reads_alt2):
            checks_failed.append(
                "No HRIS lookup found for Ryan O'Connor",
            )

        # 2. Farewell email sent to Ryan
        farewell_emails = find_email_sent(calls, to=RYAN_EMAIL)
        if not farewell_emails:
            checks_failed.append(
                f"No farewell email sent to {RYAN_EMAIL}",
            )

        # 3. Exit interview: 30-min event with Ryan AND Nancy
        exit_events = find_events_with_all_attendees(
            calls,
            emails=[RYAN_EMAIL, NANCY_EMAIL],
        )
        if not exit_events:
            all_events = find_events_created(calls)
            if not all_events:
                checks_failed.append(
                    "No exit interview calendar event created",
                )
            else:
                checks_failed.append(
                    f"No event with both {RYAN_EMAIL} and {NANCY_EMAIL}",
                )
        else:
            dur = event_duration_minutes(exit_events[0])
            if dur is not None and dur != 30:
                checks_failed.append(
                    f"Exit interview duration {dur}m, expected 30",
                )

        # 4. DM to Nancy acknowledging situation
        nancy_dm = find_chat_message_to(
            chat_actions,
            recipient=NANCY_USERNAME,
        )
        nancy_state = rocketchat_state_has_message_to(
            calls,
            NANCY_USERNAME,
        )
        if not nancy_dm and not nancy_state:
            checks_failed.append(
                f"No Chat DM to Nancy ({NANCY_USERNAME})",
            )

        # 5. Chat with Catherine BEFORE emailing her
        catherine_dm = find_chat_message_to(
            chat_actions,
            recipient=CATHERINE_USERNAME,
        )
        catherine_state = rocketchat_state_has_message_to(
            calls,
            CATHERINE_USERNAME,
        )
        if not catherine_dm and not catherine_state:
            checks_failed.append(
                f"No Chat DM to Catherine ({CATHERINE_USERNAME})",
            )

        # 6. Email sent to Catherine Moore
        catherine_emails = find_email_sent(
            calls,
            to=CATHERINE_EMAIL,
        )
        if not catherine_emails:
            checks_failed.append(
                f"No email sent to Catherine ({CATHERINE_EMAIL})",
            )

        # 7. Sequence: Chat to Catherine before email
        if catherine_dm and catherine_emails:
            has_idx = [a for a in catherine_dm if hasattr(a, "call_index")]
            chat_idx = min(a.call_index for a in has_idx) if has_idx else None
            if chat_idx is None and not was_called_before(
                calls,
                "browser_click",
                "send_email",
            ):
                checks_failed.append(
                    "Chat to Catherine may not precede email",
                )

        # 8. Thomas Reed in final pay email
        if catherine_emails:
            thomas_included = False
            for email_call in catherine_emails:
                args = getattr(email_call, "args", {}) or {}
                all_fields = " ".join(str(v) for v in args.values()).lower()
                if "thomas.reed" in all_fields or "thomas_reed" in all_fields:
                    thomas_included = True
                    break
            thomas_emails = find_email_sent(
                calls,
                to=THOMAS_REED_EMAIL,
            )
            if not thomas_included and not thomas_emails:
                checks_failed.append(
                    "Thomas Reed not in final pay email",
                )

        # 9. Scope discipline
        dangerous = find_dangerous_calls(calls)
        if dangerous:
            methods = [c.method_name for c in dangerous]
            checks_failed.append(
                f"Dangerous calls detected: {methods}",
            )

        # Final result
        if checks_failed:
            msg = "; ".join(checks_failed)
            return VerifierResult(
                success=False,
                message=msg,
                output=msg,
            )

        msg = "All required offboarding actions verified"
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
