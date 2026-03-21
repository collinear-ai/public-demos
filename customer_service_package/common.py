"""Messages-based verification helpers for generated verifiers.

All helpers operate on ``run_artifacts.messages`` only — no HTTP calls,
no ``run_artifacts.diffs``.  Verifiers import these primitives and chain
them into pure logic checks.

Supported tool servers: Frappe HRIS, Frappe Helpdesk, Email,
Calendar (Chronos), RocketChat (via Playwright), Playwright.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any

import requests


def call_tool(tool_server_url: str, tool_name: str, parameters: dict[str, Any]) -> Any:  # noqa: ANN401
    """Call a Tool Server tool via HTTP and return structured content when possible."""
    url = tool_server_url.rstrip("/") + "/step"
    resp = requests.post(
        url,
        json={"action": {"tool_name": tool_name, "parameters": parameters}},
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    # Unwrap observation envelope if present (tool servers wrap responses)
    if "observation" in body and isinstance(body["observation"], dict):
        body = body["observation"]
    if body.get("is_error"):
        raise RuntimeError(body.get("text") or f"{tool_name} failed")
    if body.get("structured_content") is not None:
        return body["structured_content"]
    text = body.get("text") or ""
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def normalize_text(value: str | None) -> str:
    """Lowercase and strip whitespace for fuzzy comparison."""
    return (value or "").strip().lower()


def find_ticket_id_by_subject(
    helpdesk_url: str,
    subject: str,
) -> str | None:
    """Search helpdesk tickets by subject and return the first match's name."""
    # Try keyword search first (more targeted)
    try:
        results = call_tool(
            helpdesk_url,
            "helpdesk_search_documents",
            {"query": subject, "limit": 20},
        )
        if isinstance(results, list):
            subject_lower = subject.strip().lower()
            for ticket in results:
                if not isinstance(ticket, dict):
                    continue
                ticket_subject = (ticket.get("subject") or "").strip().lower()
                if subject_lower in ticket_subject or ticket_subject in subject_lower:
                    return ticket.get("name") or ticket.get("ticket_id")
    except (RuntimeError, Exception):
        pass

    # Fall back to listing all tickets
    try:
        tickets = call_tool(
            helpdesk_url,
            "helpdesk_list_resource",
            {"limit": 100},
        )
    except (RuntimeError, Exception):
        return None
    if not isinstance(tickets, list):
        tickets = (tickets or {}).get("data", [])
    subject_lower = subject.strip().lower()
    for ticket in tickets:
        if not isinstance(ticket, dict):
            continue
        ticket_subject = (ticket.get("subject") or "").strip().lower()
        if subject_lower in ticket_subject or ticket_subject in subject_lower:
            return ticket.get("name") or ticket.get("ticket_id")
    return None


class VerifierResult:
    """Result from a verifier execution."""

    def __init__(self, success: bool, message: str = "", output: str = "") -> None:
        """Initialize with success flag and optional message/output."""
        self.success = success
        self.message = message
        self.output = output

    def __bool__(self) -> bool:
        """Treat success as truthy."""
        return self.success


class RunArtifacts:
    """Type stub for verify() — real class injected at runtime."""

    messages: list[dict[str, object]]
    diffs: dict[str, object]
    final_observation: str

    def server_url(self, name: str) -> str:  # noqa: D102
        ...

    def tool_server_url(self, name: str) -> str:  # noqa: D102
        ...


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants: tool classification
# ---------------------------------------------------------------------------

FRAPPE_READ_METHODS: frozenset[str] = frozenset(
    {
        "frappe_search_documents",
        "frappe_list_doctypes",
        "frappe_get_doctype",
        "frappe_list_resource",
        "frappe_get_resource",
    }
)

FRAPPE_WRITE_METHODS: frozenset[str] = frozenset(
    {
        "frappe_create_resource",
        "frappe_update_resource",
        "frappe_delete_resource",
        "frappe_call_method",
    }
)

EMAIL_READ_METHODS: frozenset[str] = frozenset(
    {
        "search_emails",
        "get_email",
    }
)

EMAIL_WRITE_METHODS: frozenset[str] = frozenset(
    {
        "send_email",
        "delete_all_emails",
    }
)

CALENDAR_READ_METHODS: frozenset[str] = frozenset(
    {
        "list_accounts",
        "test_account",
        "list_calendars",
        "get_events_range",
        "search_events",
        "list_tasks",
        "list_journals",
    }
)

CALENDAR_WRITE_METHODS: frozenset[str] = frozenset(
    {
        "add_account",
        "remove_account",
        "create_calendar",
        "delete_calendar",
        "create_event",
        "update_event",
        "delete_event",
        "create_recurring_event",
        "bulk_create_events",
        "bulk_delete_events",
        "create_task",
        "update_task",
        "delete_task",
        "bulk_create_tasks",
        "bulk_delete_tasks",
        "create_journal",
        "update_journal",
        "delete_journal",
        "bulk_create_journals",
        "bulk_delete_journals",
    }
)

# Playwright tools that change page state
PLAYWRIGHT_MUTATING_METHODS: frozenset[str] = frozenset(
    {
        "browser_click",
        "browser_type",
        "browser_fill_form",
        "browser_press_key",
        "browser_select_option",
        "browser_drag",
        "browser_run_code",
        "browser_evaluate",
        "browser_handle_dialog",
        "browser_file_upload",
    }
)

# Helpdesk read tools
HELPDESK_READ_METHODS: frozenset[str] = frozenset(
    {
        "helpdesk_get_resource",
        "helpdesk_list_resource",
        "helpdesk_search_documents",
        "helpdesk_search_kb",
        "helpdesk_get_kb_article",
        "helpdesk_get_sla",
        "helpdesk_check_sla_status",
        "helpdesk_get_assignment_rules",
        "helpdesk_list_saved_replies",
        "helpdesk_render_saved_reply",
    }
)

# Helpdesk write tools
HELPDESK_WRITE_METHODS: frozenset[str] = frozenset(
    {
        "helpdesk_create_resource",
        "helpdesk_update_resource",
        "helpdesk_assign_ticket",
        "helpdesk_create_ticket_from_chat",
        "helpdesk_link_chat_to_ticket",
        "helpdesk_send_ticket_email",
        "helpdesk_send_internal_email",
    }
)

STATE_CHANGING_METHODS: frozenset[str] = (
    FRAPPE_WRITE_METHODS
    | EMAIL_WRITE_METHODS
    | CALENDAR_WRITE_METHODS
    | PLAYWRIGHT_MUTATING_METHODS
    | HELPDESK_WRITE_METHODS
)

DANGEROUS_METHODS: frozenset[str] = frozenset(
    {
        "delete_all_emails",
        "delete_calendar",
        "remove_account",
        "frappe_delete_resource",
        "bulk_delete_events",
        "bulk_delete_tasks",
        "bulk_delete_journals",
    }
)

# Servers whose mutating tool calls produce [STATE DIFF] blocks
SERVERS_WITH_SNAPSHOTS: frozenset[str] = frozenset(
    {
        "frappe-hrms-env",
        "frappe-helpdesk-env",
        "chronos-server",
        "email-env",
        "rocketchat-env",
    }
)

