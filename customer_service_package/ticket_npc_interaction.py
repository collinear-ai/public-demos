"""Verifier for cs-208-ticket-npc-interaction.

Validates multi-customer ticket triage with engineering escalation:
- Enterprise ticket (david.park) with Urgent priority and full lifecycle
- SMB ticket (alex.thompson) with Medium priority
- Engineering escalation to marcus.chen with technical details
- Priority triage ordering (enterprise first)
- Cross-system references (ticket <-> chat)
- Complete audit trails in ticket comments
- Quality checks: NPC response incorporation, escalation detail depth
"""

from __future__ import annotations

from collinear.core.run_artifacts import RunArtifacts
from collinear.core.verifier import VerifierResult

from .common import call_tool
from .common import find_ticket_id_by_subject
from .common import normalize_text


DAVID_USERNAME = "david.park"
DAVID_EMAIL = "david.park@parkindustries.com"
ALEX_USERNAME = "alex.thompson"
ALEX_EMAIL = "alex.thompson@thompsondesign.co"
MARCUS_USERNAME = "marcus.chen"

ENTERPRISE_SUBJECT = "API 500 Errors - Bulk Import Failure"
SMB_SUBJECT = "Dashboard Performance Issue"


def _get_dm_messages(
    rc_url: str, username: str
) -> tuple[list[dict], list[dict], str | None]:
    """Return (agent_msgs, npc_msgs, error) for a DM room."""
    try:
        dm = call_tool(rc_url, "rocketchat_get_dm_room", {"username": username})
    except Exception as exc:
        return [], [], f"rocketchat_get_dm_room failed for {username}: {exc}"
    if not isinstance(dm, dict):
        return [], [], f"Could not get DM room for {username} (got {type(dm).__name__})"
    room_id = dm.get("room_id")
    if not isinstance(room_id, str) or not room_id:
        return [], [], f"Missing room_id for {username} (response: {dm})"
    try:
        history = call_tool(
            rc_url, "rocketchat_get_room_history", {"room_id": room_id, "count": 200}
        )
    except Exception as exc:
        return [], [], f"rocketchat_get_room_history failed for {username}: {exc}"
    if not isinstance(history, list):
        return [], [], f"Could not get history for {username} (got {type(history).__name__})"

    agent_msgs: list[dict] = []
    npc_msgs: list[dict] = []
    for msg in history:
        if not isinstance(msg, dict):
            continue
        u = msg.get("username")
        if not isinstance(u, str):
            continue
        if normalize_text(u) == "agent":
            agent_msgs.append(msg)
        elif normalize_text(u) == normalize_text(username):
            npc_msgs.append(msg)
    return agent_msgs, npc_msgs, None


def _msg_contains_any(msgs: list[dict], keywords: list[str]) -> bool:
    """Check if any message text contains at least one keyword."""
    for msg in msgs:
        text = msg.get("text")
        if not isinstance(text, str):
            continue
        text_lower = normalize_text(text)
        if any(kw in text_lower for kw in keywords):
            return True
    return False


def _get_all_text(msgs: list[dict]) -> str:
    """Get concatenated text of all messages."""
    parts = []
    for msg in msgs:
        text = msg.get("text")
        if isinstance(text, str):
            parts.append(text)
    return " ".join(parts)


