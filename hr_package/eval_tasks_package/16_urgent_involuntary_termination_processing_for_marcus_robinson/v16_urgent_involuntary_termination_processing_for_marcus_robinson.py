"""Verifier for urgent involuntary termination processing for Marcus Robinson.

Checks HRIS termination, stakeholder comms, calendar scheduling,
information gathering sequence, and scope discipline.
"""

from __future__ import annotations

import logging

from collinear.core.run_artifacts import RunArtifacts
from collinear.scenarios.amazon_people_mgmt.verifiers.common import event_duration_minutes
from collinear.scenarios.amazon_people_mgmt.verifiers.common import event_has_attendee
from collinear.scenarios.amazon_people_mgmt.verifiers.common import extract_rocketchat_actions
from collinear.scenarios.amazon_people_mgmt.verifiers.common import extract_tool_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_dangerous_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_email_sent
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_events_created
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_reads
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_update
from collinear.scenarios.amazon_people_mgmt.verifiers.common import find_frappe_writes
from collinear.scenarios.amazon_people_mgmt.verifiers.common import get_frappe_calls
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_dm_sent
from collinear.scenarios.amazon_people_mgmt.verifiers.common import rocketchat_state_has_message_to
from collinear.workspace_controller.task_execution import VerifierResult

logger = logging.getLogger(__name__)

# Key people
EMPLOYEE_NAME = "Marcus Robinson"
EMPLOYEE_EMP_ID = "EMP-019"

VICTORIA_USERNAME = "victoria_wells"
VICTORIA_EMAIL = "victoria.wells@amazon.com"

DANIEL_USERNAME = "daniel_harris"
DANIEL_EMAIL = "daniel.harris@amazon.com"