# ---------------------------------------------------------------------------
# Core dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ToolCall:
    """A single tool invocation extracted from the message history."""

    call_id: str
    tool_name: str  # e.g. "frappe-hrms-env__frappe_update_resource"
    server_name: str  # e.g. "frappe-hrms-env"
    method_name: str  # e.g. "frappe_update_resource"
    args: dict  # Parsed from stringified JSON
    response: str | None = None
    state_diff: str | None = None
    rocketchat_state: str | None = None
    message_index: int = 0
    is_mutating: bool = False


@dataclass
class RocketChatAction:
    """A RocketChat interaction extracted from Playwright tool calls."""

    recipient: str | None = None
    channel_type: str | None = None  # "direct", "channel", or None
    message_text: str | None = None
    method_name: str = ""
    call_id: str = ""
    message_index: int = 0


# ---------------------------------------------------------------------------
# 5.2  Extraction functions
# ---------------------------------------------------------------------------

_STATE_DIFF_RE = re.compile(r"\n\n\[STATE DIFF\]\n(.+)", re.DOTALL)
_ROCKETCHAT_STATE_RE = re.compile(
    r"\n\n(?:RocketChat State|Rocket\.Chat State|"
    r"\[RocketChat State\])\n(.+)",
    re.DOTALL,
)


def _parse_iso_datetime_utc(value: str) -> datetime:
    """Parse ISO datetime text and normalize to UTC-aware datetimes.

    - Supports trailing ``Z`` timestamps by converting to ``+00:00``.
    - Interprets naive timestamps as UTC.
    """
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _split_response_blocks(content: str) -> tuple[str, str | None, str | None]:
    """Split tool response into (body, state_diff, rocketchat_state)."""
    state_diff: str | None = None
    rocketchat_state: str | None = None

    m = _STATE_DIFF_RE.search(content)
    if m:
        state_diff = m.group(1).strip()

    m = _ROCKETCHAT_STATE_RE.search(content)
    if m:
        rocketchat_state = m.group(1).strip()

    # Body is everything before first special block
    body = content
    for marker in (
        "\n\n[STATE DIFF]\n",
        "\n\nRocketChat State\n",
        "\n\nRocket.Chat State\n",
        "\n\n[RocketChat State]\n",
    ):
        idx = content.find(marker)
        if idx != -1:
            body = content[:idx]
            break

    return body, state_diff, rocketchat_state


def extract_tool_calls(messages: list[dict]) -> list[ToolCall]:
    """Extract all ToolCall records from the message history in order."""
    # Build response lookup: tool_call_id -> content
    response_map: dict[str, str] = {}
    for msg in messages:
        if msg.get("role") == "tool":
            tcid = msg.get("tool_call_id", "")
            content = msg.get("content", "")
            if tcid:
                response_map[tcid] = content if isinstance(content, str) else str(content)

    calls: list[ToolCall] = []
    for msg_idx, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        for tc in msg.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            full_name = fn.get("name", "")
            call_id = tc.get("id", "")

            # Parse server__method
            parts = full_name.split("__", 1)
            server_name = parts[0] if len(parts) == 2 else ""
            method_name = parts[1] if len(parts) == 2 else full_name

            # Parse args
            raw_args = fn.get("arguments", "{}")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except (json.JSONDecodeError, TypeError):
                args = {}
            if not isinstance(args, dict):
                args = {}

            # Get response and split blocks
            resp_content = response_map.get(call_id)
            state_diff = None
            rocketchat_state = None
            if resp_content:
                _, state_diff, rocketchat_state = _split_response_blocks(resp_content)

            calls.append(
                ToolCall(
                    call_id=call_id,
                    tool_name=full_name,
                    server_name=server_name,
                    method_name=method_name,
                    args=args,
                    response=resp_content,
                    state_diff=state_diff,
                    rocketchat_state=rocketchat_state,
                    message_index=msg_idx,
                    is_mutating=method_name in STATE_CHANGING_METHODS,
                )
            )
    return calls


def get_calls_for_server(
    calls: list[ToolCall],
    server: str,
) -> list[ToolCall]:
    """Filter tool calls by server name."""
    return [c for c in calls if c.server_name == server]


def get_calls_for_method(
    calls: list[ToolCall],
    method: str,
) -> list[ToolCall]:
    """Filter tool calls by method name."""
    return [c for c in calls if c.method_name == method]


def get_mutating_calls(calls: list[ToolCall]) -> list[ToolCall]:
    """Return only state-changing tool calls."""
    return [c for c in calls if c.is_mutating]


def get_read_only_calls(calls: list[ToolCall]) -> list[ToolCall]:
    """Return only read-only tool calls."""
    return [c for c in calls if not c.is_mutating]


def parse_state_diffs_from_calls(calls: list[ToolCall]) -> list[str]:
    """Return all non-empty state_diff strings."""
    return [c.state_diff for c in calls if c.state_diff]


# ---------------------------------------------------------------------------
# 5.3  Frappe HRIS helpers
# ---------------------------------------------------------------------------


def get_frappe_calls(
    calls: list[ToolCall],
    method: str | None = None,
    doctype: str | None = None,
) -> list[ToolCall]:
    """Filter to frappe-hrms-env calls, optionally by method and/or doctype."""
    result = [c for c in calls if c.server_name == "frappe-hrms-env"]
    if method:
        result = [c for c in result if c.method_name == method]
    if doctype:
        dt_lower = doctype.lower()
        result = [
            c for c in result if normalize_text(str(c.args.get("doctype", ""))).lower() == dt_lower
        ]
    return result


def find_frappe_reads(
    calls: list[ToolCall],
    doctype: str | None = None,
    name_contains: str | None = None,
) -> list[ToolCall]:
    """Find Frappe read calls, optionally matching doctype or name/query."""
    result = [
        c
        for c in calls
        if c.server_name == "frappe-hrms-env" and c.method_name in FRAPPE_READ_METHODS
    ]
    if doctype:
        dt_lower = doctype.lower()
        result = [
            c
            for c in result
            if normalize_text(str(c.args.get("doctype", ""))).lower() == dt_lower
            or (
                c.method_name == "frappe_search_documents"
                and normalize_text(str(c.args.get("category", ""))).lower()
                in (dt_lower, dt_lower + "s")
            )
        ]
    if name_contains:
        kw = name_contains.lower()
        filtered = []
        for c in result:
            # Check name, query, and filters for the keyword
            name_val = str(c.args.get("name", "")).lower()
            query_val = str(c.args.get("query", "")).lower()
            filters_str = json.dumps(c.args.get("filters", "")).lower()
            if kw in name_val or kw in query_val or kw in filters_str:
                filtered.append(c)
        result = filtered
    return result


def find_frappe_writes(
    calls: list[ToolCall],
    doctype: str | None = None,
    name_contains: str | None = None,
) -> list[ToolCall]:
    """Find Frappe create/update calls for a doctype."""
    result = [
        c
        for c in calls
        if c.server_name == "frappe-hrms-env"
        and c.method_name in ("frappe_create_resource", "frappe_update_resource")
    ]
    if doctype:
        dt_lower = doctype.lower()
        result = [
            c for c in result if normalize_text(str(c.args.get("doctype", ""))).lower() == dt_lower
        ]
    if name_contains:
        kw = name_contains.lower()
        result = [
            c
            for c in result
            if kw in str(c.args.get("name", "")).lower()
            or kw in json.dumps(c.args.get("payload", {})).lower()
        ]
    return result


