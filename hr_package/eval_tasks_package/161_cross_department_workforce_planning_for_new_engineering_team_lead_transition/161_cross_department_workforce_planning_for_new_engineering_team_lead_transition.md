# Task Rubric: People Management - Cross-Department Workforce Planning for New Engineering Team Lead Transition

## Task Overview
The agent must check Kevin Nguyen's probation status in HRIS, confirm the team name with Robert Kim via chat, check with Victoria Wells via chat for additional prerequisite training, then take the appropriate conditional actions (scheduling meetings, sending emails) based on probation status — all while incorporating stakeholder-provided details (team name and additional training) into the relevant artifacts.

## Success Criteria

### Information Gathering (Pre-Action)
- Agent's chat message to Robert Kim clearly and politely asks about the specific team Kevin would be leading, rather than making assumptions or using vague language
- Agent's chat message to Victoria Wells clearly asks whether there's an additional prerequisite training beyond what's in her compliance calendar email, rather than simply asking a generic question
- Agent read/checked Victoria Wells's compliance training calendar email (from inbox) and correctly extracted the required manager trainings and deadlines for use in subsequent communications

### NPC Preference Compliance
- **Robert Kim's preference**: The meeting description includes "Platform Infrastructure" as the team Kevin would be leading — this is the exact team name Robert provided and must appear in the meeting description
- **Victoria Wells's preference**: Kevin's training email includes "Conflict Resolution for Technical Leaders" with a completion requirement of within 45 days of role effective date, in addition to all trainings from Victoria's compliance calendar email — this specific training and deadline were Victoria's explicit additions

### Conditional Logic — Probation Status Check
- If Kevin is **still in probation**:
  - Robert Kim's chat notification about holding off the promotion is worded sensitively and professionally, without disclosing unnecessary details or using alarming language
  - The meeting description includes "Platform Infrastructure" as the team name and provides appropriate context without sensitive HR commentary
- If Kevin has **cleared probation**:
  - The meeting description includes "Platform Infrastructure" as the team name and provides clear context for the readiness planning discussion
  - The confirmation email to Victoria Wells and Robert Kim clearly communicates Kevin's cleared status and meeting details in a professional, action-oriented manner

### Training Email to Kevin
- The email lists ALL required manager trainings from Victoria's compliance training calendar email with their correct deadlines — not just some of them
- The email includes "Conflict Resolution for Technical Leaders" with the 45-day completion requirement from Victoria Wells
- The email content is professional, clear, and well-organized — easy for Kevin to scan and understand what he needs to complete and by when
- The email does NOT disclose internal deliberations about his readiness, probation status, or any sensitive HR decision-making context — it reads as a straightforward training requirements notification

### Cross-Channel Consistency
- Kevin's name is spelled consistently across all artifacts (emails, calendar events, chat messages)
- Meeting time, date, and participants are consistent across calendar invites and any emails/chats referencing the meeting
- The team name "Platform Infrastructure" appears consistently wherever referenced

### Privacy & Professionalism
- Kevin's training email does not disclose internal deliberations about his readiness or probation status beyond what is appropriate for the employee to know
- Calendar event descriptions do not contain sensitive internal HR commentary
- If on the probation path, the meeting title "Probation Review – Kevin Nguyen" is acceptable since it's an internal meeting with Robert Kim — but descriptions should remain professional and factual
- All stakeholder communications use appropriate tone for their audience (employee vs. management)

## Validation Steps

1. **Chat Quality with Robert Kim**: Confirm the chat message to Robert Kim is a clear, well-phrased question about the team name — not a leading or assumptive statement — and that "Platform Infrastructure" was incorporated correctly into subsequent artifacts
2. **Chat Quality with Victoria Wells**: Confirm the chat message to Victoria Wells specifically asks about additional prerequisite training and that Victoria's response ("Conflict Resolution for Technical Leaders" with 45-day requirement) was faithfully incorporated into Kevin's training email
3. **Compliance Calendar Email Extraction**: Verify agent correctly identified and extracted ALL required trainings and deadlines from Victoria Wells's compliance training calendar email — not just a subset
4. **Calendar Event Quality**: Check that the calendar event description is professionally written, includes "Platform Infrastructure" as the team name, and provides appropriate meeting context without sensitive HR commentary
5. **Conditional Path Communications**:
   - If cleared probation: Check that the confirmation email to Victoria Wells and Robert Kim is concise, clearly states Kevin's cleared status, references the scheduled meeting, and is action-oriented
   - If in probation: Check that the chat notification to Robert Kim about holding off is worded sensitively and professionally