ROBERT_USERNAME = "robert_kim"
ROBERT_EMAIL = "robert.kim@amazon.com"


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify task completion from message-level tool call evidence."""
    try:
        calls = extract_tool_calls(run_artifacts.messages or [])
        frappe = get_frappe_calls(calls)
        chat_actions = extract_rocketchat_actions(calls)
        checks_failed: list[str] = []

        # ---------------------------------------------------------------
        # 1. Information Gathering: Read Victoria's seed email
        # ---------------------------------------------------------------
        email_reads = [
            c
            for c in calls
            if c.server_name == "email-env" and c.method_name in ("search_emails", "get_email")
        ]
        if not email_reads:
            checks_failed.append(
                "No email read/search found — agent should read Victoria's security breach email"
            )

        # ---------------------------------------------------------------
        # 2. Contact Daniel Harris to confirm termination reason code
        #    (via chat or email — he has a secret)
        # ---------------------------------------------------------------
        contacted_daniel_chat = rocketchat_dm_sent(
            chat_actions, DANIEL_USERNAME
        ) or rocketchat_state_has_message_to(calls, DANIEL_USERNAME)
        contacted_daniel_email = bool(find_email_sent(calls, to=DANIEL_EMAIL))
        contacted_daniel = contacted_daniel_chat or contacted_daniel_email
        if not contacted_daniel:
            checks_failed.append(
                f"No contact with Daniel Harris ({DANIEL_USERNAME}) "
                "to confirm termination reason code"
            )

        # ---------------------------------------------------------------
        # 3. Contact Victoria Wells on chat for handover instructions
        #    (she has a secret about Atlas Infrastructure Migration)
        # ---------------------------------------------------------------
        contacted_victoria_chat = rocketchat_dm_sent(
            chat_actions, VICTORIA_USERNAME
        ) or rocketchat_state_has_message_to(calls, VICTORIA_USERNAME)
        if not contacted_victoria_chat:
            checks_failed.append(
                f"No chat message to Victoria Wells ({VICTORIA_USERNAME}) "
                "to retrieve handover instructions"
            )

        # ---------------------------------------------------------------
        # 4. HRIS lookup for Marcus Robinson
        # ---------------------------------------------------------------
        emp_reads = find_frappe_reads(frappe, doctype="Employee", name_contains="Marcus")
        if not emp_reads:
            emp_reads = find_frappe_reads(frappe, doctype="Employee", name_contains="Robinson")
        if not emp_reads:
            emp_reads = find_frappe_reads(frappe, doctype="Employee", name_contains="EMP-019")
        if not emp_reads:
            checks_failed.append(f"No HRIS lookup found for {EMPLOYEE_NAME}")

        # ---------------------------------------------------------------
        # 5. HRIS termination update for Marcus Robinson
        # ---------------------------------------------------------------
        termination_updates = find_frappe_update(frappe, doctype="Employee")
        # Also check for frappe_call_method or frappe_create_resource
        # that might process termination
        termination_writes = find_frappe_writes(frappe, doctype="Employee")
        hris_updated = bool(termination_updates) or bool(termination_writes)
        if not hris_updated:
            checks_failed.append("No HRIS Employee update/write found for termination")

        # ---------------------------------------------------------------
        # 6. Sequencing: Daniel Harris contacted BEFORE HRIS update
        # ---------------------------------------------------------------
        if contacted_daniel and hris_updated:
            # Check that the contact with Daniel happened before
            # the HRIS write. We check by index in the calls list.
            daniel_contact_idx = None
            hris_write_idx = None

            for i, c in enumerate(calls):
                if daniel_contact_idx is None:
                    # Check chat
                    if c.server_name == "playwright-mcp" and c.method_name in (
                        "browser_type",
                        "browser_click",
                        "browser_navigate",
                        "browser_press_key",
                    ):
                        args_str = str(c.args).lower()
                        if DANIEL_USERNAME in args_str:
                            daniel_contact_idx = i
                    # Check email
                    if c.server_name == "email-env" and c.method_name == "send_email":
                        args_str = str(c.args).lower()
                        if DANIEL_EMAIL.lower() in args_str:
                            daniel_contact_idx = i

                if hris_write_idx is None and (
                    c.server_name == "frappe-hrms-env"
                    and c.method_name
                    in (
                        "frappe_update_resource",
                        "frappe_call_method",
                        "frappe_create_resource",
                    )
                ):
                    args_str = str(c.args).lower()
                    if "employee" in args_str and (
                        "marcus" in args_str
                        or "robinson" in args_str
                        or "emp-019" in args_str
                        or "terminat" in args_str
                        or "left" in args_str
                        or "inactive" in args_str
                    ):
                        hris_write_idx = i

            if (
                daniel_contact_idx is not None
                and hris_write_idx is not None
                and daniel_contact_idx > hris_write_idx
            ):
                checks_failed.append(
                    "HRIS termination was processed BEFORE contacting "
                    "Daniel Harris to confirm the reason code"
                )

        # ---------------------------------------------------------------
        # 7. Email sent to Victoria Wells confirming termination
        # ---------------------------------------------------------------
        victoria_emails = find_email_sent(calls, to=VICTORIA_EMAIL)
        if not victoria_emails:
            checks_failed.append(
                f"No email sent to Victoria Wells ({VICTORIA_EMAIL}) confirming the termination"
            )

        # ---------------------------------------------------------------
        # 8. Chat to Robert Kim with dismissal info + handover
        # ---------------------------------------------------------------
        robert_chat = rocketchat_dm_sent(
            chat_actions, ROBERT_USERNAME
        ) or rocketchat_state_has_message_to(calls, ROBERT_USERNAME)
        if not robert_chat:
            checks_failed.append(
                f"No chat message to Robert Kim ({ROBERT_USERNAME}) "
                "informing of the dismissal and handover instructions"
            )

        # ---------------------------------------------------------------
        # 9. Calendar: 30-min offboarding review with Victoria & Daniel
        # ---------------------------------------------------------------
        events = find_events_created(calls)
        if not events:
            checks_failed.append("No calendar event created for offboarding review")
        else:
            # Find an event that has both Victoria and Daniel
            matching_event = None
            for ev in events:
                has_victoria = event_has_attendee(ev, VICTORIA_EMAIL)
                has_daniel = event_has_attendee(ev, DANIEL_EMAIL)
                if has_victoria and has_daniel:
                    matching_event = ev
                    break

            if matching_event is None:
                # Check with looser matching in arguments
                for ev in events:
                    args_str = str(ev.args).lower()
                    has_v = (
                        "victoria" in args_str
                        or VICTORIA_EMAIL.lower() in args_str
                        or VICTORIA_USERNAME in args_str
                    )
                    has_d = (
                        "daniel" in args_str
                        or DANIEL_EMAIL.lower() in args_str
                        or DANIEL_USERNAME in args_str
                    )
                    if has_v and has_d:
                        matching_event = ev
                        break

            if matching_event is None:
                checks_failed.append(
                    "No calendar event found with BOTH Victoria Wells "
                    "and Daniel Harris as attendees"
                )
            else:
                dur = event_duration_minutes(matching_event)
                if dur is not None and dur != 30:
                    checks_failed.append(
                        f"Offboarding review meeting duration is {dur} min, expected 30"
                    )

        # ---------------------------------------------------------------
        # 10. Scope discipline: no dangerous calls
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