def find_frappe_creates(
    calls: list[ToolCall],
    doctype: str | None = None,
    payload_contains: dict | None = None,
) -> list[ToolCall]:
    """Find frappe_create_resource calls with optional filters."""
    result = get_frappe_calls(calls, method="frappe_create_resource", doctype=doctype)
    if payload_contains:
        result = [c for c in result if _payload_matches(c, payload_contains)]
    return result


def find_frappe_update(
    calls: list[ToolCall],
    doctype: str | None = None,
    name_contains: str | None = None,
    payload_contains: dict | None = None,
) -> list[ToolCall]:
    """Find frappe_update_resource calls with optional filters."""
    result = get_frappe_calls(calls, method="frappe_update_resource", doctype=doctype)
    if name_contains:
        kw = name_contains.lower()
        result = [c for c in result if kw in str(c.args.get("name", "")).lower()]
    if payload_contains:
        result = [c for c in result if _payload_matches(c, payload_contains)]
    return result


def find_frappe_deletes(
    calls: list[ToolCall],
    doctype: str | None = None,
) -> list[ToolCall]:
    """Find frappe_delete_resource calls."""
    return get_frappe_calls(calls, method="frappe_delete_resource", doctype=doctype)


def find_frappe_method_calls(
    calls: list[ToolCall],
    method_name: str | None = None,
) -> list[ToolCall]:
    """Find frappe_call_method calls."""
    result = get_frappe_calls(calls, method="frappe_call_method")
    if method_name:
        result = [c for c in result if c.args.get("method") == method_name]
    return result


def find_note_created(
    calls: list[ToolCall],
    content_contains: str | None = None,
) -> list[ToolCall]:
    """Find frappe_create_resource calls creating a Note doctype."""
    result = find_frappe_creates(calls, doctype="Note")
    if content_contains:
        kw = content_contains.lower()
        result = [c for c in result if kw in json.dumps(c.args.get("payload", {})).lower()]
    return result


def find_doctype_discovery(calls: list[ToolCall]) -> list[ToolCall]:
    """Find schema exploration calls (list_doctypes, get_doctype)."""
    return [
        c
        for c in calls
        if c.server_name == "frappe-hrms-env"
        and c.method_name in ("frappe_list_doctypes", "frappe_get_doctype")
    ]


def state_diff_shows_hris_change(
    calls: list[ToolCall],
    keyword: str,
) -> bool:
    """Return True if any Frappe state diff contains keyword."""
    kw = keyword.lower()
    for c in calls:
        if c.server_name == "frappe-hrms-env" and c.state_diff and kw in c.state_diff.lower():
            return True
    return False


def response_contains(call: ToolCall, keyword: str) -> bool:
    """Return True if the tool response content contains keyword."""
    if not call.response:
        return False
    return keyword.lower() in call.response.lower()


# ---------------------------------------------------------------------------
# 5.4  RocketChat helpers
# ---------------------------------------------------------------------------

_RC_URL_DIRECT_RE = re.compile(r"rocketchat[^/]*/direct/([^/?#]+)", re.IGNORECASE)
_RC_URL_CHANNEL_RE = re.compile(r"rocketchat[^/]*/channel/([^/?#]+)", re.IGNORECASE)
_RC_PAGE_URL_RE = re.compile(r"Page URL:\s*(https?://\S+)", re.IGNORECASE)
_RC_MESSAGE_BOX_RE = re.compile(
    r"message\s+(?:box\s+(?:for|to)\s+(?P<pfx1>[#@])?\s*|(?P<pfx2>[#@])\s*)(?P<room>[a-z0-9_.-]+)",
    re.IGNORECASE,
)


def _normalize_rocketchat_room(name: str | None) -> str | None:
    if not name:
        return None
    cleaned = name.strip().lstrip("#@")
    return cleaned or None


def _rocketchat_context_from_url(
    url: str,
) -> tuple[bool, str | None, str | None]:
    """Return (on_rocketchat, recipient, channel_type) inferred from a URL."""
    url_s = (url or "").strip()
    if not url_s:
        return False, None, None

    on_rc = "rocketchat" in url_s.lower()
    if not on_rc:
        return False, None, None

    m = _RC_URL_DIRECT_RE.search(url_s)
    if m:
        return True, _normalize_rocketchat_room(m.group(1)), "direct"
    m = _RC_URL_CHANNEL_RE.search(url_s)
    if m:
        return True, _normalize_rocketchat_room(m.group(1)), "channel"

    return True, None, None


def _rocketchat_context_from_element(
    element: str | None,
) -> tuple[str | None, str | None]:
    """Return (recipient, channel_type) inferred from an element label."""
    if not element:
        return None, None
    m = _RC_MESSAGE_BOX_RE.search(str(element))
    if not m:
        return None, None
    prefix = m.group("pfx1") or m.group("pfx2")
    room = _normalize_rocketchat_room(m.group("room"))
    if not room:
        return None, None
    if prefix == "#":
        return room, "channel"
    return room, "direct"


_RC_SEND_ELEMENT_RE = re.compile(
    r"\bsend\b",
    re.IGNORECASE,
)


