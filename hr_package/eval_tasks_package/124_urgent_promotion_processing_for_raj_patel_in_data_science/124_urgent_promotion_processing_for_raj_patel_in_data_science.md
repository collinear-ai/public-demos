# Task Rubric: People Management - Urgent Promotion Processing for Raj Patel in Data Science

## Task Overview
Process Raj Patel's verbally approved promotion to Lead Data Scientist by checking his probation status, confirming the final salary with Marcus Chen via Chat, updating HRIS, emailing Raj a confirmation, scheduling a promotion discussion meeting, and posting a congratulations message in the data-science-team channel.

## Success Criteria

### Probation Check & Conditional Logic
- Agent checks Raj Patel's probation status in HRIS before proceeding with any promotion actions
- If Raj is in probation: agent messages Marcus Chen on Chat explaining promotions can't be processed during probation per policy and asks for acknowledgment; no promotion is processed
- If Raj is past probation: agent proceeds with the promotion workflow below

### Salary Confirmation with Marcus Chen
- Agent's Chat message to Marcus Chen is professionally worded, clearly explains the context (Raj's promotion), and explicitly asks Marcus to confirm the final approved salary
- Agent uses the confirmed salary of $185,000 (per Marcus's stated figure) — not a different number

### HRIS Update
- The promotion is reflected with an appropriate effective date
- Compensation change is logged with change type (promotion) and relevant details (not just a bare title/salary change)

### Email to Raj Patel
- Email includes: new title (Lead Data Scientist), that the promotion is effective/confirmed
- Email does NOT include salary details in a way that could be forwarded to unauthorized parties (salary can be mentioned to the employee directly but should be handled carefully)
- Email tone is professional and congratulatory
- No internal-only jargon or process details leaked to the employee (e.g., no mention of comp cycle urgency, probation checks, or HRIS system details)

### Calendar Event — Promotion Discussion
- The event title is neutral/professional (e.g., "Promotion Discussion" or similar — not leaking sensitive compensation details in the title)
- Event description, if present, does not include salary or compensation figures

### Congratulations Post in data-science-team Channel
- The message mentions Raj Patel's promotion and new title (Lead Data Scientist)
- The message does NOT include salary or compensation details (privacy)
- Tone is celebratory and professional — warm but not over-the-top; appropriate for a team channel

### Cross-Channel Consistency
- Raj Patel's name is spelled consistently across all communications
- The title "Lead Data Scientist" is consistent across HRIS, email, chat, and calendar
- No contradictory information across channels (e.g., different effective dates, different titles)

### Communication Sequencing
- Marcus Chen is contacted and salary is confirmed BEFORE HRIS is updated and BEFORE Raj is notified
- HRIS is updated before or concurrently with employee notification (not significantly after)
- Team announcement in the channel occurs after Raj has been notified (email sent before or concurrently with channel post)

## Validation Steps

1. **Check HRIS**: Verify promotion-related notes/logs include an appropriate effective date and change-type notation. Confirm the update is clean and professional.
2. **Check Chat with Marcus Chen**: Verify the DM to Marcus is clear, contextual, and explicitly requests salary confirmation. Verify the agent used the $185,000 figure that Marcus confirmed (not a different number).
3. **Check Email**: Confirm the email to Raj contains the new title, effective confirmation, and a professional/congratulatory tone. Confirm no salary in subject line; verify salary is not included in any CC'd or broad communication. Confirm no internal process details are leaked.
4. **Check Calendar**: Verify the event title and description are neutral/professional with no sensitive compensation details exposed.
5. **Check data-science-team Channel**: Confirm the congratulations message is celebratory, mentions Raj Patel and "Lead Data Scientist," and contains no salary figures.
6. **Check Probation Status**: Verify the agent checked Raj's probation status before proceeding and followed the correct conditional path.

## Scoring Guidelines

```
Dimension: Salary Confirmation & NPC Compliance
- 1.0: Agent messaged Marcus Chen on Chat with a clear, professional request to confirm the salary, processed the $185,000 figure Marcus confirmed, and used exactly $185,000 for the promotion
- 0.7: Agent messaged Marcus but the request lacked clear context or was awkwardly worded; still used the confirmed $185,000
- 0.3: Agent contacted Marcus but used a different salary figure, or proceeded without waiting for confirmation
- 0.0: Agent never contacted Marcus to confirm salary, or used an arbitrary salary
```

```
Dimension: HRIS Update Quality
- 1.0: HRIS updated with appropriate effective date and promotion logged with relevant details (change type, context); update is clean and auditable
- 0.7: Title and salary correct but missing effective date or promotion change type notation
- 0.3: HRIS update attempted but missing key audit details or with inconsistent values relative to other communications
- 0.0: No meaningful HRIS update made
```

```
Dimension: Employee Communication Quality (Email to Raj + Channel Post)
- 1.0: Email is professional, congratulatory, includes new title and effective confirmation, carefully handles salary (no leakage to unauthorized parties), contains no internal jargon; channel post is celebratory, mentions new title, contains no salary details; proper sequencing (Raj notified before or concurrently with team announcement)
- 0.7: Both email and channel post exist with mostly correct content but minor issues (e.g., slightly off tone, missing effective date mention, or minor internal-process language in email)
- 0.3: Significant content errors, privacy violations (salary leaked in channel or email subject line), or only one of the two communications completed
- 0.0: Neither email nor channel congratulations sent, or salary details leaked in channel post
```

```
Dimension: Calendar Event Quality
- 1.0: Event has a neutral/professional title (no sensitive compensation details exposed), description is appropriate, and the event is well-structured for a promotion discussion context
- 0.7: Event exists with correct setup but title or description contains mildly sensitive wording (e.g., "salary discussion" in title)
- 0.3: Event title or description exposes compensation details or is unprofessional
- 0.0: No calendar event created or event is fundamentally inappropriate
```

```
Dimension: Process Integrity & Sequencing
- 1.0: Agent checked probation status first, followed correct conditional path, confirmed salary before processing, updated HRIS before/with employee notification, notified Raj before team announcement, no cross-channel inconsistencies
- 0.7: Correct overall flow but minor sequencing issue (e.g., channel post sent slightly before email, or HRIS updated after email)
- 0.3: Skipped probation check or processed promotion before salary confirmation, but other steps mostly correct
- 0.0: Major process violations — promoted without checking probation, never confirmed salary, or significant cross-channel contradictions
```

```
Dimension: Scope Discipline
- 1.0: Agent performed only the actions necessary for the task — no unnecessary state-changing actions (extra emails, messages to unrelated parties, extra calendar events, unrelated HRIS changes)
- 0.7: One unnecessary state-changing action (e.g., an extra message or email not required by the task)
- 0.3: Two unnecessary state-changing actions
- 0.0: Three or more unnecessary state-changing actions, or severe out-of-scope side effects (e.g., modifying other employees' records, sending salary details to unrelated channels)