def _find_ticket_robust(
    helpdesk_url: str, subject: str, customer_email: str | None = None
) -> tuple[dict | None, str | None, str | None]:
    """Find a ticket by subject with multiple fallback strategies."""
    ticket_id = None
    try:
        ticket_id = find_ticket_id_by_subject(helpdesk_url, subject)
    except Exception:
        pass

    if not ticket_id:
        try:
            tickets = call_tool(
                helpdesk_url, "helpdesk_list_resource", {"limit": 50}
            )
            if isinstance(tickets, list):
                subject_lower = subject.strip().lower()
                for t in tickets:
                    if not isinstance(t, dict):
                        continue
                    t_subj = (t.get("subject") or "").strip().lower()
                    if subject_lower in t_subj or t_subj in subject_lower:
                        ticket_id = t.get("name") or t.get("ticket_id")
                        break
                if not ticket_id:
                    subject_words = set(subject_lower.split())
                    best_overlap = 0
                    for t in tickets:
                        if not isinstance(t, dict):
                            continue
                        t_subj = (t.get("subject") or "").strip().lower()
                        t_words = set(t_subj.split())
                        overlap = len(subject_words & t_words)
                        if overlap > best_overlap and overlap >= 3:
                            best_overlap = overlap
                            ticket_id = t.get("name") or t.get("ticket_id")
                if not ticket_id and customer_email:
                    for t in tickets:
                        if not isinstance(t, dict):
                            continue
                        raised = (t.get("raised_by") or "").strip().lower()
                        if raised == customer_email.lower():
                            ticket_id = t.get("name") or t.get("ticket_id")
                            break
        except Exception:
            pass

    if not ticket_id:
        return None, None, f"No ticket found matching subject '{subject}'"

    try:
        ticket = call_tool(helpdesk_url, "helpdesk_get_resource", {"ticket_id": ticket_id})
    except Exception as exc:
        return None, ticket_id, f"Error retrieving ticket {ticket_id}: {exc}"
    if not isinstance(ticket, dict):
        return None, ticket_id, f"Could not retrieve ticket {ticket_id}"
    return ticket, ticket_id, None


def _count_comments(ticket: dict) -> int:
    """Count comments on a ticket."""
    comments = ticket.get("comments")
    if not isinstance(comments, list):
        return 0
    return len(comments)


def _ticket_comments_text(ticket: dict) -> str:
    """Get all comment text from a ticket, concatenated."""
    comments = ticket.get("comments")
    if not isinstance(comments, list):
        return ""
    parts = []
    for c in comments:
        if isinstance(c, dict):
            content = c.get("content") or ""
            if isinstance(content, str):
                parts.append(content)
    return " ".join(parts)