def extract_rocketchat_actions(
    calls: list[ToolCall],
) -> list[RocketChatAction]:
    """Extract RocketChat interactions from Playwright tool calls.

    Tracks navigation to rocketchat URLs to determine the current
    recipient, then captures text from browser_type / browser_fill_form
    / browser_run_code as message actions.

    Handles both submit patterns:
    - browser_type(text=..., submit=True)          -- direct submit
    - browser_type(text=..., submit=False) + click Send / Enter
    - browser_fill_form(fields=[...]) + click Send / Enter
    """
    pw_calls = [c for c in calls if c.server_name == "playwright-mcp"]

    actions: list[RocketChatAction] = []
    current_recipient: str | None = None
    current_channel_type: str | None = None
    on_rocketchat = False

    # Pending (typed/filled but not yet submitted) message.
    # Snapshot recipient at buffer time -- subsequent response URLs
    # (from browser_press_key / browser_click) would otherwise clobber
    # it before flush.
    pending_text: str | None = None
    pending_call: ToolCall | None = None
    pending_recipient: str | None = None
    pending_channel_type: str | None = None

    def _flush_pending() -> None:
        """Emit the pending message as a confirmed sent action."""
        nonlocal pending_text, pending_call
        nonlocal pending_recipient, pending_channel_type
        if pending_text and pending_call:
            actions.append(
                RocketChatAction(
                    recipient=pending_recipient,
                    channel_type=pending_channel_type,
                    message_text=pending_text,
                    method_name=pending_call.method_name,
                    call_id=pending_call.call_id,
                    message_index=pending_call.message_index,
                )
            )
        pending_text = None
        pending_call = None
        pending_recipient = None
        pending_channel_type = None

    for c in pw_calls:
        # Prefer explicit page URL evidence from the tool response
        # when present.  Many Playwright actions (click/type/wait)
        # include a "Page URL:" line even when no browser_navigate
        # call occurs.
        if c.response:
            m = _RC_PAGE_URL_RE.search(c.response)
            if m:
                on_rc, recipient, ch_type = _rocketchat_context_from_url(m.group(1))
                if on_rc:
                    on_rocketchat = True
                    current_recipient = recipient
                    current_channel_type = ch_type
                else:
                    on_rocketchat = False
                    pending_text = None
                    pending_call = None
                    pending_recipient = None
                    pending_channel_type = None
                    current_recipient = None
                    current_channel_type = None

        if c.method_name == "browser_navigate":
            url = str(c.args.get("url", ""))
            on_rc, recipient, ch_type = _rocketchat_context_from_url(url)
            if on_rc:
                on_rocketchat = True
                current_recipient = recipient
                current_channel_type = ch_type
            else:
                on_rocketchat = False
                pending_text = None
                pending_call = None
                pending_recipient = None
                pending_channel_type = None
                current_recipient = None
                current_channel_type = None
            continue

        # Some calls (especially browser_type) carry the room in the
        # element label.
        if c.method_name in (
            "browser_type",
            "browser_fill_form",
            "browser_press_key",
            "browser_click",
        ):
            recipient, ch_type = _rocketchat_context_from_element(str(c.args.get("element", "")))
            if recipient:
                on_rocketchat = True
                current_recipient = recipient
                current_channel_type = ch_type

        if not on_rocketchat:
            continue

        if c.method_name == "browser_type":
            text = c.args.get("text", "")
            submit = c.args.get("submit", False)
            if text and submit:
                # Direct submit -- emit immediately (also flushes any
                # earlier pending).
                pending_text = None
                pending_call = None
                actions.append(
                    RocketChatAction(
                        recipient=current_recipient,
                        channel_type=current_channel_type,
                        message_text=text,
                        method_name=c.method_name,
                        call_id=c.call_id,
                        message_index=c.message_index,
                    )
                )
            elif text:
                # submit=False/None -- buffer for a subsequent Send
                # click / Enter.
                pending_text = text
                pending_call = c
                pending_recipient = current_recipient
                pending_channel_type = current_channel_type

        elif c.method_name == "browser_fill_form":
            # Collect all non-empty field values.  The form is
            # considered pending until a Send click or Enter is
            # observed (same as browser_type/submit=False).
            values = [
                fld.get("value", "") for fld in c.args.get("fields", []) if fld.get("value", "")
            ]
            if values:
                pending_text = " ".join(values)
                pending_call = c
                pending_recipient = current_recipient
                pending_channel_type = current_channel_type

        elif c.method_name == "browser_click":
            element = str(c.args.get("element", ""))
            if _RC_SEND_ELEMENT_RE.search(element):
                # Clicking a Send button flushes any pending message.
                _flush_pending()

        elif c.method_name in (
            "browser_run_code",
            "browser_evaluate",
        ):
            code = c.args.get("code", "") or c.args.get("function", "")
            if code and "rocketchat" in code.lower():
                actions.append(
                    RocketChatAction(
                        recipient=current_recipient,
                        channel_type=current_channel_type,
                        message_text=code,
                        method_name=c.method_name,
                        call_id=c.call_id,
                        message_index=c.message_index,
                    )
                )

        elif c.method_name == "browser_press_key":
            key = c.args.get("key", "")
            if key.lower() == "enter":
                if pending_text:
                    # Flush buffered text with the pending call's
                    # metadata.
                    _flush_pending()
                else:
                    # Enter with no buffered text -- record the action
                    # with no text.
                    actions.append(
                        RocketChatAction(
                            recipient=current_recipient,
                            channel_type=current_channel_type,
                            message_text=None,
                            method_name=c.method_name,
                            call_id=c.call_id,
                            message_index=c.message_index,
                        )
                    )

    return actions


def find_chat_message_to(
    actions: list[RocketChatAction],
    recipient: str,
) -> list[RocketChatAction]:
    """Filter actions targeting a specific recipient."""
    r = recipient.lower()
    return [a for a in actions if a.recipient and a.recipient.lower() == r]


def find_chat_message_containing(
    actions: list[RocketChatAction],
    text: str,
) -> list[RocketChatAction]:
    """Filter actions whose message_text contains a substring."""
    kw = text.lower()
    return [a for a in actions if a.message_text and kw in a.message_text.lower()]


def rocketchat_dm_sent(
    actions: list[RocketChatAction],
    recipient: str,
) -> bool:
    """Return True if at least one DM was sent to recipient."""
    return bool(find_chat_message_to(actions, recipient))


def rocketchat_channel_message_sent(
    actions: list[RocketChatAction],
    channel: str,
) -> bool:
    """Return True if at least one message was sent to a named channel."""
    ch = (_normalize_rocketchat_room(channel) or "").lower()
    return any(
        a.recipient and a.recipient.lower() == ch and a.channel_type == "channel" for a in actions
    )


def find_rocketchat_navigations(
    calls: list[ToolCall],
) -> list[ToolCall]:
    """Find browser_navigate calls targeting rocketchat URLs."""
    return [
        c
        for c in calls
        if c.server_name == "playwright-mcp"
        and c.method_name == "browser_navigate"
        and "rocketchat" in str(c.args.get("url", "")).lower()
    ]


def get_all_rocketchat_recipients(
    actions: list[RocketChatAction],
) -> list[str]:
    """Return deduplicated list of all recipients messaged."""
    seen: set[str] = set()
    result: list[str] = []
    for a in actions:
        if a.recipient and a.recipient.lower() not in seen:
            seen.add(a.recipient.lower())
            result.append(a.recipient)
    return result


# --- RocketChat State block parsing ---


def extract_rocketchat_states(calls: list[ToolCall]) -> list[str]:
    """Extract all RocketChat State snapshots from Playwright responses."""
    return [c.rocketchat_state for c in calls if c.rocketchat_state]


def extract_rocketchat_transcripts(
    calls: list[ToolCall],
) -> list[str]:
    """Extract Rocket.Chat transcripts from any supported evidence blocks.

    Verified formats in this repo include:
    - Legacy Playwright observations containing a ``RocketChat State``
      block.
    - Amazon-specific snapshots appended as a ``[STATE DIFF]`` block
      whose body starts with ``RocketChat Messages``
      (see `RLG-556/...` changes).
    """
    transcripts: list[str] = []
    for c in calls:
        if c.rocketchat_state:
            transcripts.append(c.rocketchat_state)
        if c.state_diff and c.state_diff.strip().lower().startswith("rocketchat messages"):
            transcripts.append(c.state_diff)
    return transcripts


def rocketchat_state_has_message_to(
    calls: list[ToolCall],
    recipient: str,
    text_contains: str | None = None,
) -> bool:
    """Check if any RocketChat State snapshot shows a message to recipient."""
    kw_recipient = recipient.lower()
    for state_text in extract_rocketchat_transcripts(calls):
        lower = state_text.lower()
        if kw_recipient in lower:
            if text_contains is None:
                return True
            if text_contains.lower() in lower:
                return True
    return False