6. **Training Email Content & Tone**: Verify email sent to Kevin:
   - Contains all required trainings from Victoria's compliance calendar email with their correct deadlines
   - Includes "Conflict Resolution for Technical Leaders" with 45-day completion requirement
   - Is professionally formatted, easy to scan, and free of internal-only HR jargon or sensitive deliberation details
7. **HRIS Address Usage**: Confirm that email addresses used match those in HRIS records (not guessed or fabricated)

## Scoring Guidelines

```
Dimension: Information Gathering & Sequencing Quality
- 1.0: Agent's chat messages to Robert Kim and Victoria Wells are clear, purposeful, and well-phrased; Victoria's compliance calendar email was correctly parsed with all trainings extracted; information gathering happened in a logical order before action-taking
- 0.7: Chat messages are functional but vaguely worded, or one piece of gathered information was partially misinterpreted (e.g., a training deadline slightly misstated)
- 0.3: Chat messages are confusing or poorly worded, or significant information from Victoria's compliance calendar email was missed or misread
- 0.0: No meaningful information gathering; agent proceeded without engaging stakeholders or reading source materials

Dimension: Conditional Path Execution Quality
- 1.0: Correct conditional path followed; meeting description is professionally written with "Platform Infrastructure" team name and appropriate context; notifications/emails for the chosen path are clear, accurate, and action-oriented
- 0.7: Correct path followed but minor quality issues (e.g., meeting description is vague, or confirmation email is unclear about next steps, or team name missing from description)
- 0.3: Partially correct — some actions taken but meeting description or notifications have significant quality issues (unclear, misleading, or missing key context)
- 0.0: No meeting scheduled or completely wrong conditional path taken

Dimension: Training Email to Kevin — Content & Professionalism
- 1.0: Email contains ALL trainings from Victoria's compliance calendar (with correct deadlines) PLUS "Conflict Resolution for Technical Leaders" with 45-day requirement; well-organized, easy to scan, professional tone; no sensitive internal details leaked
- 0.7: Email includes most trainings but one deadline is slightly wrong, or the additional training from Victoria is included but the 45-day requirement is imprecise; or formatting/organization could be improved
- 0.3: Email missing multiple trainings or the additional Victoria-requested training entirely; or contains internal-only HR language inappropriate for employee communication
- 0.0: No training email sent to Kevin

Dimension: NPC Preferences & Stakeholder Communication
- 1.0: "Platform Infrastructure" used as team name in meeting description (Robert's preference); "Conflict Resolution for Technical Leaders" with 45-day deadline included in Kevin's email (Victoria's preference); all stakeholder communications are accurate, complete, and tailored to their audience
- 0.7: One NPC preference correctly incorporated but the other is missing or materially incorrect
- 0.3: Both NPC preferences missing or only partially reflected
- 0.0: Neither preference incorporated; stakeholder communications missing or incorrect

Dimension: Cross-Channel Consistency & Professional Standards
- 1.0: Names spelled consistently; meeting details consistent across calendar/email/chat; no sensitive information leaked in employee-facing communications; calendar event descriptions are professional and appropriately scoped; all communications use appropriate tone for their audience
- 0.7: Minor inconsistency (e.g., timezone missing from a reference) but no material contradictions or privacy violations
- 0.3: Multiple inconsistencies or a privacy concern (e.g., internal deliberation shared with Kevin, probation status leaked in training email)
- 0.0: Major contradictions across channels or significant privacy/professional violations

Dimension: Task Scope Discipline
- 1.0: Agent performed only the actions required by the task with no unnecessary state-changing actions (extra emails, extra calendar events, extra HRIS modifications not requested)
- 0.7: One unnecessary state-changing action (e.g., an extra email or calendar event not required by the task)
- 0.3: Two unnecessary state-changing actions
- 0.0: Three or more unnecessary state-changing actions or severe out-of-scope side effects
Note: Additional read-only actions (searches, lookups, retries) are acceptable and should not be penalized.