def _get_all_ticket_text(ticket: dict) -> str:
    """Get description + all comment text."""
    desc = ticket.get("description") or ""
    return normalize_text(desc + " " + _ticket_comments_text(ticket))


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify multi-customer ticket triage with engineering escalation."""
    rc_url = run_artifacts.server_url("rocketchat-env")
    if not rc_url:
        return VerifierResult(success=False, message="Missing Tool Server URL for rocketchat-env")

    helpdesk_url = run_artifacts.server_url("frappe-helpdesk-env")
    if not helpdesk_url:
        return VerifierResult(
            success=False, message="Missing Tool Server URL for frappe-helpdesk-env"
        )

    errors: list[str] = []
    checks_passed = 0
    total_checks = 18

    # ===== ENTERPRISE TICKET (david.park) =====

    ent_ticket, ent_ticket_id, err = _find_ticket_robust(
        helpdesk_url, ENTERPRISE_SUBJECT, DAVID_EMAIL
    )
    if err or ent_ticket is None:
        errors.append(f"Enterprise ticket: {err}")
    else:
        # 1. Priority is Urgent
        priority = normalize_text(ent_ticket.get("priority") or "")
        if "urgent" in priority or "high" in priority:
            checks_passed += 1
        else:
            errors.append(
                f"Enterprise ticket priority='{ent_ticket.get('priority')}' (expected Urgent)"
            )

        # 2. Status is In Progress or beyond
        status = normalize_text(ent_ticket.get("status") or "")
        if any(s in status for s in ["in progress", "open", "replied", "resolved"]):
            checks_passed += 1
        else:
            errors.append(
                f"Enterprise ticket status='{ent_ticket.get('status')}' (expected In Progress+)"
            )

        # 3. Linked to david.park email
        raised_by = normalize_text(ent_ticket.get("raised_by") or "")
        if DAVID_EMAIL.lower() in raised_by:
            checks_passed += 1
        else:
            errors.append(
                f"Enterprise ticket raised_by={ent_ticket.get('raised_by')!r} "
                f"(expected {DAVID_EMAIL!r})"
            )

        # 4. Has 3+ comments (audit trail)
        comment_count = _count_comments(ent_ticket)
        if comment_count >= 3:
            checks_passed += 1
        else:
            errors.append(f"Enterprise ticket has {comment_count} comments (need 3+)")

        # 5. Has chat/escalation cross-references
        all_ticket_text = _get_all_ticket_text(ent_ticket)
        has_chat_ref = any(
            kw in all_ticket_text
            for kw in [
                "rocket", "chat", "room", "dm", "conversation",
                "marcus", "engineering", "escalat",
            ]
        )
        if has_chat_ref:
            checks_passed += 1
        else:
            errors.append("Enterprise ticket missing cross-reference to chat/escalation")

        # 6. Ticket comments contain technical detail (not just "investigating")
        has_technical_detail = any(
            kw in all_ticket_text
            for kw in [
                "500", "api", "bulk", "import", "endpoint", "payload",
                "error", "timestamp", "reproduction",
            ]
        )
        if has_technical_detail:
            checks_passed += 1
        else:
            errors.append(
                "Enterprise ticket comments lack technical detail "
                "(expected: error codes, API references, reproduction info)"
            )

        # 7. Ticket updated with customer-provided details (not just initial report)
        has_customer_update = any(
            kw in all_ticket_text
            for kw in [
                "customer provided", "david", "additional detail",
                "update", "reported", "confirmed", "says",
            ]
        )
        if has_customer_update:
            checks_passed += 1
        else:
            errors.append(
                "Enterprise ticket not updated with information from customer conversation"
            )

    # ===== ENTERPRISE CHAT (david.park) =====

    david_agent, david_npc, err = _get_dm_messages(rc_url, DAVID_USERNAME)
    if err:
        errors.append(f"David DM: {err}")
    else:
        # 8. Agent messaged David AND David responded
        if david_agent and david_npc:
            checks_passed += 1
        elif david_agent and not david_npc:
            errors.append("David did not respond to agent's message")
        else:
            errors.append("Agent did not message david.park")

        # 9. Agent sent 2+ messages to David (initial contact + follow-up with eng update)
        if len(david_agent) >= 2:
            checks_passed += 1
        else:
            errors.append(
                f"Agent sent only {len(david_agent)} message(s) to David "
                f"(need 2+: initial contact + engineering update)"
            )

        # 10. Agent's follow-up to David references engineering/timeline/update
        if len(david_agent) >= 2:
            later_msgs = david_agent[1:]
            eng_update_keywords = [
                "engineer", "marcus", "team", "investigating", "timeline",
                "update", "working on", "looking into", "fix", "resolution",
            ]
            if _msg_contains_any(later_msgs, eng_update_keywords):
                checks_passed += 1
            else:
                errors.append(
                    "Agent's follow-up message to David doesn't reference "
                    "engineering update or timeline"
                )

    # ===== ENGINEERING ESCALATION (marcus.chen) =====

    marcus_agent, marcus_npc, err = _get_dm_messages(rc_url, MARCUS_USERNAME)
    if err:
        errors.append(f"Marcus DM: {err}")
    else:
        # 11. Agent escalated with technical details
        technical_keywords = [
            "500", "api", "error", "bulk", "import", "endpoint",
            "payload", "reproduce", "timestamp", "failing", "integration",
        ]
        if marcus_agent and _msg_contains_any(marcus_agent, technical_keywords):
            checks_passed += 1
        elif marcus_agent:
            errors.append("Engineering escalation lacks specific technical details")
        else:
            errors.append("Agent did not escalate to marcus.chen")

        # 12. Marcus responded
        if marcus_npc:
            checks_passed += 1
        elif not err:
            errors.append("marcus.chen did not respond")

        # 13. Engineering escalation mentions customer impact
        if marcus_agent:
            impact_keywords = [
                "enterprise", "blocking", "team", "production",
                "critical", "urgent", "customer", "david", "park industries",
            ]
            if _msg_contains_any(marcus_agent, impact_keywords):
                checks_passed += 1
            else:
                errors.append(
                    "Engineering escalation doesn't mention customer impact or urgency"
                )

    # ===== SMB TICKET (alex.thompson) =====

    smb_ticket, smb_ticket_id, err = _find_ticket_robust(
        helpdesk_url, SMB_SUBJECT, ALEX_EMAIL
    )
    if err or smb_ticket is None:
        errors.append(f"SMB ticket: {err}")
    else:
        # 14. Priority is Medium
        priority = normalize_text(smb_ticket.get("priority") or "")
        if any(p in priority for p in ["medium", "low", "normal"]):
            checks_passed += 1
        else:
            errors.append(
                f"SMB ticket priority='{smb_ticket.get('priority')}' (expected Medium)"
            )

        # 15. Linked to alex.thompson email
        raised_by = normalize_text(smb_ticket.get("raised_by") or "")
        if ALEX_EMAIL.lower() in raised_by:
            checks_passed += 1
        else:
            errors.append(
                f"SMB ticket raised_by={smb_ticket.get('raised_by')!r} "
                f"(expected {ALEX_EMAIL!r})"
            )

    # ===== SMB CHAT (alex.thompson) =====

    alex_agent, alex_npc, err = _get_dm_messages(rc_url, ALEX_USERNAME)
    if err:
        errors.append(f"Alex DM: {err}")
    else:
        # 16. Agent messaged Alex
        if alex_agent:
            checks_passed += 1
        else:
            errors.append("Agent did not message alex.thompson")

        # 17. Alex responded AND agent updated SMB ticket with Alex's details
        if alex_npc and smb_ticket:
            smb_text = _get_all_ticket_text(smb_ticket) if smb_ticket else ""
            has_alex_detail = any(
                kw in smb_text
                for kw in [
                    "dashboard", "alex", "slow", "performance",
                    "customer", "detail", "report", "update",
                ]
            )
            if has_alex_detail:
                checks_passed += 1
            else:
                errors.append(
                    "SMB ticket not updated with Alex's response details"
                )
        elif not alex_npc:
            errors.append("Alex did not respond")

    # ===== TRIAGE ORDERING =====

    # 18. Enterprise ticket created before SMB ticket
    if ent_ticket and smb_ticket:
        ent_created = ent_ticket.get("creation") or ent_ticket.get("created_at") or ""
        smb_created = smb_ticket.get("creation") or smb_ticket.get("created_at") or ""
        if isinstance(ent_created, str) and isinstance(smb_created, str):
            if ent_created and smb_created and ent_created <= smb_created:
                checks_passed += 1
            elif ent_created and smb_created:
                errors.append(
                    f"Triage order wrong: enterprise={ent_created}, SMB={smb_created}"
                )
            else:
                errors.append("Cannot determine ticket creation timestamps")
        else:
            errors.append("Ticket creation timestamps not available")
    elif ent_ticket and not smb_ticket:
        pass  # Enterprise handled, SMB missing — triage direction correct
    else:
        errors.append("Cannot check triage ordering — tickets missing")

    # ===== FINAL VERDICT =====
    # Two conditions must BOTH be met:
    #   1. At least 12/18 checks passed
    #   2. Hard gate: David AND Marcus must have responded (agent must wait
    #      for NPC replies, not proceed without real input)
    david_responded = bool(david_npc)
    marcus_responded = bool(marcus_npc)
    npc_gate_passed = david_responded and marcus_responded

    success = checks_passed >= 12 and npc_gate_passed
    npc_note = ""
    if not npc_gate_passed:
        missing_npcs = []
        if not david_responded:
            missing_npcs.append("david.park")
        if not marcus_responded:
            missing_npcs.append("marcus.chen")
        npc_note = (
            f"; NPC response gate failed: {', '.join(missing_npcs)} did not respond "
            f"— agent must wait for NPC replies before proceeding"
        )
    if success:
        return VerifierResult(
            success=True,
            message=(
                f"Multi-customer ticket triage verified: {checks_passed}/{total_checks} "
                f"checks passed, all critical NPCs responded"
            ),
        )
    return VerifierResult(
        success=False,
        message=(
            f"Ticket triage incomplete: {checks_passed}/{total_checks} checks passed"
            f"{npc_note}. "
            f"Failures: {'; '.join(errors)}"
        ),
    )