def get_latest_rocketchat_state(
    calls: list[ToolCall],
) -> str | None:
    """Return the last RocketChat State snapshot."""
    states = extract_rocketchat_states(calls)
    return states[-1] if states else None


# ---------------------------------------------------------------------------
# 5.5  Email helpers
# ---------------------------------------------------------------------------


def get_email_calls(calls: list[ToolCall]) -> list[ToolCall]:
    """Filter to email-env tool calls."""
    return get_calls_for_server(calls, "email-env")


def find_email_sent(
    calls: list[ToolCall],
    to: str | None = None,
    subject_contains: str | None = None,
    body_contains: str | None = None,
) -> list[ToolCall]:
    """Find send_email calls with optional filters."""
    result = [c for c in calls if c.server_name == "email-env" and c.method_name == "send_email"]
    if to:
        to_lower = to.lower()
        result = [c for c in result if to_lower in _extract_email_recipients(c)]
    if subject_contains:
        kw = subject_contains.lower()
        result = [c for c in result if kw in str(c.args.get("subject", "")).lower()]
    if body_contains:
        kw = body_contains.lower()
        result = [c for c in result if kw in str(c.args.get("body", "")).lower()]
    return result


def find_email_searches(
    calls: list[ToolCall],
    kind: str | None = None,
    query_contains: str | None = None,
) -> list[ToolCall]:
    """Find search_emails calls."""
    result = [c for c in calls if c.server_name == "email-env" and c.method_name == "search_emails"]
    if kind:
        result = [c for c in result if c.args.get("kind") == kind]
    if query_contains:
        kw = query_contains.lower()
        result = [c for c in result if kw in str(c.args.get("query", "")).lower()]
    return result


def find_email_fetches(calls: list[ToolCall]) -> list[ToolCall]:
    """Find get_email calls."""
    return [c for c in calls if c.server_name == "email-env" and c.method_name == "get_email"]


def find_email_deletes(calls: list[ToolCall]) -> list[ToolCall]:
    """Find delete_all_emails calls."""
    return [
        c for c in calls if c.server_name == "email-env" and c.method_name == "delete_all_emails"
    ]


def email_sent_to(calls: list[ToolCall], recipient: str) -> bool:
    """Return True if at least one email was sent to recipient."""
    return bool(find_email_sent(calls, to=recipient))


def email_sent_with_subject(
    calls: list[ToolCall],
    subject_keyword: str,
) -> bool:
    """Return True if at least one email was sent with subject containing keyword."""
    return bool(find_email_sent(calls, subject_contains=subject_keyword))


def get_all_email_recipients(calls: list[ToolCall]) -> list[str]:
    """Return deduplicated list of all email recipients."""
    seen: set[str] = set()
    result: list[str] = []
    for c in find_email_sent(calls):
        for addr in _extract_email_recipients(c):
            if addr not in seen:
                seen.add(addr)
                result.append(addr)
    return result


def email_read_before_send(calls: list[ToolCall]) -> bool:
    """Return True if a search/get email call appears before any send."""
    first_read = None
    first_send = None
    for i, c in enumerate(calls):
        if c.server_name != "email-env":
            continue
        if c.method_name in EMAIL_READ_METHODS and first_read is None:
            first_read = i
        if c.method_name == "send_email" and first_send is None:
            first_send = i
    if first_send is None:
        return True  # No sends, trivially true
    if first_read is None:
        return False
    return first_read < first_send


# ---------------------------------------------------------------------------
# 5.6  Calendar event helpers
# ---------------------------------------------------------------------------


def get_calendar_calls(
    calls: list[ToolCall],
    method: str | None = None,
    account: str | None = None,
) -> list[ToolCall]:
    """Filter to chronos-server calls."""
    result = get_calls_for_server(calls, "chronos-server")
    if method:
        result = [c for c in result if c.method_name == method]
    if account:
        acct = account.lower()
        result = [c for c in result if str(c.args.get("account", "")).lower() == acct]
    return result


def find_calendar_reads(
    calls: list[ToolCall],
    account: str | None = None,
) -> list[ToolCall]:
    """Find get_events_range or search_events calls."""
    result = [
        c
        for c in calls
        if c.server_name == "chronos-server"
        and c.method_name in ("get_events_range", "search_events")
    ]
    if account:
        acct = account.lower()
        result = [c for c in result if str(c.args.get("account", "")).lower() == acct]
    return result


def find_availability_check(
    calls: list[ToolCall],
    account: str,
    date_contains: str | None = None,
) -> list[ToolCall]:
    """Find get_events_range calls for an account."""
    result = get_calendar_calls(calls, method="get_events_range", account=account)
    if date_contains:
        result = [
            c
            for c in result
            if date_contains in str(c.args.get("start_date", ""))
            or date_contains in str(c.args.get("end_date", ""))
        ]
    return result


def find_events_created(
    calls: list[ToolCall],
    account: str | None = None,
    summary_contains: str | None = None,
) -> list[ToolCall]:
    """Find create_event calls."""
    result = get_calendar_calls(calls, method="create_event", account=account)
    if summary_contains:
        kw = summary_contains.lower()
        result = [c for c in result if kw in str(c.args.get("summary", "")).lower()]
    return result


def find_recurring_events_created(
    calls: list[ToolCall],
    account: str | None = None,
    summary_contains: str | None = None,
) -> list[ToolCall]:
    """Find create_recurring_event calls."""
    result = get_calendar_calls(calls, method="create_recurring_event", account=account)
    if summary_contains:
        kw = summary_contains.lower()
        result = [c for c in result if kw in str(c.args.get("summary", "")).lower()]
    return result


def find_events_updated(
    calls: list[ToolCall],
    account: str | None = None,
    event_uid: str | None = None,
) -> list[ToolCall]:
    """Find update_event calls."""
    result = get_calendar_calls(calls, method="update_event", account=account)
    if event_uid:
        result = [c for c in result if c.args.get("event_uid") == event_uid]
    return result


def find_events_deleted(
    calls: list[ToolCall],
    account: str | None = None,
) -> list[ToolCall]:
    """Find delete_event calls."""
    return get_calendar_calls(calls, method="delete_event", account=account)


def find_bulk_events_created(
    calls: list[ToolCall],
    account: str | None = None,
) -> list[ToolCall]:
    """Find bulk_create_events calls."""
    return get_calendar_calls(calls, method="bulk_create_events", account=account)


def total_events_created(
    calls: list[ToolCall],
    account: str | None = None,
) -> int:
    """Count total events across create_event + bulk_create_events."""
    singles = len(find_events_created(calls, account=account))
    bulk_count = 0
    for c in find_bulk_events_created(calls, account=account):
        evts = c.args.get("events", [])
        bulk_count += len(evts) if isinstance(evts, list) else 0
    return singles + bulk_count


def event_has_attendee(call: ToolCall, email: str) -> bool:
    """Return True if a calendar event call includes email in attendees_json."""
    raw = call.args.get("attendees_json", "")
    if not raw:
        return False
    try:
        attendees = json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return email.lower() in str(raw).lower()
    if isinstance(attendees, list):
        return any(
            email.lower() == str(a.get("email", "")).lower()
            for a in attendees
            if isinstance(a, dict)
        )
    return email.lower() in str(raw).lower()


