"""Verifier for cs-207-escalation-flow.

Validates multi-level escalation with conflict resolution:
- Manager escalation (jennifer.lee) with context and response
- Billing consultation (diana.walsh) with financial questions and response
- VP escalation (robert.hayes) with synthesized summary and response
- Escalation ordering (jennifer → diana → robert)
- Helpdesk ticket documenting the full escalation chain
- Customer resolution message (james.wilson.wrg)
- Message quality checks (specificity, synthesis, professionalism)
"""

from __future__ import annotations

from collinear.core.run_artifacts import RunArtifacts
from collinear.core.verifier import VerifierResult

from .common import call_tool
from .common import find_ticket_id_by_subject
from .common import normalize_text


MANAGER_USERNAME = "jennifer.lee"
BILLING_USERNAME = "diana.walsh"
VP_USERNAME = "robert.hayes"
CUSTOMER_USERNAME = "james.wilson.wrg"
CUSTOMER_EMAIL = "james.wilson@wilsonretailgroup.com"
TICKET_SUBJECT = "Enterprise Escalation - Service Credit Request"


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


def _msg_contains_all(msgs: list[dict], keyword_groups: list[list[str]]) -> bool:
    """Check if messages collectively contain at least one keyword from each group."""
    all_text = ""
    for msg in msgs:
        text = msg.get("text")
        if isinstance(text, str):
            all_text += " " + normalize_text(text)
    return all(
        any(kw in all_text for kw in group)
        for group in keyword_groups
    )


def _get_all_text(msgs: list[dict]) -> str:
    """Concatenate all message text."""
    parts = []
    for msg in msgs:
        text = msg.get("text")
        if isinstance(text, str):
            parts.append(text)
    return " ".join(parts)


def _get_first_agent_timestamp(msgs: list[dict]) -> str:
    """Get timestamp of first agent message."""
    for msg in msgs:
        ts = msg.get("ts") or msg.get("timestamp") or ""
        if ts:
            return str(ts)
    return ""


def _get_ticket_text(helpdesk_url: str) -> tuple[dict | None, str, list[str]]:
    """Return (ticket, all_text, errors)."""
    errors: list[str] = []
    ticket_id = None
    try:
        ticket_id = find_ticket_id_by_subject(helpdesk_url, TICKET_SUBJECT)
    except Exception as exc:
        errors.append(f"Error searching for ticket: {exc}")
        return None, "", errors
    if not ticket_id:
        errors.append(f"No ticket found with subject '{TICKET_SUBJECT}'")
        return None, "", errors

    try:
        ticket = call_tool(helpdesk_url, "helpdesk_get_resource", {"ticket_id": ticket_id})
    except Exception as exc:
        errors.append(f"Error retrieving ticket {ticket_id}: {exc}")
        return None, "", errors
    if not isinstance(ticket, dict):
        errors.append("Could not retrieve escalation ticket")
        return None, "", errors

    desc = normalize_text(ticket.get("description") or "")
    comments = ticket.get("comments") or []
    all_comment_text = ""
    if isinstance(comments, list):
        for c in comments:
            if isinstance(c, dict):
                content = c.get("content") or ""
                if isinstance(content, str):
                    all_comment_text += " " + content
    return ticket, desc + " " + normalize_text(all_comment_text), errors


