"""
Scenario 1: Cerulean Analytics - Q1 QBR Verifiers
===================================================

Programmatic verifiers for each task in the QBR preparation DAG.
These verifiers run against an agent's action log (a structured record of
every tool call the agent made: Slack messages, emails, calendar invites, etc.)

Usage:
    from verifiers import QBRVerifier
    verifier = QBRVerifier(action_log)
    results = verifier.run_all()

The action_log is expected to be a list of dicts, each representing one tool
action the agent performed. See ActionLog schema below.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


# =============================================================================
# Action Log Schema
# =============================================================================

class ActionType(Enum):
    SLACK_MESSAGE = "slack_message"
    EMAIL = "email"
    CALENDAR_INVITE = "calendar_invite"
    DOCUMENT_CREATE = "document_create"
    DOCUMENT_EDIT = "document_edit"
    DOCUMENT_SHARE = "document_share"
    NOTION_TASK = "notion_task"
    JIRA_TICKET = "jira_ticket"
    FILE_UPLOAD = "file_upload"


@dataclass
class Action:
    """Represents a single agent action from the tool-call log."""
    action_type: ActionType
    timestamp: datetime
    tool: str  # e.g., "slack", "gmail", "google_calendar", "notion"
    recipient: str | None = None  # persona_id or channel name
    channel: str | None = None  # "dm", "channel", or channel name
    subject: str | None = None
    body: str | None = None
    attachments: list[str] = field(default_factory=list)
    attendees: list[str] = field(default_factory=list)
    duration_minutes: int | None = None
    start_time: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class VerifierResult:
    """Result of a single programmatic check."""
    check_id: str
    name: str
    passed: bool
    details: str
    severity: str = "error"  # "error", "warning", "info"


@dataclass
class RubricScore:
    """Result of a rubric evaluation (for LLM-as-judge)."""
    rubric_id: str
    name: str
    dimension: str
    score: int  # 1-5
    justification: str
    evidence: list[str] = field(default_factory=list)


# =============================================================================
# Persona Registry
# =============================================================================

PERSONAS = {
    "rachel_whitford": {
        "timezone": "America/Chicago",
        "working_hours": (7, 30, 18, 30),  # (start_h, start_m, end_h, end_m)
        "preferred_channel": "slack",
        "slack_style": "terse",
    },
    "marcus_tan_ohara": {
        "timezone": "America/Chicago",
        "working_hours": (8, 0, 18, 0),
        "preferred_channel": "email",
        "email_style": "formal",
    },
    "priya_narayanan": {
        "timezone": "America/Los_Angeles",
        "working_hours": (8, 0, 17, 30),
        "preferred_channel": "slack",
        "slack_style": "warm",
    },
    "diego_fuentes_rios": {
        "timezone": "America/New_York",
        "working_hours": (9, 0, 18, 0),
        "preferred_channel": "slack",
        "slack_style": "energetic",
        "hard_boundary_after_hours": True,
    },
    "kenji_watanabe": {
        "timezone": "America/Chicago",
        "working_hours": (8, 30, 17, 30),
        "preferred_channel": "slack",
        "slack_style": "terse",
    },
    "siobhan_omalley": {
        "timezone": "America/Chicago",
        "working_hours": (8, 0, 19, 0),
        "preferred_channel": "slack",
        "slack_style": "narrative",
    },
    "tomas_rezende": {
        "timezone": "America/Chicago",
        "working_hours": (9, 0, 18, 0),
        "preferred_channel": "email",
        "email_style": "structured",
    },
    "lena_strom": {
        "timezone": "America/Chicago",
        "working_hours": (7, 0, 18, 0),
        "preferred_channel": "email",
        "email_style": "brief_directive",
    },
}

# Cross-timezone feasible window for all-hands meetings (CT)
ALL_HANDS_WINDOW_CT = (10, 0, 17, 0)


# =============================================================================
# T1 Verifiers: Pull Revenue & Pipeline Metrics
# =============================================================================

class T1Verifier:
    """Verify: Agent correctly requested revenue data from Kenji."""

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.kenji_messages = [
            a for a in actions
            if a.recipient == "kenji_watanabe"
            and a.action_type == ActionType.SLACK_MESSAGE
        ]

    def check_slack_message_sent(self) -> VerifierResult:
        """T1_PC1: A Slack DM was sent to kenji_watanabe."""
        passed = len(self.kenji_messages) > 0
        return VerifierResult(
            check_id="T1_PC1",
            name="slack_message_sent",
            passed=passed,
            details=(
                f"Found {len(self.kenji_messages)} Slack message(s) to Kenji."
                if passed else "No Slack message sent to kenji_watanabe."
            ),
        )

    def check_correct_channel(self) -> VerifierResult:
        """T1_PC2: Message was sent as DM, not public channel."""
        dm_messages = [m for m in self.kenji_messages if m.channel == "dm"]
        channel_messages = [m for m in self.kenji_messages if m.channel != "dm"]
        passed = len(dm_messages) > 0 and len(channel_messages) == 0
        return VerifierResult(
            check_id="T1_PC2",
            name="correct_channel",
            passed=passed,
            details=(
                "Request sent as DM (correct)."
                if passed else
                f"Found {len(channel_messages)} message(s) in public channels. "
                "Kenji prefers DMs for data requests."
            ),
        )

    def check_data_points_specified(self) -> VerifierResult:
        """T1_PC3: Message includes all required data points."""
        required_keywords = {
            "net_new_arr": [r"net\s*new\s*arr", r"new\s*arr", r"net\s*arr"],
            "pipeline_coverage_ratio": [r"pipeline\s*coverage", r"coverage\s*ratio"],
            "win_rate_by_segment": [r"win\s*rate", r"win/loss"],
            "average_deal_cycle": [r"(deal|sales)\s*cycle", r"cycle\s*length"],
            "top_10_deals": [r"top\s*\d+\s*deals", r"largest\s*deals"],
            "deals_lost_to_acme": [r"(lost|loss).{0,20}acme", r"acme.{0,20}(lost|loss)"],
        }
        combined_body = " ".join(
            (m.body or "").lower() for m in self.kenji_messages
        )
        found = {}
        missing = []
        for key, patterns in required_keywords.items():
            matched = any(re.search(p, combined_body) for p in patterns)
            found[key] = matched
            if not matched:
                missing.append(key)

        passed = len(missing) == 0
        return VerifierResult(
            check_id="T1_PC3",
            name="data_points_specified",
            passed=passed,
            details=(
                "All 6 required data points specified."
                if passed else
                f"Missing data points: {', '.join(missing)}"
            ),
        )

    def check_deadline_included(self) -> VerifierResult:
        """T1_PC4: Message includes a specific deadline."""
        combined_body = " ".join(
            (m.body or "").lower() for m in self.kenji_messages
        )
        # Look for date patterns, "by [day]", "by EOD", specific dates
        deadline_patterns = [
            r"by\s+(monday|tuesday|wednesday|thursday|friday|eod|end\s*of\s*day)",
            r"by\s+\d{1,2}/\d{1,2}",
            r"deadline[:\s]",
            r"need\s*(this\s*)?by",
            r"due\s*(by\s*)?\d",
            r"\d{1,2}(st|nd|rd|th)\b",
        ]
        has_deadline = any(
            re.search(p, combined_body) for p in deadline_patterns
        )
        return VerifierResult(
            check_id="T1_PC4",
            name="deadline_included",
            passed=has_deadline,
            details=(
                "Deadline found in message."
                if has_deadline else
                "No specific deadline found. Avoid 'ASAP' - use a date/time."
            ),
            severity="warning" if not has_deadline else "info",
        )

    def check_response_acknowledged(self) -> VerifierResult:
        """T1_PC5: Agent acknowledged Kenji's response."""
        # Check if there's any action AFTER receiving Kenji's data
        # (e.g., a follow-up message, emoji reaction, or using the data)
        kenji_interactions = [
            a for a in self.actions
            if a.recipient == "kenji_watanabe" or
            a.metadata.get("in_response_to") == "kenji_watanabe"
        ]
        # Simplistic: if there are >1 interactions with Kenji, assume acknowledgment
        passed = len(kenji_interactions) > 1
        return VerifierResult(
            check_id="T1_PC5",
            name="response_acknowledged",
            passed=passed,
            details=(
                "Agent acknowledged Kenji's response."
                if passed else
                "No acknowledgment of Kenji's response detected."
            ),
            severity="warning",
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_slack_message_sent(),
            self.check_correct_channel(),
            self.check_data_points_specified(),
            self.check_deadline_included(),
            self.check_response_acknowledged(),
        ]