def find_events_with_attendee(
    calls: list[ToolCall],
    email: str,
    account: str | None = None,
) -> list[ToolCall]:
    """Find event creation/update calls that include a specific attendee."""
    candidates = [
        c
        for c in calls
        if c.server_name == "chronos-server"
        and c.method_name
        in (
            "create_event",
            "update_event",
            "create_recurring_event",
        )
    ]
    if account:
        acct = account.lower()
        candidates = [c for c in candidates if str(c.args.get("account", "")).lower() == acct]
    return [c for c in candidates if event_has_attendee(c, email)]


def find_events_with_all_attendees(
    calls: list[ToolCall],
    emails: list[str],
    account: str | None = None,
) -> list[ToolCall]:
    """Find events that include ALL of the specified attendee emails."""
    candidates = find_events_with_attendee(calls, emails[0], account=account) if emails else []
    return [c for c in candidates if all(event_has_attendee(c, e) for e in emails)]


def event_duration_minutes(call: ToolCall) -> int | None:
    """Return duration in minutes for a create/update event call."""
    # create_recurring_event uses duration_minutes directly
    dur = call.args.get("duration_minutes")
    if dur is not None:
        try:
            return int(dur)
        except (ValueError, TypeError):
            pass
    start_str = call.args.get("start")
    end_str = call.args.get("end")
    if not start_str or not end_str:
        return None
    try:
        start = _parse_iso_datetime_utc(str(start_str))
        end = _parse_iso_datetime_utc(str(end_str))
        return int((end - start).total_seconds() / 60)
    except (ValueError, TypeError):
        return None


def find_events_in_window(
    calls: list[ToolCall],
    window_start: str,
    window_end: str,
    account: str | None = None,
) -> list[ToolCall]:
    """Find create event calls whose start falls within a time window."""
    try:
        ws = _parse_iso_datetime_utc(window_start)
        we = _parse_iso_datetime_utc(window_end)
    except ValueError:
        return []

    candidates = [
        c
        for c in calls
        if c.server_name == "chronos-server"
        and c.method_name in ("create_event", "create_recurring_event")
    ]
    if account:
        acct = account.lower()
        candidates = [c for c in candidates if str(c.args.get("account", "")).lower() == acct]

    result = []
    for c in candidates:
        try:
            start = _parse_iso_datetime_utc(str(c.args.get("start", "")))
        except (ValueError, TypeError):
            continue
        if ws <= start <= we:
            result.append(c)
    return result


def find_events_with_duration(
    calls: list[ToolCall],
    min_minutes: int,
    max_minutes: int,
    account: str | None = None,
) -> list[ToolCall]:
    """Find create_event calls whose duration falls within range."""
    candidates = find_events_created(calls, account=account)
    candidates += find_recurring_events_created(calls, account=account)
    result = []
    for c in candidates:
        dur = event_duration_minutes(c)
        if dur is not None and min_minutes <= dur <= max_minutes:
            result.append(c)
    return result


def availability_checked_before_create(
    calls: list[ToolCall],
    account: str,
) -> bool:
    """Return True if get_events_range for account precedes any create_event."""
    first_read = None
    first_write = None
    acct = account.lower()
    for i, c in enumerate(calls):
        if c.server_name != "chronos-server":
            continue
        if str(c.args.get("account", "")).lower() != acct:
            continue
        if c.method_name == "get_events_range" and first_read is None:
            first_read = i
        if (
            c.method_name
            in (
                "create_event",
                "create_recurring_event",
                "bulk_create_events",
            )
            and first_write is None
        ):
            first_write = i
    if first_write is None:
        return True
    if first_read is None:
        return False
    return first_read < first_write


def check_no_double_booking(
    calls: list[ToolCall],
    account: str,
) -> bool:
    """Return True if no two created events for account have overlapping times."""
    acct = account.lower()
    events = [
        c
        for c in calls
        if c.server_name == "chronos-server"
        and c.method_name in ("create_event", "create_recurring_event")
        and str(c.args.get("account", "")).lower() == acct
    ]
    intervals: list[tuple[datetime, datetime]] = []
    for c in events:
        try:
            start = _parse_iso_datetime_utc(str(c.args.get("start", "")))
            end_str = c.args.get("end")
            if end_str:
                end = _parse_iso_datetime_utc(str(end_str))
            else:
                dur = c.args.get("duration_minutes", 60)
                end = start + timedelta(minutes=int(dur))
            intervals.append((start, end))
        except (ValueError, TypeError):
            continue

    for i in range(len(intervals)):
        for j in range(i + 1, len(intervals)):
            s1, e1 = intervals[i]
            s2, e2 = intervals[j]
            if s1 < e2 and s2 < e1:
                return False
    return True


def state_diff_shows_calendar_change(
    calls: list[ToolCall],
) -> bool:
    """Return True if any chronos state diff confirms an event change."""
    return any(c.state_diff for c in calls if c.server_name == "chronos-server")


# ---------------------------------------------------------------------------
# 5.7  Calendar task (VTODO) helpers
# ---------------------------------------------------------------------------


def find_tasks_created(
    calls: list[ToolCall],
    summary_contains: str | None = None,
    account: str | None = None,
) -> list[ToolCall]:
    """Find create_task calls."""
    result = get_calendar_calls(calls, method="create_task", account=account)
    if summary_contains:
        kw = summary_contains.lower()
        result = [c for c in result if kw in str(c.args.get("summary", "")).lower()]
    return result


def find_bulk_tasks_created(
    calls: list[ToolCall],
) -> list[ToolCall]:
    """Find bulk_create_tasks calls."""
    return get_calendar_calls(calls, method="bulk_create_tasks")


def total_tasks_created(calls: list[ToolCall]) -> int:
    """Count total tasks across create_task + bulk_create_tasks."""
    singles = len(find_tasks_created(calls))
    bulk = sum(
        len(c.args.get("tasks", []))
        for c in find_bulk_tasks_created(calls)
        if isinstance(c.args.get("tasks"), list)
    )
    return singles + bulk


# ---------------------------------------------------------------------------
# 5.8  Calendar journal (VJOURNAL) helpers
# ---------------------------------------------------------------------------


def find_journals_created(
    calls: list[ToolCall],
    summary_contains: str | None = None,
    account: str | None = None,
) -> list[ToolCall]:
    """Find create_journal calls."""
    result = get_calendar_calls(calls, method="create_journal", account=account)
    if summary_contains:
        kw = summary_contains.lower()
        result = [c for c in result if kw in str(c.args.get("summary", "")).lower()]
    return result


# ---------------------------------------------------------------------------
# 5.9  Playwright browser helpers
# ---------------------------------------------------------------------------


def get_playwright_calls(
    calls: list[ToolCall],
    method: str | None = None,
) -> list[ToolCall]:
    """Filter to Playwright browser calls."""
    result = get_calls_for_server(calls, "playwright-mcp")
    if method:
        result = [c for c in result if c.method_name == method]
    return result


