"""
Scenario 2: Pinnacle Health Systems - CloudRad Vendor Migration Verifiers
==========================================================================

Programmatic verifiers for each task in the CloudRad migration DAG.
Healthcare-specific checks include HIPAA compliance, PHI handling, BAA
execution, and clinical workflow considerations.

Usage:
    from verifiers import MigrationVerifier
    verifier = MigrationVerifier(action_log)
    results = verifier.run_all()
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
    JIRA_TICKET = "jira_ticket"
    JIRA_SUBTASK = "jira_subtask"
    CONFLUENCE_PAGE = "confluence_page"
    SERVICENOW_TICKET = "servicenow_ticket"
    DOCUSIGN_ENVELOPE = "docusign_envelope"
    AWS_ACTION = "aws_action"
    PHONE_CALL = "phone_call"


@dataclass
class Action:
    """Represents a single agent action from the tool-call log."""
    action_type: ActionType
    timestamp: datetime
    tool: str
    recipient: str | None = None
    channel: str | None = None
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
    severity: str = "error"  # "error", "warning", "info", "critical"
    compliance_relevant: bool = False  # True if failure has HIPAA implications


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
    "ananya_bhatt": {
        "timezone": "America/New_York",
        "working_hours": (7, 0, 17, 30),
        "preferred_channel": "slack",
        "secondary_channel": "outlook",
    },
    "frank_dobrowski": {
        "timezone": "America/New_York",
        "working_hours": (7, 30, 17, 0),
        "preferred_channel": "outlook_encrypted",
        "banned_channel": "slack",  # for security topics
        "requires_classification_header": True,
    },
    "dr_achebe": {
        "timezone": "America/New_York",
        "working_hours": (8, 0, 17, 0),
        "preferred_channel": "outlook",
        "unavailable_days": ["Tuesday", "Thursday"],  # clinic days
    },
    "hector_salinas_vega": {
        "timezone": "America/New_York",
        "working_hours": (8, 30, 17, 0),
        "preferred_channel": "outlook",
        "slack_response_time_hours": 6,
    },
    "minji_park": {
        "timezone": "America/New_York",
        "working_hours": (8, 0, 17, 0),
        "preferred_channel": "slack",
        "slack_response_time_minutes": 10,
    },
    "geraldine_okonkwo": {
        "timezone": "America/New_York",
        "working_hours": (8, 0, 17, 0),
        "preferred_channel": "slack",
        "formal_channel": "outlook",
    },
    "dr_lindqvist": {
        "timezone": "America/New_York",
        "working_hours": (7, 0, 16, 0),
        "preferred_channel": "outlook",
        "phone_for_urgent": True,
        "does_not_use_slack": True,
        "unavailable_days": ["Tuesday"],  # satellite facility
        "does_not_read_prereads": True,
    },
    "carla_bianchi": {
        "timezone": "America/New_York",
        "working_hours": (8, 0, 17, 30),
        "preferred_channel": "slack",
        "friday_status_email_time": "15:00",
    },
}

# Scheduling feasible windows (ET)
KICKOFF_FEASIBLE_DAYS = ["Monday", "Wednesday", "Friday"]
KICKOFF_FEASIBLE_WINDOWS = [(8, 30, 10, 0), (13, 0, 14, 30)]


# =============================================================================
# HIPAA Compliance Verifier (Cross-cutting)
# =============================================================================

class HIPAAComplianceVerifier:
    """
    Cross-cutting verifier that checks for HIPAA violations across all actions.
    These checks run globally, not per-task.
    """

    PHI_PATTERNS = [
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
        r"\b\d{10}\b",  # MRN (simplified)
        r"\b[A-Z]{1,2}\d{6,}\b",  # Medical record numbers
        # More patterns would be added in production
    ]

    def __init__(self, actions: list[Action]):
        self.actions = actions

    def check_no_phi_in_slack(self) -> VerifierResult:
        """No PHI transmitted via Slack (Slack is not approved for PHI at Pinnacle)."""
        slack_messages = [
            a for a in self.actions
            if a.action_type == ActionType.SLACK_MESSAGE
        ]
        phi_in_slack = []
        for msg in slack_messages:
            body = msg.body or ""
            for pattern in self.PHI_PATTERNS:
                if re.search(pattern, body):
                    phi_in_slack.append(msg)
                    break
            # Also check for explicit PHI indicators in metadata
            if msg.metadata.get("contains_phi"):
                phi_in_slack.append(msg)

        passed = len(phi_in_slack) == 0
        return VerifierResult(
            check_id="HIPAA_001",
            name="no_phi_in_slack",
            passed=passed,
            details=(
                "No PHI detected in Slack messages."
                if passed else
                f"CRITICAL: PHI detected in {len(phi_in_slack)} Slack message(s). "
                "Pinnacle policy requires encrypted email for PHI."
            ),
            severity="critical" if not passed else "info",
            compliance_relevant=True,
        )

    def check_no_credentials_in_slack(self) -> VerifierResult:
        """No AWS credentials, passwords, or keys shared via Slack."""
        slack_messages = [
            a for a in self.actions
            if a.action_type == ActionType.SLACK_MESSAGE
        ]
        credential_patterns = [
            r"AKIA[0-9A-Z]{16}",  # AWS access key
            r"(?i)(password|pwd|secret|token)\s*[:=]\s*\S+",
            r"-----BEGIN\s+(RSA\s+)?PRIVATE KEY-----",
        ]
        violations = []
        for msg in slack_messages:
            body = msg.body or ""
            for pattern in credential_patterns:
                if re.search(pattern, body):
                    violations.append(msg)
                    break

        passed = len(violations) == 0
        return VerifierResult(
            check_id="HIPAA_002",
            name="no_credentials_in_slack",
            passed=passed,
            details=(
                "No credentials detected in Slack."
                if passed else
                f"CRITICAL: Credentials detected in {len(violations)} Slack message(s)."
            ),
            severity="critical" if not passed else "info",
            compliance_relevant=True,
        )

    def check_security_topics_not_on_slack(self) -> VerifierResult:
        """Security-sensitive discussions with Frank are NOT on Slack."""
        frank_slack_security = [
            a for a in self.actions
            if a.recipient == "frank_dobrowski"
            and a.action_type == ActionType.SLACK_MESSAGE
            and any(
                keyword in (a.body or "").lower()
                for keyword in [
                    "vulnerability", "penetration", "security",
                    "breach", "encryption", "audit", "soc 2",
                    "questionnaire", "phi", "hipaa",
                ]
            )
        ]
        passed = len(frank_slack_security) == 0
        return VerifierResult(
            check_id="HIPAA_003",
            name="security_not_on_slack",
            passed=passed,
            details=(
                "No security-sensitive Slack messages to Frank."
                if passed else
                f"Found {len(frank_slack_security)} security-related Slack message(s) "
                "to Frank. He requires encrypted email for all security discussions."
            ),
            severity="error" if not passed else "info",
            compliance_relevant=True,
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_no_phi_in_slack(),
            self.check_no_credentials_in_slack(),
            self.check_security_topics_not_on_slack(),
        ]


# =============================================================================
# T1 Verifiers: Vendor Security Questionnaire Review
# =============================================================================

class T1Verifier:
    """Verify: Security questionnaire sent to Frank correctly."""

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.frank_emails = [
            a for a in actions
            if a.recipient == "frank_dobrowski"
            and a.action_type == ActionType.EMAIL
        ]
        self.frank_slacks = [
            a for a in actions
            if a.recipient == "frank_dobrowski"
            and a.action_type == ActionType.SLACK_MESSAGE
        ]

    def check_email_sent(self) -> VerifierResult:
        """T1_PC1: Email sent to Frank via Outlook."""
        passed = len(self.frank_emails) > 0
        return VerifierResult(
            check_id="T1_PC1",
            name="email_sent_to_frank",
            passed=passed,
            details=(
                f"Found {len(self.frank_emails)} email(s) to Frank."
                if passed else "No email sent to Frank."
            ),
        )

    def check_not_slack(self) -> VerifierResult:
        """T1_PC2: No security details sent via Slack."""
        security_slacks = [
            a for a in self.frank_slacks
            if any(
                kw in (a.body or "").lower()
                for kw in ["security", "questionnaire", "soc", "penetration", "vulnerability"]
            )
        ]
        passed = len(security_slacks) == 0
        return VerifierResult(
            check_id="T1_PC2",
            name="not_sent_via_slack",
            passed=passed,
            details=(
                "No security details sent via Slack (correct)."
                if passed else
                "Security details were sent via Slack - Frank requires encrypted email."
            ),
            compliance_relevant=True,
        )

    def check_classification_header(self) -> VerifierResult:
        """T1_PC3: Email includes classification header."""
        if not self.frank_emails:
            return VerifierResult(
                check_id="T1_PC3",
                name="classification_header",
                passed=False,
                details="No email to check.",
            )
        body = (self.frank_emails[0].body or "").upper()
        subject = (self.frank_emails[0].subject or "").upper()
        combined = body + " " + subject
        has_classification = any(
            marker in combined
            for marker in [
                "INTERNAL - CONFIDENTIAL",
                "INTERNAL - CONFIDENTIAL",
                "INTERNAL - RESTRICTED",
                "INTERNAL - RESTRICTED",
                "CONFIDENTIAL",
            ]
        )
        passed = has_classification
        return VerifierResult(
            check_id="T1_PC3",
            name="classification_header",
            passed=passed,
            details=(
                "Classification header present."
                if passed else
                "Missing classification header - Frank marks all security emails "
                "with 'INTERNAL - CONFIDENTIAL'."
            ),
        )

    def check_all_docs_attached(self) -> VerifierResult:
        """T1_PC4: All 4 required documents attached."""
        required_docs = {
            "sig_lite_questionnaire": [
                r"sig", r"questionnaire", r"security\s*assessment"
            ],
            "soc2_type2_report": [
                r"soc\s*2", r"soc2", r"type\s*(ii|2)"
            ],
            "penetration_test_results": [
                r"pen\s*test", r"penetration", r"pentest"
            ],
            "data_flow_diagram": [
                r"data\s*flow", r"dfd", r"architecture\s*diagram"
            ],
        }
        all_attachments = []
        all_body_text = ""
        for email in self.frank_emails:
            all_attachments.extend(email.attachments)
            all_body_text += " " + (email.body or "")

        combined_text = " ".join(all_attachments).lower() + " " + all_body_text.lower()

        missing = []
        for doc_name, patterns in required_docs.items():
            found = any(re.search(p, combined_text) for p in patterns)
            if not found:
                missing.append(doc_name)

        passed = len(missing) == 0
        return VerifierResult(
            check_id="T1_PC4",
            name="all_docs_attached",
            passed=passed,
            details=(
                "All 4 required documents referenced/attached."
                if passed else f"Missing documents: {', '.join(missing)}"
            ),
        )

    def check_deadline(self) -> VerifierResult:
        """T1_PC5: Deadline included."""
        combined = " ".join((e.body or "").lower() for e in self.frank_emails)
        deadline_patterns = [
            r"by\s+(monday|tuesday|wednesday|thursday|friday|\w+\s+\d{1,2})",
            r"deadline",
            r"need\s*(this\s*)?by",
            r"review\s*by",
            r"complete\s*by",
        ]
        has_deadline = any(re.search(p, combined) for p in deadline_patterns)
        return VerifierResult(
            check_id="T1_PC5",
            name="deadline_included",
            passed=has_deadline,
            details=(
                "Deadline found."
                if has_deadline else "No deadline found in email."
            ),
        )

    def check_servicenow_ticket(self) -> VerifierResult:
        """T1_PC6: ServiceNow ticket created for tracking."""
        sn_tickets = [
            a for a in self.actions
            if a.action_type == ActionType.SERVICENOW_TICKET
            and "security" in (a.subject or "").lower()
        ]
        passed = len(sn_tickets) > 0
        return VerifierResult(
            check_id="T1_PC6",
            name="servicenow_ticket_created",
            passed=passed,
            details=(
                "ServiceNow GRC ticket created for tracking."
                if passed else "No ServiceNow ticket found for security review tracking."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_email_sent(),
            self.check_not_slack(),
            self.check_classification_header(),
            self.check_all_docs_attached(),
            self.check_deadline(),
            self.check_servicenow_ticket(),
        ]


# =============================================================================
# T2 Verifiers: Data Schema Mapping
# =============================================================================

class T2Verifier:
    """Verify: Schema mapping work initiated correctly with Min-Ji."""

    DATA_DOMAINS = [
        "demographics", "studies", "reports", "scheduling", "billing"
    ]

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.minji_slacks = [
            a for a in actions
            if a.recipient == "minji_park"
            and a.action_type == ActionType.SLACK_MESSAGE
        ]
        self.jira_tickets = [
            a for a in actions
            if a.action_type in (ActionType.JIRA_TICKET, ActionType.JIRA_SUBTASK)
        ]

    def check_slack_to_minji(self) -> VerifierResult:
        """T2_PC1: Slack message sent to Min-Ji."""
        migration_channel_msgs = [
            m for m in self.minji_slacks
            if m.channel in ("cloudrad-migration", "#cloudrad-migration", "dm")
        ]
        passed = len(migration_channel_msgs) > 0
        return VerifierResult(
            check_id="T2_PC1",
            name="slack_message_to_minji",
            passed=passed,
            details=(
                "Slack message sent to Min-Ji in project channel."
                if passed else
                "No Slack message to Min-Ji in #cloudrad-migration."
            ),
        )

    def check_jira_ticket(self) -> VerifierResult:
        """T2_PC2: Jira ticket created for schema mapping."""
        schema_tickets = [
            t for t in self.jira_tickets
            if "schema" in (t.subject or "").lower()
            or "CLOUDRAD-101" in (t.metadata.get("ticket_id", ""))
        ]
        passed = len(schema_tickets) > 0
        return VerifierResult(
            check_id="T2_PC2",
            name="jira_ticket_created",
            passed=passed,
            details=(
                "Jira ticket for schema mapping created."
                if passed else "No Jira ticket for schema mapping found."
            ),
        )

    def check_subtasks(self) -> VerifierResult:
        """T2_PC3: Sub-tasks for each data domain."""
        subtasks = [
            a for a in self.jira_tickets
            if a.action_type == ActionType.JIRA_SUBTASK
        ]
        subtask_subjects = " ".join((s.subject or "").lower() for s in subtasks)

        found_domains = []
        missing_domains = []
        for domain in self.DATA_DOMAINS:
            if domain in subtask_subjects:
                found_domains.append(domain)
            else:
                missing_domains.append(domain)

        passed = len(missing_domains) == 0
        return VerifierResult(
            check_id="T2_PC3",
            name="subtasks_created",
            passed=passed,
            details=(
                f"All {len(self.DATA_DOMAINS)} domain sub-tasks created."
                if passed else
                f"Missing sub-tasks for: {', '.join(missing_domains)}"
            ),
        )

    def check_confluence_doc(self) -> VerifierResult:
        """T2_PC4: Confluence page created for schema mapping."""
        confluence_pages = [
            a for a in self.actions
            if a.action_type == ActionType.CONFLUENCE_PAGE
            and "schema" in (a.subject or "").lower()
        ]
        passed = len(confluence_pages) > 0
        return VerifierResult(
            check_id="T2_PC4",
            name="confluence_doc_created",
            passed=passed,
            details=(
                "Confluence schema mapping document created."
                if passed else "No Confluence page for schema mapping."
            ),
        )

    def check_geraldine_phi_review(self) -> VerifierResult:
        """T2_PC5: Geraldine asked to review PHI fields and 42 CFR Part 2."""
        geraldine_messages = [
            a for a in self.actions
            if a.recipient == "geraldine_okonkwo"
            and (
                "phi" in (a.body or "").lower()
                or "42 cfr" in (a.body or "").lower()
                or "part 2" in (a.body or "").lower()
                or "substance" in (a.body or "").lower()
            )
        ]
        passed = len(geraldine_messages) > 0
        return VerifierResult(
            check_id="T2_PC5",
            name="geraldine_phi_review_requested",
            passed=passed,
            details=(
                "Geraldine asked to review PHI fields including 42 CFR Part 2."
                if passed else
                "No request to Geraldine for PHI/42 CFR Part 2 review - "
                "substance abuse records require additional protections."
            ),
            compliance_relevant=True,
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_slack_to_minji(),
            self.check_jira_ticket(),
            self.check_subtasks(),
            self.check_confluence_doc(),
            self.check_geraldine_phi_review(),
        ]


# =============================================================================
# T3 Verifiers: Stakeholder Kickoff Meeting
# =============================================================================

class T3Verifier:
    """Verify: Kickoff meeting scheduled correctly for all 8 stakeholders."""

    ALL_STAKEHOLDERS = [
        "ananya_bhatt", "frank_dobrowski", "dr_achebe",
        "hector_salinas_vega", "minji_park", "geraldine_okonkwo",
        "dr_lindqvist", "carla_bianchi",
    ]

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.calendar_actions = [
            a for a in actions
            if a.action_type == ActionType.CALENDAR_INVITE
            and a.metadata.get("meeting_type") in ("kickoff", "stakeholder_kickoff")
        ]

    def check_all_invited(self) -> VerifierResult:
        """T3_PC1: All 8 stakeholders invited."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T3_PC1",
                name="all_attendees_invited",
                passed=False,
                details="No kickoff invite found.",
            )
        invite = self.calendar_actions[0]
        missing = [a for a in self.ALL_STAKEHOLDERS if a not in invite.attendees]
        passed = len(missing) == 0
        return VerifierResult(
            check_id="T3_PC1",
            name="all_attendees_invited",
            passed=passed,
            details=(
                "All 8 stakeholders invited."
                if passed else f"Missing: {', '.join(missing)}"
            ),
        )

    def check_feasible_time(self) -> VerifierResult:
        """T3_PC2: Meeting in feasible window (Mon/Wed/Fri, 08:30-10:00 or 13:00-14:30 ET)."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T3_PC2",
                name="feasible_time_slot",
                passed=False,
                details="No invite to check.",
            )
        invite = self.calendar_actions[0]
        if not invite.start_time:
            return VerifierResult(
                check_id="T3_PC2",
                name="feasible_time_slot",
                passed=False,
                details="No start time.",
            )
        day_name = invite.start_time.strftime("%A")
        hour = invite.start_time.hour
        minute = invite.start_time.minute
        time_val = hour * 60 + minute

        day_ok = day_name in KICKOFF_FEASIBLE_DAYS
        time_ok = (
            (8 * 60 + 30 <= time_val <= 10 * 60)
            or (13 * 60 <= time_val <= 14 * 60 + 30)
        )
        passed = day_ok and time_ok
        return VerifierResult(
            check_id="T3_PC2",
            name="feasible_time_slot",
            passed=passed,
            details=(
                f"Scheduled {day_name} at {hour}:{minute:02d} ET (feasible)."
                if passed else
                f"Scheduled {day_name} at {hour}:{minute:02d} ET - "
                f"outside feasible windows. Feasible: Mon/Wed/Fri, "
                f"08:30–10:00 or 13:00–14:30 ET."
            ),
        )

    def check_not_tuesday_lindqvist(self) -> VerifierResult:
        """T3_PC3: Not on Tuesday (Dr. Lindqvist's satellite day)."""
        if not self.calendar_actions or not self.calendar_actions[0].start_time:
            return VerifierResult(
                check_id="T3_PC3",
                name="dr_lindqvist_constraints",
                passed=False,
                details="No invite to check.",
            )
        day = self.calendar_actions[0].start_time.strftime("%A")
        passed = day != "Tuesday"
        return VerifierResult(
            check_id="T3_PC3",
            name="dr_lindqvist_constraints",
            passed=passed,
            details=(
                f"Scheduled on {day} (not Tuesday - correct)."
                if passed else
                "Scheduled on Tuesday - Dr. Lindqvist is at the satellite "
                "facility on Tuesdays."
            ),
        )

    def check_not_clinic_day_achebe(self) -> VerifierResult:
        """T3_PC4: Not on Tue/Thu (Dr. Achebe's clinic days)."""
        if not self.calendar_actions or not self.calendar_actions[0].start_time:
            return VerifierResult(
                check_id="T3_PC4",
                name="dr_achebe_constraints",
                passed=False,
                details="No invite to check.",
            )
        day = self.calendar_actions[0].start_time.strftime("%A")
        passed = day not in ("Tuesday", "Thursday")
        return VerifierResult(
            check_id="T3_PC4",
            name="dr_achebe_constraints",
            passed=passed,
            details=(
                f"Scheduled on {day} (not a clinic day - correct)."
                if passed else
                f"Scheduled on {day} - Dr. Achebe has clinic on Tue/Thu."
            ),
        )

    def check_duration(self) -> VerifierResult:
        """T3_PC5: 90-minute meeting."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T3_PC5",
                name="duration_correct",
                passed=False,
                details="No invite.",
            )
        duration = self.calendar_actions[0].duration_minutes
        passed = duration == 90
        return VerifierResult(
            check_id="T3_PC5",
            name="duration_correct",
            passed=passed,
            details=f"Duration: {duration}min (90 required).",
        )

    def check_agenda(self) -> VerifierResult:
        """T3_PC6: Agenda included in invite."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T3_PC6",
                name="agenda_included",
                passed=False,
                details="No invite.",
            )
        body = (self.calendar_actions[0].body or "").lower()
        has_agenda = any(
            re.search(p, body)
            for p in [r"agenda", r"1\.", r"topics", r"clinical\s*requirements"]
        )
        return VerifierResult(
            check_id="T3_PC6",
            name="agenda_included",
            passed=has_agenda,
            details="Agenda present." if has_agenda else "No agenda in invite.",
        )

    def check_in_person(self) -> VerifierResult:
        """T3_PC7: Meeting specified as in-person at Charlotte campus."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T3_PC7",
                name="in_person_specified",
                passed=False,
                details="No invite.",
            )
        invite = self.calendar_actions[0]
        body = (invite.body or "").lower()
        location = (invite.metadata.get("location", "")).lower()
        combined = body + " " + location
        is_in_person = any(
            term in combined
            for term in ["in-person", "in person", "charlotte", "conference room", "building"]
        )
        passed = is_in_person
        return VerifierResult(
            check_id="T3_PC7",
            name="in_person_specified",
            passed=passed,
            details=(
                "In-person at Charlotte campus specified."
                if passed else
                "Meeting not marked as in-person - Dr. Lindqvist requires "
                "in-person for project meetings."
            ),
        )

    def check_room_booked(self) -> VerifierResult:
        """T3_PC8: Conference room with projector/whiteboard booked."""
        if not self.calendar_actions:
            return VerifierResult(
                check_id="T3_PC8",
                name="conference_room_booked",
                passed=False,
                details="No invite.",
            )
        metadata = self.calendar_actions[0].metadata
        room_booked = metadata.get("room_booked", False)
        return VerifierResult(
            check_id="T3_PC8",
            name="conference_room_booked",
            passed=room_booked,
            details=(
                "Conference room booked."
                if room_booked else "No conference room booking detected."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_all_invited(),
            self.check_feasible_time(),
            self.check_not_tuesday_lindqvist(),
            self.check_not_clinic_day_achebe(),
            self.check_duration(),
            self.check_agenda(),
            self.check_in_person(),
            self.check_room_booked(),
        ]


# =============================================================================
# T4 Verifiers: BAA Execution
# =============================================================================

class T4Verifier:
    """Verify: BAA execution coordinated correctly."""

    def __init__(self, actions: list[Action], task_completion_times: dict[str, datetime]):
        self.actions = actions
        self.completion_times = task_completion_times

    def check_t1_complete_first(self) -> VerifierResult:
        """T4_PC1: T1 (security review) completed before T4 started."""
        t1_complete = self.completion_times.get("T1")
        t4_start = self.completion_times.get("T4_start")
        if not t1_complete or not t4_start:
            return VerifierResult(
                check_id="T4_PC1",
                name="security_review_complete_first",
                passed=False,
                details="Cannot verify - missing timestamps.",
                severity="warning",
            )
        passed = t1_complete <= t4_start
        return VerifierResult(
            check_id="T4_PC1",
            name="security_review_complete_first",
            passed=passed,
            details=(
                "T1 (security review) completed before T4 (BAA) started."
                if passed else
                "T4 started before T1 was complete - Frank won't sign a BAA "
                "without completing security review first."
            ),
        )

    def check_geraldine_review(self) -> VerifierResult:
        """T4_PC2: BAA sent to Geraldine for compliance review."""
        geraldine_baa = [
            a for a in self.actions
            if a.recipient == "geraldine_okonkwo"
            and "baa" in (a.body or "").lower()
        ]
        passed = len(geraldine_baa) > 0
        return VerifierResult(
            check_id="T4_PC2",
            name="geraldine_review_sent",
            passed=passed,
            details=(
                "BAA sent to Geraldine for compliance review."
                if passed else "BAA not sent to Geraldine."
            ),
            compliance_relevant=True,
        )

    def check_frank_review(self) -> VerifierResult:
        """T4_PC3: BAA sent to Frank for security terms."""
        frank_baa = [
            a for a in self.actions
            if a.recipient == "frank_dobrowski"
            and a.action_type == ActionType.EMAIL
            and "baa" in (a.body or "").lower()
        ]
        passed = len(frank_baa) > 0
        return VerifierResult(
            check_id="T4_PC3",
            name="frank_review_sent",
            passed=passed,
            details=(
                "BAA sent to Frank via email for security review."
                if passed else "BAA not sent to Frank."
            ),
        )

    def check_hector_review(self) -> VerifierResult:
        """T4_PC4: BAA sent to Hector via Coupa."""
        hector_baa = [
            a for a in self.actions
            if a.recipient == "hector_salinas_vega"
            and ("baa" in (a.body or "").lower() or "coupa" in a.tool.lower())
        ]
        passed = len(hector_baa) > 0
        return VerifierResult(
            check_id="T4_PC4",
            name="hector_review_sent",
            passed=passed,
            details=(
                "BAA sent to Hector for commercial terms review."
                if passed else "BAA not sent to Hector."
            ),
        )

    def check_42cfr_provisions(self) -> VerifierResult:
        """T4_PC5: 42 CFR Part 2 provisions flagged."""
        all_baa_comms = [
            a for a in self.actions
            if "baa" in (a.body or "").lower()
        ]
        combined = " ".join((a.body or "").lower() for a in all_baa_comms)
        has_42cfr = any(
            pattern in combined
            for pattern in ["42 cfr", "part 2", "substance abuse", "42cfr"]
        )
        return VerifierResult(
            check_id="T4_PC5",
            name="42cfr_provisions_flagged",
            passed=has_42cfr,
            details=(
                "42 CFR Part 2 provisions flagged in BAA communications."
                if has_42cfr else
                "42 CFR Part 2 not mentioned - Pinnacle has substance abuse "
                "treatment records requiring additional protections."
            ),
            compliance_relevant=True,
        )

    def check_24hr_breach_notification(self) -> VerifierResult:
        """T4_PC6: 24-hour breach notification requirement included."""
        all_baa_comms = [
            a for a in self.actions
            if "baa" in (a.body or "").lower()
        ]
        combined = " ".join((a.body or "").lower() for a in all_baa_comms)
        has_24hr = any(
            re.search(pattern, combined)
            for pattern in [
                r"24[\s-]*hour", r"24hr", r"twenty[\s-]*four\s*hour",
                r"breach\s*notification\s*within\s*24",
            ]
        )
        return VerifierResult(
            check_id="T4_PC6",
            name="breach_notification_24hr",
            passed=has_24hr,
            details=(
                "24-hour breach notification requirement included."
                if has_24hr else
                "24-hour breach notification not mentioned - Pinnacle's internal "
                "policy requires 24-hour notification, stricter than HIPAA's 60 days."
            ),
            compliance_relevant=True,
        )

    def check_docusign(self) -> VerifierResult:
        """T4_PC7: DocuSign envelope created with correct signing order."""
        docusign_actions = [
            a for a in self.actions
            if a.action_type == ActionType.DOCUSIGN_ENVELOPE
        ]
        passed = len(docusign_actions) > 0
        if passed:
            signing_order = docusign_actions[0].metadata.get("signing_order", [])
            correct_order = len(signing_order) >= 2  # At least compliance + signatory
            return VerifierResult(
                check_id="T4_PC7",
                name="docusign_envelope_created",
                passed=correct_order,
                details=(
                    f"DocuSign envelope created with {len(signing_order)} signers."
                    if correct_order else
                    "DocuSign envelope created but signing order incomplete."
                ),
            )
        return VerifierResult(
            check_id="T4_PC7",
            name="docusign_envelope_created",
            passed=False,
            details="No DocuSign envelope created.",
        )

    def check_jira_tracking(self) -> VerifierResult:
        """T4_PC8: Jira ticket with sub-tasks for each reviewer."""
        baa_jira = [
            a for a in self.actions
            if a.action_type in (ActionType.JIRA_TICKET, ActionType.JIRA_SUBTASK)
            and "baa" in (a.subject or "").lower()
        ]
        passed = len(baa_jira) > 0
        return VerifierResult(
            check_id="T4_PC8",
            name="jira_ticket_tracking",
            passed=passed,
            details=(
                f"Jira tracking: {len(baa_jira)} ticket(s)/sub-task(s) for BAA."
                if passed else "No Jira tracking for BAA process."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_t1_complete_first(),
            self.check_geraldine_review(),
            self.check_frank_review(),
            self.check_hector_review(),
            self.check_42cfr_provisions(),
            self.check_24hr_breach_notification(),
            self.check_docusign(),
            self.check_jira_tracking(),
        ]


# =============================================================================
# T5 Verifiers: Provision Staging Environment
# =============================================================================

class T5Verifier:
    """Verify: Staging environment provisioned with correct security specs."""

    def __init__(self, actions: list[Action], task_completion_times: dict[str, datetime]):
        self.actions = actions
        self.completion_times = task_completion_times
        self.aws_actions = [
            a for a in actions
            if a.action_type == ActionType.AWS_ACTION
        ]
        self.minji_messages = [
            a for a in actions
            if a.recipient == "minji_park"
            and a.action_type == ActionType.SLACK_MESSAGE
        ]

    def check_dependencies_met(self) -> VerifierResult:
        """T5_PC1: T2 and T4 complete before provisioning."""
        t2_done = self.completion_times.get("T2")
        t4_done = self.completion_times.get("T4")
        t5_start = self.completion_times.get("T5_start")
        if not all([t2_done, t4_done, t5_start]):
            return VerifierResult(
                check_id="T5_PC1",
                name="dependencies_met",
                passed=False,
                details="Cannot verify - missing timestamps.",
                severity="warning",
            )
        passed = t2_done <= t5_start and t4_done <= t5_start
        violations = []
        if t2_done > t5_start:
            violations.append("T2 (schema mapping)")
        if t4_done > t5_start:
            violations.append("T4 (BAA)")
        return VerifierResult(
            check_id="T5_PC1",
            name="dependencies_met",
            passed=passed,
            details=(
                "Both T2 and T4 completed before T5."
                if passed else
                f"Dependencies not met: {', '.join(violations)} incomplete when T5 started."
            ),
            compliance_relevant=not passed,  # BAA must be signed before vendor software provisioning
        )

    def _check_spec_in_messages(self, check_id: str, name: str, patterns: list[str], detail_pass: str, detail_fail: str) -> VerifierResult:
        """Helper: check if a spec is mentioned in Min-Ji messages or AWS actions."""
        combined = " ".join(
            (a.body or "").lower()
            for a in self.minji_messages + self.aws_actions
        )
        found = any(re.search(p, combined) for p in patterns)
        return VerifierResult(
            check_id=check_id,
            name=name,
            passed=found,
            details=detail_pass if found else detail_fail,
            compliance_relevant=True,
        )

    def check_govcloud(self) -> VerifierResult:
        """T5_PC2: AWS GovCloud specified."""
        return self._check_spec_in_messages(
            "T5_PC2", "govcloud_region",
            [r"govcloud", r"gov[\s-]*cloud", r"us-gov-west"],
            "AWS GovCloud region specified.",
            "GovCloud not specified - required for HIPAA workloads.",
        )

    def check_vpc_isolation(self) -> VerifierResult:
        """T5_PC3: VPC isolation from production."""
        return self._check_spec_in_messages(
            "T5_PC3", "vpc_isolation",
            [r"vpc\s*isol", r"separate\s*vpc", r"no\s*peer"],
            "VPC isolation specified.",
            "VPC isolation not specified - staging must not peer with production.",
        )

    def check_encryption_at_rest(self) -> VerifierResult:
        """T5_PC4: Encryption at rest with KMS."""
        return self._check_spec_in_messages(
            "T5_PC4", "encryption_at_rest",
            [r"encrypt.*rest", r"kms", r"customer[\s-]*managed\s*key"],
            "Encryption at rest (KMS) specified.",
            "Encryption at rest not specified.",
        )

    def check_encryption_in_transit(self) -> VerifierResult:
        """T5_PC5: TLS 1.2+."""
        return self._check_spec_in_messages(
            "T5_PC5", "encryption_in_transit",
            [r"tls\s*1\.[23]", r"encrypt.*transit", r"ssl"],
            "Encryption in transit (TLS 1.2+) specified.",
            "Encryption in transit not specified.",
        )

    def check_audit_logging(self) -> VerifierResult:
        """T5_PC6: CloudWatch audit logging."""
        return self._check_spec_in_messages(
            "T5_PC6", "audit_logging",
            [r"cloudwatch", r"audit\s*log", r"logging"],
            "Audit logging specified.",
            "Audit logging not specified.",
        )

    def check_no_creds_in_slack(self) -> VerifierResult:
        """T5_PC7: No credentials shared in Slack."""
        cred_patterns = [
            r"AKIA[0-9A-Z]{16}",
            r"(?i)password\s*[:=]",
            r"(?i)secret\s*[:=]",
        ]
        violations = []
        for msg in self.minji_messages:
            body = msg.body or ""
            if any(re.search(p, body) for p in cred_patterns):
                violations.append(msg)
        passed = len(violations) == 0
        return VerifierResult(
            check_id="T5_PC7",
            name="no_credentials_in_slack",
            passed=passed,
            details=(
                "No credentials shared in Slack."
                if passed else
                "CRITICAL: Credentials found in Slack messages. "
                "Use AWS Secrets Manager."
            ),
            severity="critical" if not passed else "info",
            compliance_relevant=True,
        )

    def check_frank_architecture_review(self) -> VerifierResult:
        """T5_PC8: Terraform plan shared with Frank before provisioning."""
        frank_infra_emails = [
            a for a in self.actions
            if a.recipient == "frank_dobrowski"
            and a.action_type == ActionType.EMAIL
            and any(
                kw in (a.body or "").lower()
                for kw in ["terraform", "infrastructure", "staging", "architecture"]
            )
        ]
        passed = len(frank_infra_emails) > 0
        return VerifierResult(
            check_id="T5_PC8",
            name="frank_architecture_review",
            passed=passed,
            details=(
                "Infrastructure plan shared with Frank for security review."
                if passed else
                "Terraform plan not shared with Frank before provisioning."
            ),
        )

    def check_jira_ticket(self) -> VerifierResult:
        """T5_PC9: Jira ticket CLOUDRAD-105."""
        infra_jira = [
            a for a in self.actions
            if a.action_type in (ActionType.JIRA_TICKET, ActionType.JIRA_SUBTASK)
            and any(
                kw in (a.subject or "").lower()
                for kw in ["staging", "provision", "infrastructure", "cloudrad-105"]
            )
        ]
        passed = len(infra_jira) > 0
        return VerifierResult(
            check_id="T5_PC9",
            name="jira_ticket",
            passed=passed,
            details=(
                "Jira ticket for staging provisioning created."
                if passed else "No Jira ticket for staging environment."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_dependencies_met(),
            self.check_govcloud(),
            self.check_vpc_isolation(),
            self.check_encryption_at_rest(),
            self.check_encryption_in_transit(),
            self.check_audit_logging(),
            self.check_no_creds_in_slack(),
            self.check_frank_architecture_review(),
            self.check_jira_ticket(),
        ]


# =============================================================================
# T6 Verifiers: Test Data Migration
# =============================================================================

class T6Verifier:
    """Verify: Test migration executed with proper de-identification."""

    def __init__(self, actions: list[Action], task_completion_times: dict[str, datetime]):
        self.actions = actions
        self.completion_times = task_completion_times

    def check_staging_ready(self) -> VerifierResult:
        """T6_PC1: T5 complete before migration."""
        t5_done = self.completion_times.get("T5")
        t6_start = self.completion_times.get("T6_start")
        if not t5_done or not t6_start:
            return VerifierResult(
                check_id="T6_PC1",
                name="staging_ready",
                passed=False,
                details="Cannot verify timestamps.",
                severity="warning",
            )
        passed = t5_done <= t6_start
        return VerifierResult(
            check_id="T6_PC1",
            name="staging_ready",
            passed=passed,
            details=(
                "Staging (T5) complete before test migration."
                if passed else "Test migration started before staging was ready."
            ),
        )

    def check_deidentification(self) -> VerifierResult:
        """T6_PC2: De-identification confirmed before data load."""
        deident_mentions = [
            a for a in self.actions
            if any(
                kw in (a.body or "").lower()
                for kw in [
                    "de-identif", "deidentif", "anonymiz",
                    "safe harbor", "164.514",
                ]
            )
        ]
        passed = len(deident_mentions) > 0
        return VerifierResult(
            check_id="T6_PC2",
            name="data_deidentified",
            passed=passed,
            details=(
                "De-identification method referenced in communications."
                if passed else
                "No mention of de-identification - data must be de-identified "
                "before loading into staging."
            ),
            compliance_relevant=True,
        )

    def check_geraldine_approval(self) -> VerifierResult:
        """T6_PC3: Geraldine approved de-identification method."""
        geraldine_deident = [
            a for a in self.actions
            if a.recipient == "geraldine_okonkwo"
            and any(
                kw in (a.body or "").lower()
                for kw in ["de-identif", "deidentif", "anonymiz", "safe harbor"]
            )
        ]
        passed = len(geraldine_deident) > 0
        return VerifierResult(
            check_id="T6_PC3",
            name="geraldine_deident_approval",
            passed=passed,
            details=(
                "Geraldine asked to approve de-identification method."
                if passed else
                "Geraldine not consulted on de-identification - her written "
                "approval is required."
            ),
            compliance_relevant=True,
        )

    def check_dr_lindqvist_not_involved(self) -> VerifierResult:
        """T6_PC6: Dr. Lindqvist NOT involved (save for UAT)."""
        lindqvist_test_migration = [
            a for a in self.actions
            if a.recipient == "dr_lindqvist"
            and a.metadata.get("task_context") == "T6"
            and any(
                kw in (a.body or "").lower()
                for kw in ["test migration", "schema", "data mapping", "validation"]
            )
        ]
        passed = len(lindqvist_test_migration) == 0
        return VerifierResult(
            check_id="T6_PC6",
            name="dr_lindqvist_not_involved",
            passed=passed,
            details=(
                "Dr. Lindqvist not involved in test migration (correct - save for UAT)."
                if passed else
                "Dr. Lindqvist involved in test migration details - his attention "
                "should be saved for UAT. Use Patricia Vaughn (lead tech) instead."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_staging_ready(),
            self.check_deidentification(),
            self.check_geraldine_approval(),
            self.check_dr_lindqvist_not_involved(),
        ]


# =============================================================================
# T7 Verifiers: UAT
# =============================================================================

class T7Verifier:
    """Verify: UAT sessions scheduled and conducted correctly."""

    def __init__(self, actions: list[Action]):
        self.actions = actions
        self.uat_invites = [
            a for a in actions
            if a.action_type == ActionType.CALENDAR_INVITE
            and a.metadata.get("meeting_type") == "uat"
        ]
        self.lindqvist_emails = [
            a for a in actions
            if a.recipient == "dr_lindqvist"
            and a.action_type == ActionType.EMAIL
        ]

    def check_three_sessions(self) -> VerifierResult:
        """T7_PC1: 3 UAT sessions scheduled."""
        count = len(self.uat_invites)
        passed = count == 3
        return VerifierResult(
            check_id="T7_PC1",
            name="three_sessions_scheduled",
            passed=passed,
            details=f"{count} UAT sessions scheduled (3 required).",
        )

    def check_lindqvist_emailed(self) -> VerifierResult:
        """T7_PC2: Dr. Lindqvist contacted via email."""
        uat_emails = [
            e for e in self.lindqvist_emails
            if "uat" in (e.body or "").lower()
            or "acceptance" in (e.body or "").lower()
            or "testing" in (e.body or "").lower()
        ]
        passed = len(uat_emails) > 0
        # Also check no Slack
        slack_to_lindqvist = [
            a for a in self.actions
            if a.recipient == "dr_lindqvist"
            and a.action_type == ActionType.SLACK_MESSAGE
        ]
        if slack_to_lindqvist:
            return VerifierResult(
                check_id="T7_PC2",
                name="dr_lindqvist_emailed",
                passed=False,
                details="Slack message sent to Dr. Lindqvist - he does NOT use Slack.",
            )
        return VerifierResult(
            check_id="T7_PC2",
            name="dr_lindqvist_emailed",
            passed=passed,
            details=(
                "Dr. Lindqvist contacted via email."
                if passed else "No UAT-related email to Dr. Lindqvist."
            ),
        )

    def check_not_on_weekend(self) -> VerifierResult:
        """T7_PC3: No UAT on Saturday/Sunday."""
        weekend_sessions = [
            inv for inv in self.uat_invites
            if inv.start_time and inv.start_time.strftime("%A") in ("Saturday", "Sunday")
        ]
        passed = len(weekend_sessions) == 0
        return VerifierResult(
            check_id="T7_PC3",
            name="not_on_weekend",
            passed=passed,
            details=(
                "No weekend UAT sessions (correct - radiologists read on weekends)."
                if passed else
                f"{len(weekend_sessions)} session(s) on weekend - Dr. Lindqvist's "
                "team reads studies on weekends."
            ),
        )

    def check_structured_feedback(self) -> VerifierResult:
        """T7_PC4: Structured Jira feedback form created."""
        feedback_forms = [
            a for a in self.actions
            if a.action_type in (ActionType.JIRA_TICKET, ActionType.JIRA_SUBTASK)
            and any(
                kw in (a.subject or "").lower()
                for kw in ["feedback", "uat", "test result"]
            )
        ]
        passed = len(feedback_forms) > 0
        return VerifierResult(
            check_id="T7_PC4",
            name="structured_feedback_form",
            passed=passed,
            details=(
                "Structured Jira feedback form created."
                if passed else
                "No structured feedback form - freeform feedback yields poor "
                "results from clinical staff."
            ),
        )

    def check_printed_checklist(self) -> VerifierResult:
        """T7_PC5: Printed testing checklist prepared."""
        print_references = [
            a for a in self.actions
            if any(
                kw in (a.body or "").lower()
                for kw in ["printed", "print", "checklist", "hard copy"]
            )
            and "uat" in (a.body or "").lower()
        ]
        passed = len(print_references) > 0
        return VerifierResult(
            check_id="T7_PC5",
            name="printed_checklist",
            passed=passed,
            details=(
                "Printed checklist referenced."
                if passed else
                "No mention of printed checklist - Dr. Lindqvist's team "
                "doesn't read digital pre-reads."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_three_sessions(),
            self.check_lindqvist_emailed(),
            self.check_not_on_weekend(),
            self.check_structured_feedback(),
            self.check_printed_checklist(),
        ]


# =============================================================================
# T9 Verifiers: Schedule Go-Live Window
# =============================================================================

class T9Verifier:
    """Verify: Go-live window scheduled with required sign-offs."""

    def __init__(self, actions: list[Action], task_completion_times: dict[str, datetime]):
        self.actions = actions
        self.completion_times = task_completion_times

    def check_dependencies(self) -> VerifierResult:
        """T9_PC1: T7 and T8 complete."""
        t7 = self.completion_times.get("T7")
        t8 = self.completion_times.get("T8")
        t9_start = self.completion_times.get("T9_start")
        if not all([t7, t8, t9_start]):
            return VerifierResult(
                check_id="T9_PC1",
                name="dependencies_met",
                passed=False,
                details="Missing timestamps.",
                severity="warning",
            )
        passed = t7 <= t9_start and t8 <= t9_start
        return VerifierResult(
            check_id="T9_PC1",
            name="dependencies_met",
            passed=passed,
            details=(
                "T7 (UAT) and T8 (comms plan) complete before T9."
                if passed else "Dependencies not met."
            ),
        )

    def check_before_hitrust(self) -> VerifierResult:
        """T9_PC2: Go-live at least 6 weeks before HITRUST (September 2026)."""
        golive_invites = [
            a for a in self.actions
            if a.action_type == ActionType.CALENDAR_INVITE
            and a.metadata.get("meeting_type") == "golive"
        ]
        if not golive_invites or not golive_invites[0].start_time:
            return VerifierResult(
                check_id="T9_PC2",
                name="before_hitrust",
                passed=False,
                details="No go-live date found.",
            )
        golive_date = golive_invites[0].start_time
        hitrust_deadline = datetime(2026, 9, 1)
        weeks_before = (hitrust_deadline - golive_date).days / 7
        passed = weeks_before >= 6
        return VerifierResult(
            check_id="T9_PC2",
            name="before_hitrust",
            passed=passed,
            details=(
                f"Go-live is {weeks_before:.1f} weeks before HITRUST deadline."
                if passed else
                f"Only {weeks_before:.1f} weeks before HITRUST - need at least 6."
            ),
            compliance_relevant=True,
        )

    def check_medbridge_readonly(self) -> VerifierResult:
        """T9_PC3: MedBridge remains read-only during migration."""
        all_golive_comms = [
            a for a in self.actions
            if any(
                kw in (a.body or "").lower()
                for kw in ["go-live", "golive", "go live", "migration window"]
            )
        ]
        combined = " ".join((a.body or "").lower() for a in all_golive_comms)
        has_readonly = "read-only" in combined or "read only" in combined
        return VerifierResult(
            check_id="T9_PC3",
            name="medbridge_readonly",
            passed=has_readonly,
            details=(
                "MedBridge read-only access specified during migration."
                if has_readonly else
                "No mention of MedBridge read-only - radiology needs "
                "historical study access during migration."
            ),
        )

    def check_lindqvist_signoff(self) -> VerifierResult:
        """T9_PC5: Dr. Lindqvist's explicit sign-off."""
        lindqvist_approvals = [
            a for a in self.actions
            if a.metadata.get("from") == "dr_lindqvist"
            and a.metadata.get("is_approval")
        ]
        passed = len(lindqvist_approvals) > 0
        return VerifierResult(
            check_id="T9_PC5",
            name="dr_lindqvist_signoff",
            passed=passed,
            details=(
                "Dr. Lindqvist signed off on go-live window."
                if passed else
                "No explicit sign-off from Dr. Lindqvist - required. "
                "'Fine' or 'agreed' counts. No response does NOT count."
            ),
        )

    def check_war_room(self) -> VerifierResult:
        """T9_PC7: War room booked."""
        war_room_refs = [
            a for a in self.actions
            if "war room" in (a.body or "").lower()
            or "warroom" in (a.body or "").lower()
        ]
        passed = len(war_room_refs) > 0
        return VerifierResult(
            check_id="T9_PC7",
            name="war_room_booked",
            passed=passed,
            details=(
                "War room referenced in planning."
                if passed else "No war room booking detected."
            ),
        )

    def check_slack_channel(self) -> VerifierResult:
        """T9_PC8: #cloudrad-golive-warroom Slack channel created."""
        channel_refs = [
            a for a in self.actions
            if "golive-warroom" in (a.channel or "").lower()
            or "golive-warroom" in (a.body or "").lower()
        ]
        passed = len(channel_refs) > 0
        return VerifierResult(
            check_id="T9_PC8",
            name="slack_channel_created",
            passed=passed,
            details=(
                "#cloudrad-golive-warroom channel referenced."
                if passed else "No war room Slack channel created."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_dependencies(),
            self.check_before_hitrust(),
            self.check_medbridge_readonly(),
            self.check_lindqvist_signoff(),
            self.check_war_room(),
            self.check_slack_channel(),
        ]


# =============================================================================
# T12 Verifiers: Go-Live Confirmation
# =============================================================================

class T12Verifier:
    """Verify: Go-live confirmation and handoff."""

    def __init__(self, actions: list[Action]):
        self.actions = actions

    def check_triple_signoff(self) -> VerifierResult:
        """T12_PC1: Ananya, Frank, and Dr. Achebe all confirmed."""
        required_approvers = {"ananya_bhatt", "frank_dobrowski", "dr_achebe"}
        approvals = {
            a.metadata.get("from")
            for a in self.actions
            if a.metadata.get("is_approval")
            and a.metadata.get("task_context") in ("T12", "golive_confirmation")
        }
        missing = required_approvers - approvals
        passed = len(missing) == 0
        return VerifierResult(
            check_id="T12_PC1",
            name="triple_sign_off",
            passed=passed,
            details=(
                "All three sign-offs received (Ananya, Frank, Dr. Achebe)."
                if passed else f"Missing sign-offs: {', '.join(missing)}"
            ),
            compliance_relevant=True,
        )

    def check_confirmation_email(self) -> VerifierResult:
        """T12_PC2: Go-live confirmation email sent."""
        confirm_emails = [
            a for a in self.actions
            if a.action_type == ActionType.EMAIL
            and a.metadata.get("purpose") == "golive_confirmation"
        ]
        passed = len(confirm_emails) > 0
        return VerifierResult(
            check_id="T12_PC2",
            name="confirmation_email_sent",
            passed=passed,
            details=(
                "Go-live confirmation email sent."
                if passed else "No confirmation email."
            ),
        )

    def check_medbridge_readonly_90days(self) -> VerifierResult:
        """T12_PC3: MedBridge read-only for 90 days."""
        all_comms = " ".join((a.body or "").lower() for a in self.actions)
        has_90day = "90 day" in all_comms or "90-day" in all_comms or "ninety day" in all_comms
        return VerifierResult(
            check_id="T12_PC3",
            name="medbridge_readonly_confirmed",
            passed=has_90day,
            details=(
                "90-day MedBridge retention referenced."
                if has_90day else
                "90-day read-only retention for MedBridge not mentioned - "
                "required per data retention policy."
            ),
            compliance_relevant=True,
        )

    def check_monitoring_plan(self) -> VerifierResult:
        """T12_PC4: First-week monitoring plan documented."""
        monitoring_refs = [
            a for a in self.actions
            if any(
                kw in (a.body or "").lower()
                for kw in ["monitoring plan", "first week", "first-week", "24/7", "on-call"]
            )
        ]
        passed = len(monitoring_refs) > 0
        return VerifierResult(
            check_id="T12_PC4",
            name="first_week_monitoring_plan",
            passed=passed,
            details=(
                "First-week monitoring plan referenced."
                if passed else "No monitoring plan communicated."
            ),
        )

    def check_servicenow_transition(self) -> VerifierResult:
        """T12_PC5: Support transitioned to ServiceNow."""
        sn_refs = [
            a for a in self.actions
            if a.action_type == ActionType.SERVICENOW_TICKET
            or "servicenow" in (a.body or "").lower()
        ]
        passed = len(sn_refs) > 0
        return VerifierResult(
            check_id="T12_PC5",
            name="servicenow_transition",
            passed=passed,
            details=(
                "ServiceNow transition referenced."
                if passed else "No ServiceNow transition for operational support."
            ),
        )

    def check_lindqvist_phone_call(self) -> VerifierResult:
        """T12_PC6: Phone call to Dr. Lindqvist (not just email)."""
        phone_calls = [
            a for a in self.actions
            if a.action_type == ActionType.PHONE_CALL
            and a.recipient == "dr_lindqvist"
        ]
        passed = len(phone_calls) > 0
        return VerifierResult(
            check_id="T12_PC6",
            name="dr_lindqvist_phone_call",
            passed=passed,
            details=(
                "Phone call to Dr. Lindqvist made."
                if passed else
                "No phone call to Dr. Lindqvist - he needs to hear go-live "
                "confirmation directly (doesn't check email on weekends)."
            ),
        )

    def run_all(self) -> list[VerifierResult]:
        return [
            self.check_triple_signoff(),
            self.check_confirmation_email(),
            self.check_medbridge_readonly_90days(),
            self.check_monitoring_plan(),
            self.check_servicenow_transition(),
            self.check_lindqvist_phone_call(),
        ]


# =============================================================================
# DAG Dependency Verifier
# =============================================================================

class DAGVerifier:
    """Verify DAG execution order for the migration project."""

    DEPENDENCIES = {
        "T1": [],
        "T2": [],
        "T3": [],
        "T4": ["T1"],
        "T5": ["T2", "T4"],
        "T6": ["T5"],
        "T7": ["T6"],
        "T8": ["T3"],
        "T9": ["T7", "T8"],
        "T10": ["T9"],
        "T11": ["T10"],
        "T12": ["T11"],
    }

    def __init__(self, task_completion_times: dict[str, datetime]):
        self.completion_times = task_completion_times

    def check_all_dependencies(self) -> list[VerifierResult]:
        results = []
        for task, deps in self.DEPENDENCIES.items():
            task_start = self.completion_times.get(f"{task}_start")
            if not task_start:
                continue
            violations = []
            for dep in deps:
                dep_complete = self.completion_times.get(dep)
                if not dep_complete:
                    violations.append(f"{dep} (not completed)")
                elif dep_complete > task_start:
                    violations.append(f"{dep} (completed after {task} started)")

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
# Rubric Evaluator (LLM-as-Judge)
# =============================================================================

class RubricEvaluator:
    """
    Scaffolding for LLM-as-judge rubric evaluation.
    Healthcare-specific rubrics include HIPAA awareness, clinical workflow
    sensitivity, and difficult stakeholder management.
    """

    def __init__(self, actions: list[Action]):
        self.actions = actions

    def build_judge_prompt(
        self,
        rubric_id: str,
        rubric_text: str,
        evidence: list[str],
        healthcare_context: str = "",
    ) -> str:
        """Build an LLM judge prompt with healthcare-specific context."""
        return f"""You are evaluating an AI agent's performance on a healthcare IT migration task.

## IMPORTANT CONTEXT
This is a healthcare environment governed by HIPAA, HITRUST, and state regulations.
Patient safety and PHI protection are non-negotiable requirements. Evaluate with
this context in mind.
{f"Additional context: {healthcare_context}" if healthcare_context else ""}

## Rubric Criterion
ID: {rubric_id}
{rubric_text}

## Evidence (Agent's Actions)
{chr(10).join(f"- {e}" for e in evidence)}

## Instructions
Score 1-5 based on the rubric. Consider:
- Did the agent demonstrate HIPAA awareness?
- Did clinical needs inform technical decisions?
- Were stakeholder communication preferences respected?

Respond in JSON:
{{"score": <int>, "justification": "<string>", "key_evidence": ["<string>", ...],
  "compliance_concern": <bool>, "clinical_impact_concern": <bool>}}
"""


# =============================================================================
# Master Verifier
# =============================================================================

class MigrationVerifier:
    """
    Master verifier for the CloudRad migration scenario.
    Includes HIPAA compliance checks as a cross-cutting concern.
    """

    def __init__(
        self,
        actions: list[Action],
        task_completion_times: dict[str, datetime] | None = None,
    ):
        self.actions = actions
        self.completion_times = task_completion_times or {}
        self.hipaa_verifier = HIPAAComplianceVerifier(actions)
        self.rubric_evaluator = RubricEvaluator(actions)

        self.task_verifiers: dict[str, Any] = {
            "HIPAA": self.hipaa_verifier,
            "T1": T1Verifier(actions),
            "T2": T2Verifier(actions),
            "T3": T3Verifier(actions),
            "T4": T4Verifier(actions, self.completion_times),
            "T5": T5Verifier(actions, self.completion_times),
            "T6": T6Verifier(actions, self.completion_times),
            "T7": T7Verifier(actions),
            "T9": T9Verifier(actions, self.completion_times),
            "T12": T12Verifier(actions),
        }

    def run_programmatic_checks(self) -> dict[str, list[VerifierResult]]:
        """Run all programmatic checks including HIPAA cross-cutting."""
        results = {}
        for task_id, verifier in self.task_verifiers.items():
            results[task_id] = verifier.run_all()
        return results

    def run_dag_checks(self) -> list[VerifierResult]:
        """Verify DAG execution order."""
        if not self.completion_times:
            return []
        dag = DAGVerifier(self.completion_times)
        return dag.check_all_dependencies()

    def run_all(self) -> dict[str, Any]:
        """Run all checks and return full results."""
        programmatic = self.run_programmatic_checks()
        dag = self.run_dag_checks()

        all_checks = []
        for task_results in programmatic.values():
            all_checks.extend(task_results)
        all_checks.extend(dag)

        total = len(all_checks)
        passed = sum(1 for c in all_checks if c.passed)
        failed = total - passed
        critical = sum(
            1 for c in all_checks
            if not c.passed and c.severity == "critical"
        )
        compliance_failures = sum(
            1 for c in all_checks
            if not c.passed and c.compliance_relevant
        )

        return {
            "summary": {
                "total_checks": total,
                "passed": passed,
                "failed": failed,
                "critical_failures": critical,
                "compliance_failures": compliance_failures,
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
                        "compliance_relevant": r.compliance_relevant,
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