def verify(run_artifacts: RunArtifacts) -> VerifierResult:
    """Verify multi-level escalation workflow."""
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
    total_checks = 14

    # ============================================================
    # 1. MANAGER ESCALATION — agent messaged jennifer.lee
    # ============================================================
    mgr_agent, mgr_npc, err = _get_dm_messages(rc_url, MANAGER_USERNAME)
    if err:
        errors.append(f"Manager DM: {err}")
    else:
        # 1a. Agent sent escalation mentioning credit amount and customer
        credit_keywords = [
            "credit", "refund", "$25", "25,000", "25000",
            "service credit",
        ]
        customer_keywords = ["wilson", "enterprise", "outage", "terminate", "contract"]
        if mgr_agent and _msg_contains_any(mgr_agent, credit_keywords):
            checks_passed += 1
        else:
            errors.append(
                "Agent did not mention credit/refund amount in escalation to jennifer.lee"
            )

        # 1b. Agent included customer context (not just a bare ask)
        if mgr_agent and _msg_contains_any(mgr_agent, customer_keywords):
            checks_passed += 1
        else:
            errors.append(
                "Agent escalation to jennifer.lee lacks customer context "
                "(expected: customer name, enterprise tier, outage, or termination threat)"
            )

        # 1c. Manager responded
        if mgr_npc:
            checks_passed += 1
        else:
            errors.append("Manager jennifer.lee did not respond to escalation")

    # ============================================================
    # 2. BILLING CONSULTATION — agent messaged diana.walsh
    # ============================================================
    bill_agent, bill_npc, err = _get_dm_messages(rc_url, BILLING_USERNAME)
    if err:
        errors.append(f"Billing DM: {err}")
    else:
        # 2a. Agent asked about financials/account info
        billing_keywords = [
            "account", "spend", "annual", "history", "credit",
            "financial", "policy", "billing", "revenue", "impact",
            "precedent", "appropriate",
        ]
        if bill_agent and _msg_contains_any(bill_agent, billing_keywords):
            checks_passed += 1
        else:
            errors.append(
                "Agent did not ask diana.walsh about financial impact or account history"
            )

        # 2b. Agent mentioned the specific customer/amount
        if bill_agent and _msg_contains_any(
            bill_agent, ["wilson", "25,000", "$25", "25000", "retail"]
        ):
            checks_passed += 1
        else:
            errors.append(
                "Agent did not reference the specific customer or amount in billing consultation"
            )

        # 2c. Diana responded
        if bill_npc:
            checks_passed += 1
        else:
            errors.append("Billing specialist diana.walsh did not respond")

    # ============================================================
    # 3. VP ESCALATION — agent messaged robert.hayes with synthesis
    # ============================================================
    vp_agent, vp_npc, err = _get_dm_messages(rc_url, VP_USERNAME)
    if err:
        errors.append(f"VP DM: {err}")
    else:
        if vp_agent:
            vp_text = normalize_text(_get_all_text(vp_agent))

            # 3a. VP escalation references manager input
            has_manager_ref = any(
                kw in vp_text
                for kw in [
                    "jennifer", "manager", "denied", "smaller",
                    "counter", "goodwill", "authority", "approval limit",
                ]
            )
            # 3b. VP escalation references billing input
            has_billing_ref = any(
                kw in vp_text
                for kw in [
                    "diana", "billing", "financial", "spend",
                    "account history", "annual", "revenue", "assessment",
                ]
            )
            # 3c. Agent includes own recommendation
            has_recommendation = any(
                kw in vp_text
                for kw in [
                    "recommend", "suggest", "propose", "my recommendation",
                    "believe", "advise", "i think", "in my view",
                ]
            )

            # Synthesis check: must reference both manager and billing
            if has_manager_ref and has_billing_ref:
                checks_passed += 1
            elif has_manager_ref or has_billing_ref:
                errors.append(
                    "VP escalation partially synthesized — missing reference to "
                    + ("billing assessment" if has_manager_ref else "manager recommendation")
                )
            else:
                errors.append(
                    "VP escalation lacks synthesis — does not reference manager or billing inputs"
                )

            # Recommendation check
            if has_recommendation:
                checks_passed += 1
            else:
                errors.append(
                    "VP escalation missing agent's own recommendation"
                )
        else:
            errors.append("Agent did not send escalation to VP robert.hayes")

        # 3d. VP responded with a decision
        if vp_npc:
            checks_passed += 1
        else:
            errors.append("VP robert.hayes did not respond with a final decision")

    # ============================================================
    # 4. ESCALATION ORDER — jennifer before diana before robert
    # ============================================================
    mgr_ts = _get_first_agent_timestamp(mgr_agent) if mgr_agent else ""
    bill_ts = _get_first_agent_timestamp(bill_agent) if bill_agent else ""
    vp_ts = _get_first_agent_timestamp(vp_agent) if vp_agent else ""

    if mgr_ts and bill_ts and vp_ts:
        if mgr_ts <= bill_ts <= vp_ts:
            checks_passed += 1
        else:
            errors.append(
                f"Escalation order incorrect: jennifer={mgr_ts}, "
                f"diana={bill_ts}, robert={vp_ts} "
                f"(expected jennifer < diana < robert)"
            )
    elif mgr_ts or bill_ts or vp_ts:
        errors.append(
            "Cannot fully verify escalation order — missing timestamps for some NPCs"
        )
    else:
        errors.append("No agent messages found to any internal NPC — cannot check order")

    # ============================================================
    # 5. HELPDESK TICKET — documentation quality
    # ============================================================
    ticket, all_ticket_text, ticket_errors = _get_ticket_text(helpdesk_url)
    errors.extend(ticket_errors)

    if ticket:
        # 5a. Ticket linked to correct customer
        raised_by = normalize_text(ticket.get("raised_by") or "")
        if CUSTOMER_EMAIL.lower() in raised_by:
            checks_passed += 1
        else:
            errors.append(
                f"Ticket raised_by={ticket.get('raised_by')!r} "
                f"(expected {CUSTOMER_EMAIL!r})"
            )

        # 5b. Ticket documents escalation chain (references manager + credit)
        has_escalation_doc = (
            ("jennifer" in all_ticket_text or "manager" in all_ticket_text)
            and ("credit" in all_ticket_text or "refund" in all_ticket_text)
        )
        has_billing_doc = (
            "diana" in all_ticket_text or "billing" in all_ticket_text
            or "financial" in all_ticket_text
        )
        has_vp_doc = (
            "robert" in all_ticket_text or "vp" in all_ticket_text
            or "vice president" in all_ticket_text or "final decision" in all_ticket_text
        )

        doc_score = sum([has_escalation_doc, has_billing_doc, has_vp_doc])
        if doc_score >= 2:
            checks_passed += 1
        else:
            missing = []
            if not has_escalation_doc:
                missing.append("manager escalation")
            if not has_billing_doc:
                missing.append("billing consultation")
            if not has_vp_doc:
                missing.append("VP decision")
            errors.append(
                f"Ticket documentation incomplete — missing: {', '.join(missing)}"
            )

    # ============================================================
    # 6. CUSTOMER RESOLUTION — message to james.wilson.wrg
    # ============================================================
    cust_agent, cust_npc, err = _get_dm_messages(rc_url, CUSTOMER_USERNAME)
    if err:
        errors.append(f"Customer DM: {err}")
    else:
        # 6a. Agent sent resolution message with concrete outcome
        resolution_keywords = [
            "credit", "approved", "resolution", "decision",
            "compensat", "resolved", "outcome", "offer", "$",
        ]
        if cust_agent and _msg_contains_any(cust_agent, resolution_keywords):
            checks_passed += 1
        else:
            errors.append(
                "Agent did not send resolution message with concrete outcome to james.wilson.wrg"
            )

    # ============================================================
    # FINAL VERDICT
    # Two conditions must BOTH be met:
    #   1. At least 10/14 checks passed
    #   2. At least 2 of 3 internal NPCs responded (hard gate — agent must
    #      actually wait for responses, not fabricate decisions)
    # ============================================================
    npc_responses = sum([
        bool(mgr_npc),
        bool(bill_npc),
        bool(vp_npc),
    ])
    npc_gate_passed = npc_responses >= 2

    success = checks_passed >= 10 and npc_gate_passed
    npc_note = ""
    if not npc_gate_passed:
        npc_note = (
            f"; NPC response gate failed: only {npc_responses}/3 internal NPCs responded "
            f"(need 2+) — agent must wait for NPC replies before proceeding"
        )
    if success:
        return VerifierResult(
            success=True,
            message=(
                f"Multi-level escalation verified: {checks_passed}/{total_checks} "
                f"checks passed, {npc_responses}/3 NPCs responded"
            ),
        )
    return VerifierResult(
        success=False,
        message=(
            f"Escalation flow incomplete: {checks_passed}/{total_checks} checks passed"
            f"{npc_note}. "
            f"Failures: {'; '.join(errors)}"
        ),
    )