def find_navigations(
    calls: list[ToolCall],
    url_contains: str | None = None,
) -> list[ToolCall]:
    """Find browser_navigate calls."""
    result = get_playwright_calls(calls, method="browser_navigate")
    if url_contains:
        kw = url_contains.lower()
        result = [c for c in result if kw in str(c.args.get("url", "")).lower()]
    return result


def find_browser_code_runs(
    calls: list[ToolCall],
    code_contains: str | None = None,
) -> list[ToolCall]:
    """Find browser_run_code calls."""
    result = get_playwright_calls(calls, method="browser_run_code")
    if code_contains:
        kw = code_contains.lower()
        result = [c for c in result if kw in str(c.args.get("code", "")).lower()]
    return result


def urls_visited(calls: list[ToolCall]) -> list[str]:
    """Return ordered list of URLs from browser_navigate calls."""
    return [
        str(c.args.get("url", "")) for c in get_playwright_calls(calls, method="browser_navigate")
    ]


def visited_url_matching(calls: list[ToolCall], pattern: str) -> bool:
    """Return True if any browser_navigate URL contains the pattern."""
    kw = pattern.lower()
    return any(kw in url.lower() for url in urls_visited(calls))


# ---------------------------------------------------------------------------
# 5.10  Sequencing helpers
# ---------------------------------------------------------------------------


def was_called_before(
    calls: list[ToolCall],
    first_method: str,
    second_method: str,
) -> bool:
    """Return True if first_method appears before second_method."""
    first_idx = None
    second_idx = None
    for i, c in enumerate(calls):
        if c.method_name == first_method and first_idx is None:
            first_idx = i
        if c.method_name == second_method and second_idx is None:
            second_idx = i
    if second_idx is None:
        return True
    if first_idx is None:
        return False
    return first_idx < second_idx


def read_before_write(
    calls: list[ToolCall],
    doctype: str,
) -> bool:
    """Return True if a Frappe read for doctype precedes any Frappe write."""
    reads = find_frappe_reads(calls, doctype=doctype)
    writes = find_frappe_writes(calls, doctype=doctype)
    if not writes:
        return True
    if not reads:
        return False
    first_read = min(calls.index(c) for c in reads)
    first_write = min(calls.index(c) for c in writes)
    return first_read < first_write


def hris_lookup_before_chat(
    calls: list[ToolCall],
    rocketchat_actions: list[RocketChatAction],
) -> bool:
    """Return True if at least one HRIS read occurred before first chat action."""
    frappe_reads = [
        c
        for c in calls
        if c.server_name == "frappe-hrms-env" and c.method_name in FRAPPE_READ_METHODS
    ]
    if not frappe_reads or not rocketchat_actions:
        return True  # Trivially true if no reads or no chat
    first_read_idx = frappe_reads[0].message_index
    first_chat_idx = rocketchat_actions[0].message_index
    return first_read_idx <= first_chat_idx


def call_a_before_call_b(
    calls: list[ToolCall],
    a_method: str,
    b_method: str,
) -> bool:
    """Return True if any call with a_method appears before any with b_method."""
    return was_called_before(calls, a_method, b_method)


# ---------------------------------------------------------------------------
# 5.11  Negative / scope-discipline helpers
# ---------------------------------------------------------------------------


def count_state_changing_calls(calls: list[ToolCall]) -> int:
    """Count all calls where is_mutating is True."""
    return sum(1 for c in calls if c.is_mutating)


def find_unintended_writes(
    calls: list[ToolCall],
    allowed_doctypes: list[str],
) -> list[ToolCall]:
    """Return Frappe write calls that target doctypes not in the allowed list."""
    allowed_lower = {d.lower() for d in allowed_doctypes}
    return [
        c
        for c in calls
        if c.server_name == "frappe-hrms-env"
        and c.method_name in FRAPPE_WRITE_METHODS
        and c.method_name != "frappe_call_method"
        and normalize_text(str(c.args.get("doctype", ""))).lower() not in allowed_lower
    ]


def find_unintended_email_recipients(
    calls: list[ToolCall],
    allowed_recipients: list[str],
) -> list[ToolCall]:
    """Return send_email calls to recipients not in the allowed list."""
    allowed_lower = {r.lower() for r in allowed_recipients}
    bad = []
    for c in find_email_sent(calls):
        recipients = _extract_email_recipients(c)
        if any(r not in allowed_lower for r in recipients):
            bad.append(c)
    return bad


def find_unintended_chat_recipients(
    actions: list[RocketChatAction],
    allowed_recipients: list[str],
) -> list[RocketChatAction]:
    """Return chat actions targeting recipients not in the allowed list."""
    allowed_lower = {r.lower() for r in allowed_recipients}
    return [a for a in actions if a.recipient and a.recipient.lower() not in allowed_lower]


def find_dangerous_calls(calls: list[ToolCall]) -> list[ToolCall]:
    """Return calls to destructive tools."""
    return [c for c in calls if c.method_name in DANGEROUS_METHODS]


def count_repeated_calls(
    calls: list[ToolCall],
    method: str,
    max_allowed: int = 3,
) -> list[ToolCall]:
    """Return calls where the same method was called more than max_allowed times."""
    method_calls = [c for c in calls if c.method_name == method]
    if len(method_calls) > max_allowed:
        return method_calls
    return []


def find_empty_payload_writes(
    calls: list[ToolCall],
) -> list[ToolCall]:
    """Return Frappe create/update calls with empty or missing payload."""
    return [
        c
        for c in calls
        if c.server_name == "frappe-hrms-env"
        and c.method_name in ("frappe_create_resource", "frappe_update_resource")
        and not c.args.get("payload")
    ]


# ---------------------------------------------------------------------------
# 5.12  Utility
# ---------------------------------------------------------------------------


def args_contain(call: ToolCall, key: str, value: str) -> bool:
    """Return True if call.args[key] contains value (case-insensitive)."""
    return value.lower() in str(call.args.get(key, "")).lower()


def args_equal(call: ToolCall, key: str, value: object) -> bool:
    """Return True if call.args[key] == value."""
    return call.args.get(key) == value


def response_json(call: ToolCall) -> dict | None:
    """Parse tool response content as JSON (before STATE DIFF block)."""
    if not call.response:
        return None
    body, _, _ = _split_response_blocks(call.response)
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        return None


def state_diff_contains(call: ToolCall, keyword: str) -> bool:
    """Return True if the call's state_diff contains keyword."""
    if not call.state_diff:
        return False
    return keyword.lower() in call.state_diff.lower()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _payload_matches(call: ToolCall, expected: dict) -> bool:
    """Return True if call.args['payload'] contains all expected key-value pairs."""
    payload = call.args.get("payload", {})
    if not isinstance(payload, dict):
        return False
    for k, v in expected.items():
        actual = payload.get(k)
        if isinstance(v, str) and isinstance(actual, str):
            if v.lower() != actual.lower():
                return False
        elif actual != v:
            return False
    return True