# =============================================================================
# T2 Verifiers: Collect Customer Health Scores
# =============================================================================

class T2Verifier:
    """Verify: Agent correctly requested CS data from Priya."""

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.priya_messages = [
            a for a in actions
            if a.recipient == "priya_narayanan"
            and a.action_type == ActionType.SLACK_MESSAGE
        ]

    def check_slack_message_sent(self) -> VerifierResult:
        """T2_PC1: Slack DM sent to priya_narayanan."""
        passed = len(self.priya_messages) > 0
        return VerifierResult(
            check_id="T2_PC1",
            name="slack_message_sent",
            passed=passed,
            details=(
                f"Found {len(self.priya_messages)} message(s) to Priya."
                if passed else "No Slack message sent to priya_narayanan."
            ),
        )

    def check_timezone_respected(self) -> VerifierResult:
        """T2_PC2: Message sent during Priya's working hours (PT)."""
        if not self.priya_messages:
            return VerifierResult(
                check_id="T2_PC2",
                name="timezone_respected",
                passed=False,
                details="No messages to evaluate.",
            )
        # Check if the first message was sent during Priya's hours
        # Priya: 08:00-17:30 PT. We check the UTC offset.
        first_msg = self.priya_messages[0]
        msg_hour = first_msg.timestamp.hour
        # Simplified: assume action timestamps are in PT for this check
        # In production, convert using pytz/zoneinfo
        priya_start = 8
        priya_end = 17  # 17:30 simplified to 17
        passed = priya_start <= msg_hour <= priya_end
        return VerifierResult(
            check_id="T2_PC2",
            name="timezone_respected",
            passed=passed,
            details=(
                f"Message sent at {msg_hour}:00 (within Priya's PT hours)."
                if passed else
                f"Message sent at {msg_hour}:00 - outside Priya's working hours (08:00–17:30 PT)."
            ),
        )

    def check_data_points_requested(self) -> VerifierResult:
        """T2_PC3: All required CS data points requested."""
        required_keywords = {
            "nrr_current_vs_target": [r"nrr", r"net\s*revenue\s*retention"],
            "logo_churn_details": [r"churn", r"logo\s*(churn|loss)"],
            "nps_trend": [r"nps", r"net\s*promoter"],
            "at_risk_accounts_with_reasons": [r"at[\s-]*risk", r"risk\s*account"],
            "top_5_expansion_opportunities": [r"expansion", r"upsell", r"grow"],
        }
        combined_body = " ".join(
            (m.body or "").lower() for m in self.priya_messages
        )
        missing = [
            key for key, patterns in required_keywords.items()
            if not any(re.search(p, combined_body) for p in patterns)
        ]
        passed = len(missing) == 0
        return VerifierResult(
            check_id="T2_PC3",
            name="data_points_requested",
            passed=passed,
            details=(
                "All 5 required data points requested."
                if passed else f"Missing: {', '.join(missing)}"
            ),
        )

    def check_loom_accepted(self) -> VerifierResult:
        """T2_PC4: If Priya sent a Loom, agent accepted it."""
        # Check if Priya responded with a Loom and agent didn't ask for a doc instead
        priya_loom_received = any(
            a.metadata.get("contains_loom_link")
            for a in self.actions
            if a.metadata.get("from") == "priya_narayanan"
        )
        if not priya_loom_received:
            return VerifierResult(
                check_id="T2_PC4",
                name="loom_accepted",
                passed=True,
                details="Priya did not send a Loom (conditional check skipped).",
                severity="info",
            )
        # Check agent didn't ask for a written doc after receiving Loom
        subsequent_msgs = [
            m for m in self.priya_messages
            if m.timestamp > max(
                a.timestamp for a in self.actions
                if a.metadata.get("from") == "priya_narayanan"
                and a.metadata.get("contains_loom_link")
            )
        ]
        asked_for_doc = any(
            re.search(r"(written|document|doc|text|type.{0,10}up)", (m.body or "").lower())
            for m in subsequent_msgs
        )
        return VerifierResult(
            check_id="T2_PC4",
            name="loom_accepted",
            passed=not asked_for_doc,
            details=(
                "Loom accepted without asking for written alternative."
                if not asked_for_doc else
                "Agent asked Priya for a written doc after she sent a Loom - this doesn't match her workflow."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_slack_message_sent(),
            self.check_timezone_respected(),
            self.check_data_points_requested(),
            self.check_loom_accepted(),
        ]


# =============================================================================
# T3 Verifiers: Gather Product Roadmap Highlights
# =============================================================================

class T3Verifier:
    """Verify: Agent correctly requested roadmap from Tomás via email."""

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.tomas_emails = [
            a for a in actions
            if a.recipient == "tomas_rezende"
            and a.action_type == ActionType.EMAIL
        ]
        self.tomas_slacks = [
            a for a in actions
            if a.recipient == "tomas_rezende"
            and a.action_type == ActionType.SLACK_MESSAGE
        ]

    def check_email_sent(self) -> VerifierResult:
        """T3_PC1: Email sent to tomas_rezende."""
        passed = len(self.tomas_emails) > 0
        return VerifierResult(
            check_id="T3_PC1",
            name="email_sent",
            passed=passed,
            details=(
                f"Found {len(self.tomas_emails)} email(s) to Tomás."
                if passed else "No email sent to tomas_rezende."
            ),
        )

    def check_not_slack(self) -> VerifierResult:
        """T3_PC2: No Slack DM sent to Tomás."""
        passed = len(self.tomas_slacks) == 0
        return VerifierResult(
            check_id="T3_PC2",
            name="email_not_slack",
            passed=passed,
            details=(
                "No Slack messages sent to Tomás (correct - he prefers email)."
                if passed else
                f"Found {len(self.tomas_slacks)} Slack message(s) to Tomás. "
                "He prefers email for cross-functional requests."
            ),
        )

    def check_structured_request(self) -> VerifierResult:
        """T3_PC3: Email contains a numbered list."""
        combined_body = " ".join(
            (e.body or "") for e in self.tomas_emails
        )
        # Check for numbered list patterns: "1.", "1)", "#1", etc.
        numbered_pattern = r"(?:^|\n)\s*\d+[\.\)]\s"
        has_numbered_list = bool(re.search(numbered_pattern, combined_body))
        return VerifierResult(
            check_id="T3_PC3",
            name="structured_request",
            passed=has_numbered_list,
            details=(
                "Email contains a structured numbered list (matches Tomás's preference)."
                if has_numbered_list else
                "Email lacks a numbered list - Tomás expects structured, numbered requests."
            ),
        )

    def check_deadline_lead_time(self) -> VerifierResult:
        """T3_PC4: Deadline is at least 48 hours from send time."""
        if not self.tomas_emails:
            return VerifierResult(
                check_id="T3_PC4",
                name="deadline_with_lead_time",
                passed=False,
                details="No email to evaluate.",
            )
        # Extract deadline from email metadata
        email = self.tomas_emails[0]
        deadline = email.metadata.get("deadline")
        if not deadline:
            return VerifierResult(
                check_id="T3_PC4",
                name="deadline_with_lead_time",
                passed=False,
                details="No deadline found in email metadata.",
                severity="warning",
            )
        if isinstance(deadline, str):
            try:
                deadline = datetime.fromisoformat(deadline)
            except ValueError:
                return VerifierResult(
                    check_id="T3_PC4",
                    name="deadline_with_lead_time",
                    passed=False,
                    details=f"Could not parse deadline: {deadline}",
                    severity="warning",
                )
        lead_time = deadline - email.timestamp
        passed = lead_time >= timedelta(hours=48)
        return VerifierResult(
            check_id="T3_PC4",
            name="deadline_with_lead_time",
            passed=passed,
            details=(
                f"Lead time: {lead_time.total_seconds() / 3600:.0f} hours (≥48h required)."
                if passed else
                f"Lead time: {lead_time.total_seconds() / 3600:.0f} hours - "
                "Tomás requires at least 48h notice."
            ),
        )

    def check_no_sales_framing(self) -> VerifierResult:
        """T3_PC5: Email does NOT use sales-trigger phrases."""
        trigger_phrases = [
            r"features?\s*(that\s*)?sales\s*needs?",
            r"sales\s*is\s*(asking|requesting|waiting)",
            r"close\s*(the|a|this)\s*deal",
            r"deal[\s-]critical",
            r"revenue[\s-]blocking",
            r"customer\s*is\s*waiting\s*for",
        ]
        combined_body = " ".join(
            (e.body or "").lower() for e in self.tomas_emails
        )
        found_triggers = [
            p for p in trigger_phrases if re.search(p, combined_body)
        ]
        passed = len(found_triggers) == 0
        return VerifierResult(
            check_id="T3_PC5",
            name="no_sales_framing",
            passed=passed,
            details=(
                "No sales-trigger phrases found (correct - avoids the prioritization tension)."
                if passed else
                "Sales-oriented framing detected. This triggers Tomás's resistance "
                "to 'building features for Sales.'"
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_email_sent(),
            self.check_not_slack(),
            self.check_structured_request(),
            self.check_deadline_lead_time(),
            self.check_no_sales_framing(),
        ]


# =============================================================================
# T4 Verifiers: Compile Competitive Intelligence
# =============================================================================

class T4Verifier:
    """Verify: Agent correctly requested competitive intel from Diego."""

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.diego_messages = [
            a for a in actions
            if a.recipient == "diego_fuentes_rios"
            and a.action_type == ActionType.SLACK_MESSAGE
        ]

    def check_slack_sent(self) -> VerifierResult:
        """T4_PC1: Slack DM sent to Diego."""
        passed = len(self.diego_messages) > 0
        return VerifierResult(
            check_id="T4_PC1",
            name="slack_message_sent",
            passed=passed,
            details=(
                f"Found {len(self.diego_messages)} message(s) to Diego."
                if passed else "No Slack message sent to diego_fuentes_rios."
            ),
        )

    def check_sent_during_hours(self) -> VerifierResult:
        """T4_PC2: Message sent during Diego's hours (09:00-18:00 ET)."""
        if not self.diego_messages:
            return VerifierResult(
                check_id="T4_PC2",
                name="sent_during_hours",
                passed=False,
                details="No messages to evaluate.",
            )
        msg = self.diego_messages[0]
        hour = msg.timestamp.hour
        passed = 9 <= hour < 18
        return VerifierResult(
            check_id="T4_PC2",
            name="sent_during_hours",
            passed=passed,
            details=(
                f"Sent at {hour}:00 ET (within Diego's hours)."
                if passed else
                f"Sent at {hour}:00 ET - Diego disconnects fully after 18:00 ET."
            ),
        )

    def check_acme_mentioned(self) -> VerifierResult:
        """T4_PC3: Request specifically mentions Acme."""
        combined = " ".join((m.body or "").lower() for m in self.diego_messages)
        passed = "acme" in combined
        return VerifierResult(
            check_id="T4_PC3",
            name="acme_mentioned",
            passed=passed,
            details=(
                "Acme specifically mentioned in request."
                if passed else "Request did not mention Acme by name."
            ),
        )

    def check_gong_data_requested(self) -> VerifierResult:
        """T4_PC4: Request includes ask for Gong win rate data."""
        combined = " ".join((m.body or "").lower() for m in self.diego_messages)
        patterns = [r"gong", r"win\s*rate", r"competitive\s*win"]
        passed = any(re.search(p, combined) for p in patterns)
        return VerifierResult(
            check_id="T4_PC4",
            name="gong_data_requested",
            passed=passed,
            details=(
                "Gong/win rate data requested."
                if passed else "No mention of Gong data or competitive win rate."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_slack_sent(),
            self.check_sent_during_hours(),
            self.check_acme_mentioned(),
            self.check_gong_data_requested(),
        ]


# =============================================================================
# T5 Verifiers: Draft QBR Deck
# =============================================================================

class T5Verifier:
    """Verify: Agent correctly compiled the QBR deck."""

    REQUIRED_SECTIONS = [
        "executive_summary",
        "revenue_performance",
        "pipeline_analysis",
        "customer_health",
        "product_roadmap",
        "competitive_landscape",
        "key_wins_losses",
        "q2_plan",
    ]

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.deck_actions = [
            a for a in actions
            if a.action_type in (ActionType.DOCUMENT_CREATE, ActionType.DOCUMENT_EDIT)
            and a.metadata.get("document_type") == "slides"
        ]
        self.share_actions = [
            a for a in actions
            if a.action_type == ActionType.DOCUMENT_SHARE
            or (a.action_type == ActionType.SLACK_MESSAGE
                and a.recipient == "rachel_whitford"
                and a.metadata.get("contains_doc_link"))
        ]

    def check_all_inputs_used(self) -> VerifierResult:
        """T5_PC1: Deck incorporates data from T1, T2, T3, T4."""
        if not self.deck_actions:
            return VerifierResult(
                check_id="T5_PC1",
                name="all_inputs_used",
                passed=False,
                details="No deck creation actions found.",
            )
        deck = self.deck_actions[-1]  # latest version
        sources = deck.metadata.get("data_sources", [])
        required = {"T1", "T2", "T3", "T4"}
        found = required.intersection(set(sources))
        missing = required - found
        passed = len(missing) == 0
        return VerifierResult(
            check_id="T5_PC1",
            name="all_inputs_used",
            passed=passed,
            details=(
                "All 4 data sources incorporated."
                if passed else f"Missing sources: {', '.join(missing)}"
            ),
        )

    def check_required_sections(self) -> VerifierResult:
        """T5_PC2: Deck includes all 8 required sections."""
        if not self.deck_actions:
            return VerifierResult(
                check_id="T5_PC2",
                name="required_sections_present",
                passed=False,
                details="No deck to evaluate.",
            )
        deck = self.deck_actions[-1]
        sections = deck.metadata.get("sections", [])
        missing = [s for s in self.REQUIRED_SECTIONS if s not in sections]
        passed = len(missing) == 0
        return VerifierResult(
            check_id="T5_PC2",
            name="required_sections_present",
            passed=passed,
            details=(
                "All 8 required sections present."
                if passed else f"Missing sections: {', '.join(missing)}"
            ),
        )

    def check_slide_count(self) -> VerifierResult:
        """T5_PC3: Deck does not exceed 25 slides."""
        if not self.deck_actions:
            return VerifierResult(
                check_id="T5_PC3",
                name="slide_count",
                passed=False,
                details="No deck to evaluate.",
            )
        slide_count = self.deck_actions[-1].metadata.get("slide_count", 0)
        passed = slide_count <= 25
        return VerifierResult(
            check_id="T5_PC3",
            name="slide_count",
            passed=passed,
            details=(
                f"Deck has {slide_count} slides (≤25 limit)."
                if passed else
                f"Deck has {slide_count} slides - exceeds 25-slide limit "
                "(Lena is intolerant of long presentations)."
            ),
        )

    def check_shared_with_rachel(self) -> VerifierResult:
        """T5_PC4: Deck shared with Rachel via Slack DM."""
        rachel_shares = [
            a for a in self.share_actions
            if a.recipient == "rachel_whitford"
        ]
        passed = len(rachel_shares) > 0
        return VerifierResult(
            check_id="T5_PC4",
            name="shared_with_rachel",
            passed=passed,
            details=(
                "Draft deck shared with Rachel."
                if passed else "Deck not shared with Rachel via Slack DM."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_all_inputs_used(),
            self.check_required_sections(),
            self.check_slide_count(),
            self.check_shared_with_rachel(),
        ]


# =============================================================================
# T6 Verifiers: Schedule QBR Prep Meeting
# =============================================================================

class T6Verifier:
    """Verify: Agent correctly scheduled the prep meeting."""

    REQUIRED_ATTENDEES = [
        "rachel_whitford",
        "priya_narayanan",
        "kenji_watanabe",
        "diego_fuentes_rios",
    ]

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.calendar_actions = [
            a for a in actions
            if a.action_type == ActionType.CALENDAR_INVITE
            and a.metadata.get("meeting_type") == "prep"
        ]

    def check_attendees(self) -> VerifierResult:
        """T6_PC1: All 4 required attendees are on the invite."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T6_PC1",
                name="all_attendees_included",
                passed=False,
                details="No calendar invite found.",
            )
        invite = self.calendar_actions[0]
        missing = [
            a for a in self.REQUIRED_ATTENDEES
            if a not in invite.attendees
        ]
        passed = len(missing) == 0
        return VerifierResult(
            check_id="T6_PC1",
            name="all_attendees_included",
            passed=passed,
            details=(
                "All 4 attendees included."
                if passed else f"Missing attendees: {', '.join(missing)}"
            ),
        )

    def check_duration(self) -> VerifierResult:
        """T6_PC2: Meeting is exactly 60 minutes."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T6_PC2",
                name="duration_correct",
                passed=False,
                details="No invite to evaluate.",
            )
        duration = self.calendar_actions[0].duration_minutes
        passed = duration == 60
        return VerifierResult(
            check_id="T6_PC2",
            name="duration_correct",
            passed=passed,
            details=(
                "Duration: 60 minutes (correct)."
                if passed else f"Duration: {duration} minutes (expected 60)."
            ),
        )

    def check_timezone_feasible(self) -> VerifierResult:
        """T6_PC3: Meeting within cross-timezone window (10:00-17:00 CT)."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T6_PC3",
                name="timezone_feasible",
                passed=False,
                details="No invite to evaluate.",
            )
        invite = self.calendar_actions[0]
        if not invite.start_time:
            return VerifierResult(
                check_id="T6_PC3",
                name="timezone_feasible",
                passed=False,
                details="No start time on invite.",
            )
        hour = invite.start_time.hour
        passed = ALL_HANDS_WINDOW_CT[0] <= hour < ALL_HANDS_WINDOW_CT[2]
        return VerifierResult(
            check_id="T6_PC3",
            name="timezone_feasible",
            passed=passed,
            details=(
                f"Meeting at {hour}:00 CT (within 10:00–17:00 cross-TZ window)."
                if passed else
                f"Meeting at {hour}:00 CT - outside feasible window for Priya (PT)."
            ),
        )

    def check_agenda_included(self) -> VerifierResult:
        """T6_PC4: Calendar invite body contains an agenda."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T6_PC4",
                name="agenda_included",
                passed=False,
                details="No invite to evaluate.",
            )
        body = (self.calendar_actions[0].body or "").lower()
        agenda_indicators = [r"agenda", r"1\.", r"topics?:", r"discussion\s*items"]
        passed = any(re.search(p, body) for p in agenda_indicators)
        return VerifierResult(
            check_id="T6_PC4",
            name="agenda_included",
            passed=passed,
            details=(
                "Agenda found in invite body."
                if passed else "No agenda detected in calendar invite."
            ),
        )

    def check_timing_before_qbr(self) -> VerifierResult:
        """T6_PC5: Meeting is at least 3 business days before QBR."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T6_PC5",
                name="three_days_before_qbr",
                passed=False,
                details="No invite to evaluate.",
            )
        invite = self.calendar_actions[0]
        qbr_date = invite.metadata.get("qbr_date")
        if not qbr_date or not invite.start_time:
            return VerifierResult(
                check_id="T6_PC5",
                name="three_days_before_qbr",
                passed=False,
                details="QBR date or meeting date not available for comparison.",
                severity="warning",
            )
        if isinstance(qbr_date, str):
            qbr_date = datetime.fromisoformat(qbr_date)
        days_before = (qbr_date - invite.start_time).days
        passed = days_before >= 3
        return VerifierResult(
            check_id="T6_PC5",
            name="three_days_before_qbr",
            passed=passed,
            details=(
                f"Prep meeting is {days_before} days before QBR (≥3 required)."
                if passed else
                f"Only {days_before} day(s) before QBR - need at least 3 business days."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_attendees(),
            self.check_duration(),
            self.check_timezone_feasible(),
            self.check_agenda_included(),
            self.check_timing_before_qbr(),
        ]


# =============================================================================
# T7-T12 Verifiers (abbreviated - same pattern)
# =============================================================================

class T7Verifier:
    """Verify: Pre-read materials circulated correctly."""

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.preread_emails = [
            a for a in actions
            if a.action_type == ActionType.EMAIL
            and a.metadata.get("purpose") == "pre_read"
        ]

    def check_email_sent(self) -> VerifierResult:
        """T7_PC1: Email sent to all 4 prep attendees."""
        recipients = set()
        for email in self.preread_emails:
            if email.recipient:
                recipients.add(email.recipient)
            recipients.update(email.metadata.get("cc", []))
            recipients.update(email.metadata.get("to", []))
        required = {"rachel_whitford", "priya_narayanan", "kenji_watanabe", "diego_fuentes_rios"}
        missing = required - recipients
        passed = len(missing) == 0
        return VerifierResult(
            check_id="T7_PC1",
            name="email_sent",
            passed=passed,
            details=(
                "Pre-read email sent to all 4 attendees."
                if passed else f"Missing recipients: {', '.join(missing)}"
            ),
        )

    def check_timing(self) -> VerifierResult:
        """T7_PC2: Sent at least 48 hours before meeting."""
        if not self.preread_emails:
            return VerifierResult(
                check_id="T7_PC2",
                name="timing_correct",
                passed=False,
                details="No pre-read email found.",
            )
        email = self.preread_emails[0]
        meeting_time = email.metadata.get("meeting_time")
        if not meeting_time:
            return VerifierResult(
                check_id="T7_PC2",
                name="timing_correct",
                passed=False,
                details="Meeting time not available.",
                severity="warning",
            )
        if isinstance(meeting_time, str):
            meeting_time = datetime.fromisoformat(meeting_time)
        lead = meeting_time - email.timestamp
        passed = lead >= timedelta(hours=48)
        return VerifierResult(
            check_id="T7_PC2",
            name="timing_correct",
            passed=passed,
            details=f"Pre-read sent {lead.total_seconds() / 3600:.0f}h before meeting (48h required).",
        )

    def check_deck_link(self) -> VerifierResult:
        """T7_PC3: Email contains deck link."""
        has_link = any(
            e.metadata.get("contains_doc_link") or
            re.search(r"https?://", e.body or "")
            for e in self.preread_emails
        )
        return VerifierResult(
            check_id="T7_PC3",
            name="deck_link_included",
            passed=has_link,
            details="Deck link found." if has_link else "No deck link in email.",
        )

    def check_no_extra_recipients(self) -> VerifierResult:
        """T7_PC4: Email NOT sent to Lena, Tomás, Marcus, or Siobhán."""
        excluded = {"lena_strom", "tomas_rezende", "marcus_tan_ohara", "siobhan_omalley"}
        all_recipients = set()
        for email in self.preread_emails:
            if email.recipient:
                all_recipients.add(email.recipient)
            all_recipients.update(email.metadata.get("cc", []))
            all_recipients.update(email.metadata.get("to", []))
        leaked = excluded.intersection(all_recipients)
        passed = len(leaked) == 0
        return VerifierResult(
            check_id="T7_PC4",
            name="no_extra_recipients",
            passed=passed,
            details=(
                "Pre-read correctly scoped to prep attendees only."
                if passed else
                f"Pre-read sent to non-prep attendees: {', '.join(leaked)}. "
                "This is a working session pre-read, not final distribution."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_email_sent(),
            self.check_timing(),
            self.check_deck_link(),
            self.check_no_extra_recipients(),
        ]


class T8Verifier:
    """Verify: Prep meeting follow-up distributed correctly."""

    def __init__(self, actions: list[Action]):
        self.actions = actions

    def check_slack_summary(self) -> VerifierResult:
        """T8_PC1: Summary posted in Slack within 2 hours."""
        summaries = [
            a for a in self.actions
            if a.action_type == ActionType.SLACK_MESSAGE
            and a.metadata.get("purpose") == "meeting_summary"
        ]
        passed = len(summaries) > 0
        return VerifierResult(
            check_id="T8_PC1",
            name="slack_summary_posted",
            passed=passed,
            details="Meeting summary posted." if passed else "No summary posted.",
        )

    def check_action_items_owners(self) -> VerifierResult:
        """T8_PC2: Every action item has an owner."""
        action_items = [
            a for a in self.actions
            if a.metadata.get("is_action_item")
        ]
        if not action_items:
            return VerifierResult(
                check_id="T8_PC2",
                name="action_items_have_owners",
                passed=False,
                details="No action items found.",
            )
        without_owner = [a for a in action_items if not a.metadata.get("owner")]
        passed = len(without_owner) == 0
        return VerifierResult(
            check_id="T8_PC2",
            name="action_items_have_owners",
            passed=passed,
            details=(
                f"All {len(action_items)} action items have owners."
                if passed else
                f"{len(without_owner)}/{len(action_items)} items lack owners."
            ),
        )

    def check_action_items_deadlines(self) -> VerifierResult:
        """T8_PC3: Every action item has a deadline."""
        action_items = [
            a for a in self.actions
            if a.metadata.get("is_action_item")
        ]
        if not action_items:
            return VerifierResult(
                check_id="T8_PC3",
                name="action_items_have_deadlines",
                passed=False,
                details="No action items found.",
            )
        without_deadline = [a for a in action_items if not a.metadata.get("deadline")]
        passed = len(without_deadline) == 0
        return VerifierResult(
            check_id="T8_PC3",
            name="action_items_have_deadlines",
            passed=passed,
            details=(
                f"All {len(action_items)} items have deadlines."
                if passed else
                f"{len(without_deadline)}/{len(action_items)} items lack deadlines."
            ),
        )

    def check_priya_followup(self) -> VerifierResult:
        """T8_PC4: Follow-up DM sent to Priya for additional thoughts."""
        priya_followups = [
            a for a in self.actions
            if a.recipient == "priya_narayanan"
            and a.action_type == ActionType.SLACK_MESSAGE
            and a.metadata.get("purpose") in ("followup", "feedback_request")
        ]
        passed = len(priya_followups) > 0
        return VerifierResult(
            check_id="T8_PC4",
            name="priya_followup_dm",
            passed=passed,
            details=(
                "Follow-up DM sent to Priya (good - she's conflict-avoidant in groups)."
                if passed else
                "No follow-up sent to Priya. She may have additional feedback "
                "she didn't share in the group meeting."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_slack_summary(),
            self.check_action_items_owners(),
            self.check_action_items_deadlines(),
            self.check_priya_followup(),
        ]


class T9Verifier:
    """Verify: Final deck approved by Rachel."""

    def __init__(self, actions: list[Action]):
        self.actions = actions

    def check_rachel_approved(self) -> VerifierResult:
        """T9_PC2: Rachel explicitly approved."""
        approval_indicators = [
            a for a in self.actions
            if a.metadata.get("from") == "rachel_whitford"
            and a.metadata.get("is_approval")
        ]
        passed = len(approval_indicators) > 0
        return VerifierResult(
            check_id="T9_PC2",
            name="rachel_approved",
            passed=passed,
            details=(
                "Rachel's explicit approval received."
                if passed else
                "No explicit approval from Rachel. "
                "A 👍 or 'looks good' counts. No response does NOT count."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [self.check_rachel_approved()]


class T10Verifier:
    """Verify: QBR invite sent correctly."""

    REQUIRED_ATTENDEES = [
        "rachel_whitford", "lena_strom", "marcus_tan_ohara",
        "priya_narayanan", "diego_fuentes_rios", "kenji_watanabe",
        "siobhan_omalley",
    ]

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.qbr_invites = [
            a for a in actions
            if a.action_type == ActionType.CALENDAR_INVITE
            and a.metadata.get("meeting_type") == "qbr"
        ]

    def check_attendees(self) -> VerifierResult:
        """T10_PC1: All 7 required attendees."""
        if not self.qbr_invites:
            return VerifierResult(
                check_id="T10_PC1",
                name="all_attendees",
                passed=False,
                details="No QBR invite found.",
            )
        missing = [
            a for a in self.REQUIRED_ATTENDEES
            if a not in self.qbr_invites[0].attendees
        ]
        passed = len(missing) == 0
        return VerifierResult(
            check_id="T10_PC1",
            name="all_attendees",
            passed=passed,
            details=(
                "All 7 attendees included."
                if passed else f"Missing: {', '.join(missing)}"
            ),
        )

    def check_duration(self) -> VerifierResult:
        """T10_PC2: 90-minute meeting."""
        if not self.qbr_invites:
            return VerifierResult(
                check_id="T10_PC2",
                name="duration",
                passed=False,
                details="No invite.",
            )
        passed = self.qbr_invites[0].duration_minutes == 90
        return VerifierResult(
            check_id="T10_PC2",
            name="duration",
            passed=passed,
            details=f"Duration: {self.qbr_invites[0].duration_minutes}min (90 required).",
        )

    def check_conclusion_first_agenda(self) -> VerifierResult:
        """T10_PC5: Agenda starts with executive summary."""
        if not self.qbr_invites:
            return VerifierResult(
                check_id="T10_PC5",
                name="conclusion_first_agenda",
                passed=False,
                details="No invite.",
            )
        body = (self.qbr_invites[0].body or "").lower()
        # Check that "executive summary" or "conclusion" appears before other sections
        exec_pos = body.find("executive summary")
        if exec_pos == -1:
            exec_pos = body.find("bottom line")
        if exec_pos == -1:
            exec_pos = body.find("key findings")
        other_sections = ["pipeline", "customer health", "competitive", "roadmap"]
        first_other = min(
            (body.find(s) for s in other_sections if body.find(s) != -1),
            default=len(body)
        )
        passed = exec_pos != -1 and exec_pos < first_other
        return VerifierResult(
            check_id="T10_PC5",
            name="conclusion_first_agenda",
            passed=passed,
            details=(
                "Agenda leads with executive summary (Lena's 'start with the conclusion')."
                if passed else
                "Agenda does not lead with executive summary/conclusion."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_attendees(),
            self.check_duration(),
            self.check_conclusion_first_agenda(),
        ]


class T11Verifier:
    """Verify: Executive pre-brief sent to Lena."""

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.lena_emails = [
            a for a in actions
            if a.recipient == "lena_strom"
            and a.action_type == ActionType.EMAIL
            and a.metadata.get("purpose") == "pre_brief"
        ]

    def check_email_sent(self) -> VerifierResult:
        """T11_PC1: Email sent to Lena."""
        passed = len(self.lena_emails) > 0
        return VerifierResult(
            check_id="T11_PC1",
            name="email_sent",
            passed=passed,
            details="Pre-brief email sent to Lena." if passed else "No pre-brief email.",
        )

    def check_timing(self) -> VerifierResult:
        """T11_PC2: Sent ~24h before QBR (±4h tolerance)."""
        if not self.lena_emails:
            return VerifierResult(
                check_id="T11_PC2",
                name="timing",
                passed=False,
                details="No email to evaluate.",
            )
        email = self.lena_emails[0]
        qbr_time = email.metadata.get("qbr_time")
        if not qbr_time:
            return VerifierResult(
                check_id="T11_PC2",
                name="timing",
                passed=False,
                details="QBR time not available.",
                severity="warning",
            )
        if isinstance(qbr_time, str):
            qbr_time = datetime.fromisoformat(qbr_time)
        hours_before = (qbr_time - email.timestamp).total_seconds() / 3600
        passed = 20 <= hours_before <= 28  # 24h ± 4h
        return VerifierResult(
            check_id="T11_PC2",
            name="timing",
            passed=passed,
            details=f"Sent {hours_before:.0f}h before QBR (target: 24h ± 4h).",
        )

    def check_not_slack(self) -> VerifierResult:
        """T11_PC3: Sent via email, not Slack."""
        lena_slacks = [
            a for a in self.actions
            if a.recipient == "lena_strom"
            and a.action_type == ActionType.SLACK_MESSAGE
            and a.metadata.get("purpose") == "pre_brief"
        ]
        passed = len(lena_slacks) == 0
        return VerifierResult(
            check_id="T11_PC3",
            name="not_slack",
            passed=passed,
            details=(
                "Pre-brief sent via email (correct)."
                if passed else
                "Pre-brief sent via Slack - Lena doesn't engage with long Slack messages."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_email_sent(),
            self.check_timing(),
            self.check_not_slack(),
        ]


class T12Verifier:
    """Verify: Post-QBR action items distributed."""

    def __init__(self, actions: list[Action]):
        self.actions = actions

    def check_email_sent(self) -> VerifierResult:
        """T12_PC1: Email sent within 4 hours."""
        action_emails = [
            a for a in self.actions
            if a.action_type == ActionType.EMAIL
            and a.metadata.get("purpose") == "post_qbr_actions"
        ]
        passed = len(action_emails) > 0
        return VerifierResult(
            check_id="T12_PC1",
            name="email_sent",
            passed=passed,
            details="Action items email sent." if passed else "No post-QBR email.",
        )

    def check_notion_tasks(self) -> VerifierResult:
        """T12_PC3: Notion tasks created."""
        notion_actions = [
            a for a in self.actions
            if a.action_type == ActionType.NOTION_TASK
        ]
        passed = len(notion_actions) > 0
        return VerifierResult(
            check_id="T12_PC3",
            name="notion_tasks_created",
            passed=passed,
            details=(
                f"{len(notion_actions)} Notion task(s) created."
                if passed else "No Notion tasks created."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_email_sent(),
            self.check_notion_tasks(),
        ]


# =============================================================================
# DAG Dependency Verifier
# =============================================================================

class DAGVerifier:
    """Verify that tasks were executed in correct dependency order."""

    DEPENDENCIES = {
        "T1": [],
        "T2": [],
        "T3": [],
        "T4": [],
        "T5": ["T1", "T2", "T3", "T4"],
        "T6": [],
        "T7": ["T5", "T6"],
        "T8": ["T7"],
        "T9": ["T8"],
        "T10": ["T9"],
        "T11": ["T9"],
        "T12": ["T10"],
    }

    def __init__(self, task_completion_times: dict[str, datetime]):
        """
        Args:
            task_completion_times: mapping of task_id -> completion timestamp
        """
        self.completion_times = task_completion_times

    def check_all_dependencies(self) -> list[VerifierResult]:
        results = []
        for task, deps in self.DEPENDENCIES.items():
            if task not in self.completion_times:
                continue
            task_start = self.completion_times[task]
            violations = []
            for dep in deps:
                if dep not in self.completion_times:
                    violations.append(f"{dep} (not completed)")
                elif self.completion_times[dep] > task_start:
                    violations.append(
                        f"{dep} (completed after {task} started)"
                    )
            passed = len(violations) == 0
            results.append(VerifierResult(
                check_id=f"DAG_{task}",
                name=f"dag_dependency_{task.lower()}",
                passed=passed,
                details=(
                    f"{task}: All dependencies satisfied."
                    if passed else
                    f"{task}: Dependency violations: {', '.join(violations)}"
                ),
            ))
        return results


# =============================================================================
# Rubric Evaluator (LLM-as-Judge scaffolding)
# =============================================================================

class RubricEvaluator:
    """
    Scaffolding for LLM-as-judge rubric evaluation.

    In production, each evaluate_* method would call an LLM with the rubric
    criteria, the agent's action log, and the persona context, asking it to
    score 1-5 with justification.
    """

    def __init__(self, actions: list[Action]):
        self.actions = actions

    def _get_messages_to(self, persona_id: str) -> list[Action]:
        return [
            a for a in self.actions
            if a.recipient == persona_id
        ]

    def evaluate_communication_style_match(
        self,
        persona_id: str,
        expected_style: str,
    ) -> RubricScore:
        """
        Evaluate whether the agent's communication matched the persona's
        preferred style.

        In production, this would invoke an LLM judge with:
        - The persona's communication profile
        - The agent's actual messages
        - The rubric scoring criteria
        """
        messages = self._get_messages_to(persona_id)
        message_texts = [m.body or "" for m in messages]

        # Placeholder: return a score structure for the LLM judge to fill
        return RubricScore(
            rubric_id=f"style_{persona_id}",
            name=f"communication_style_match_{persona_id}",
            dimension="Persona Fidelity",
            score=0,  # To be filled by LLM judge
            justification="[LLM judge evaluation pending]",
            evidence=message_texts[:3],  # First 3 messages as evidence
        )

    def evaluate_political_navigation(self) -> RubricScore:
        """
        Evaluate how well the agent navigated organizational politics.

        Key tensions to check:
        - Rachel/Tomás: feature prioritization
        - Priya/Lena: retention vs. expansion
        - Rachel/Marcus: discount authority
        - Rachel's Q4 blame: product vs. pricing
        """
        # Collect all cross-functional interactions
        tomas_messages = self._get_messages_to("tomas_rezende")
        priya_messages = self._get_messages_to("priya_narayanan")

        return RubricScore(
            rubric_id="G_R4",
            name="political_navigation",
            dimension="Organizational Awareness",
            score=0,  # LLM judge
            justification="[LLM judge evaluation pending]",
            evidence=[
                f"Tomás messages: {len(tomas_messages)}",
                f"Priya messages: {len(priya_messages)}",
            ],
        )

    def build_judge_prompt(
        self,
        rubric_id: str,
        rubric_text: str,
        evidence: list[str],
    ) -> str:
        """
        Build a prompt for an LLM judge to evaluate a rubric criterion.

        Returns a formatted prompt string that can be sent to an evaluation LLM.
        """
        return f"""You are evaluating an AI agent's performance on a workplace task.

## Rubric Criterion
ID: {rubric_id}
{rubric_text}

## Evidence (Agent's Actions)
{chr(10).join(f"- {e}" for e in evidence)}

## Instructions
Score the agent's performance on a scale of 1-5 based on the rubric above.
Provide:
1. Score (1-5)
2. Justification (2-3 sentences explaining why this score)
3. Specific evidence from the actions that supports your score

Respond in JSON format:
{{"score": <int>, "justification": "<string>", "key_evidence": ["<string>", ...]}}
"""


# =============================================================================
# Master Verifier
# =============================================================================

class QBRVerifier:
    """
    Master verifier that runs all programmatic checks and prepares rubric
    evaluations for the QBR scenario.
    """

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.task_verifiers = {
            "T1": T1Verifier(actions),
            "T2": T2Verifier(actions),
            "T3": T3Verifier(actions),
            "T4": T4Verifier(actions),
            "T5": T5Verifier(actions),
            "T6": T6Verifier(actions),
            "T7": T7Verifier(actions),
            "T8": T8Verifier(actions),
            "T9": T9Verifier(actions),
            "T10": T10Verifier(actions),
            "T11": T11Verifier(actions),
            "T12": T12Verifier(actions),
        }
        self.rubric_evaluator = RubricEvaluator(actions)

    def run_programmatic_checks(self) -> dict[str, list[VerifierResult]]:
        """Run all programmatic verifiers for all tasks."""
        results = {}
        for task_id, verifier in self.task_verifiers.items():
            results[task_id] = verifier.run_all()
        return results

    def run_dag_checks(
        self, completion_times: dict[str, datetime]
    ) -> list[VerifierResult]:
        """Verify DAG execution order."""
        dag = DAGVerifier(completion_times)
        return dag.check_all_dependencies()

    def run_all(
        self,
        completion_times: dict[str, datetime] | None = None,
    ) -> dict[str, Any]:
        """Run all checks and return a full results dict."""
        programmatic = self.run_programmatic_checks()
        dag = (
            self.run_dag_checks(completion_times)
            if completion_times else []
        )

        # Aggregate pass/fail stats
        all_checks = []
        for task_results in programmatic.values():
            all_checks.extend(task_results)
        all_checks.extend(dag)

        total = len(all_checks)
        passed = sum(1 for c in all_checks if c.passed)
        failed = total - passed

        return {
            "summary": {
                "total_checks": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": f"{passed / total * 100:.1f}%" if total > 0 else "N/A",
            },
            "programmatic_results": {
                task_id: [
                    {
                        "check_id": r.check_id,
                        "name": r.name,
                        "passed": r.passed,
                        "details": r.details,
                        "severity": r.severity,
                    }
                    for r in results
                ]
                for task_id, results in programmatic.items()
            },
            "dag_results": [
                {
                    "check_id": r.check_id,
                    "name": r.name,
                    "passed": r.passed,
                    "details": r.details,
                }
                for r in dag
            ],
        }