def _extract_email_recipients(call: ToolCall) -> set[str]:
    """Extract all recipients from a send_email call's args."""
    recipients: set[str] = set()
    for field_name in ("to", "cc", "bcc"):
        val = call.args.get(field_name)
        if isinstance(val, str):
            for part in val.replace(";", ",").split(","):
                clean_part = part.strip()
                if clean_part:
                    recipients.add(clean_part.lower())
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    recipients.add(item.strip().lower())
    return recipients


# ---------------------------------------------------------------------------
# Structured verifier result builder
# ---------------------------------------------------------------------------


def make_verifier_result(
    checks: list[dict[str, Any]],
    error: str | None = None,
) -> VerifierResult:
    """Build a VerifierResult with structured JSON output.

    Args:
        checks: List of check dicts, each with ``name``, ``passed``,
            and ``detail`` keys.
        error: If provided, the result is marked as a failure and the
            error message is included in the JSON output.

    """
    payload: dict[str, Any] = {"checks": checks}
    if error is not None:
        payload["error"] = error
        return VerifierResult(
            success=False,
            message=error,
            output=json.dumps(payload, indent=2),
        )
    checks_failed = [c["detail"] for c in checks if not c["passed"]]
    msg = "; ".join(checks_failed) if checks_failed else "All checks passed"
    return VerifierResult(
        success=not bool(checks_failed),
        message=msg,
        output=json.dumps(payload, indent=2),
    )


# ---------------------------------------------------------------------------
# Helpdesk helpers
# ---------------------------------------------------------------------------


def get_helpdesk_calls(
    calls: list[ToolCall],
    method: str | None = None,
) -> list[ToolCall]:
    """Filter to frappe-helpdesk-env calls, optionally by method."""
    result = [c for c in calls if c.server_name == "frappe-helpdesk-env"]
    if method:
        result = [c for c in result if c.method_name == method]
    return result


def find_helpdesk_reads(
    calls: list[ToolCall],
    ticket_id_contains: str | None = None,
) -> list[ToolCall]:
    """Find helpdesk read calls, optionally matching ticket_id."""
    result = [
        c
        for c in calls
        if c.server_name == "frappe-helpdesk-env" and c.method_name in HELPDESK_READ_METHODS
    ]
    if ticket_id_contains:
        kw = ticket_id_contains.lower()
        result = [
            c
            for c in result
            if kw in str(c.args.get("ticket_id", "")).lower()
            or kw in str(c.args.get("article_id", "")).lower()
            or kw in str(c.args.get("query", "")).lower()
        ]
    return result


def find_helpdesk_writes(
    calls: list[ToolCall],
    ticket_id_contains: str | None = None,
) -> list[ToolCall]:
    """Find helpdesk write calls, optionally matching ticket_id."""
    result = [
        c
        for c in calls
        if c.server_name == "frappe-helpdesk-env" and c.method_name in HELPDESK_WRITE_METHODS
    ]
    if ticket_id_contains:
        kw = ticket_id_contains.lower()
        result = [c for c in result if kw in str(c.args.get("ticket_id", "")).lower()]
    return result


def find_helpdesk_creates(
    calls: list[ToolCall],
    payload_contains: dict | None = None,
) -> list[ToolCall]:
    """Find helpdesk_create_resource calls."""
    result = get_helpdesk_calls(
        calls,
        method="helpdesk_create_resource",
    )
    if payload_contains:
        filtered = []
        for c in result:
            match = True
            for k, v in payload_contains.items():
                actual = c.args.get(k)
                if isinstance(v, str) and isinstance(actual, str):
                    if v.lower() != actual.lower():
                        match = False
                        break
                elif actual != v:
                    match = False
                    break
            if match:
                filtered.append(c)
        result = filtered
    return result


def find_helpdesk_update(
    calls: list[ToolCall],
    ticket_id_contains: str | None = None,
    payload_contains: dict | None = None,
) -> list[ToolCall]:
    """Find helpdesk_update_resource calls with optional filters."""
    result = get_helpdesk_calls(
        calls,
        method="helpdesk_update_resource",
    )
    if ticket_id_contains:
        kw = ticket_id_contains.lower()
        result = [c for c in result if kw in str(c.args.get("ticket_id", "")).lower()]
    if payload_contains:
        filtered = []
        for c in result:
            match = True
            for k, v in payload_contains.items():
                actual = c.args.get(k)
                if isinstance(v, str) and isinstance(actual, str):
                    if v.lower() != actual.lower():
                        match = False
                        break
                elif actual != v:
                    match = False
                    break
            if match:
                filtered.append(c)
        result = filtered
    return result


def find_helpdesk_ticket_search(
    calls: list[ToolCall],
    query_contains: str | None = None,
) -> list[ToolCall]:
    """Find helpdesk_search_documents calls."""
    result = get_helpdesk_calls(
        calls,
        method="helpdesk_search_documents",
    )
    if query_contains:
        kw = query_contains.lower()
        result = [c for c in result if kw in str(c.args.get("query", "")).lower()]
    return result


def find_helpdesk_kb_search(
    calls: list[ToolCall],
    query_contains: str | None = None,
) -> list[ToolCall]:
    """Find helpdesk_search_kb calls."""
    result = get_helpdesk_calls(calls, method="helpdesk_search_kb")
    if query_contains:
        kw = query_contains.lower()
        result = [c for c in result if kw in str(c.args.get("query", "")).lower()]
    return result


def find_helpdesk_assignment(
    calls: list[ToolCall],
    ticket_id_contains: str | None = None,
) -> list[ToolCall]:
    """Find helpdesk_assign_ticket calls."""
    result = get_helpdesk_calls(
        calls,
        method="helpdesk_assign_ticket",
    )
    if ticket_id_contains:
        kw = ticket_id_contains.lower()
        result = [c for c in result if kw in str(c.args.get("ticket_id", "")).lower()]
    return result


def find_helpdesk_email_sent(
    calls: list[ToolCall],
    ticket_id_contains: str | None = None,
) -> list[ToolCall]:
    """Find helpdesk_send_ticket_email calls."""
    result = get_helpdesk_calls(
        calls,
        method="helpdesk_send_ticket_email",
    )
    if ticket_id_contains:
        kw = ticket_id_contains.lower()
        result = [c for c in result if kw in str(c.args.get("ticket_id", "")).lower()]
    return result


def find_helpdesk_ticket_from_chat(
    calls: list[ToolCall],
) -> list[ToolCall]:
    """Find helpdesk_create_ticket_from_chat calls."""
    return get_helpdesk_calls(
        calls,
        method="helpdesk_create_ticket_from_chat",
    )


def state_diff_shows_helpdesk_change(
    calls: list[ToolCall],
    keyword: str,
) -> bool:
    """Return True if any helpdesk state diff contains keyword."""
    kw = keyword.lower()
    for c in calls:
        if c.server_name == "frappe-helpdesk-env" and c.state_diff and kw in c.state_diff.lower():
            return True
    return False


def find_helpdesk_sla_check(
    calls: list[ToolCall],
) -> list[ToolCall]:
    """Find helpdesk_check_sla_status or helpdesk_get_sla calls."""
    return [
        c
        for c in calls
        if c.server_name == "frappe-helpdesk-env"
        and c.method_name in ("helpdesk_check_sla_status", "helpdesk_get_sla")
    ]
