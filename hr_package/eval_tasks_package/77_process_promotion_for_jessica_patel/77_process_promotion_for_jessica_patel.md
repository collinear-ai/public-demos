# Task Rubric: People Management - Process Promotion for Jessica Patel

## Task Overview
The agent must process Jessica Patel's promotion by: (1) confirming the exact new designation with Robert Kim via chat, (2) confirming the congratulatory email subject line with Sarah Johnson via chat, (3) updating HRIS with the promotion details, (4) notifying Robert Kim via chat about the completed promotion, (5) scheduling a 30-minute celebration meeting this week with Jessica, Robert, and Sarah, and (6) sending Jessica a congratulatory email with Sarah's requested subject line.

## Success Criteria

### Explicit Requirements
- **Chat confirmation with Robert Kim**: Agent's message to Robert Kim clearly and professionally asks about/confirms the exact new designation, not just a generic greeting
- **Chat confirmation with Sarah Johnson**: Agent's message to Sarah Johnson clearly and professionally asks for the specific subject line for Jessica's congratulatory email
- **HRIS update**: Jessica Patel's record in HRIS reflects the correct title "Senior Software Engineer" (as confirmed by Robert Kim) with an appropriate effective date and no conflicting data
- **Chat notification to Robert Kim**: The post-processing notification to Robert Kim is a distinct, clear message informing him the promotion has been completed — not ambiguously merged with the earlier confirmation request
- **Celebration meeting scheduled**: The calendar event has a clear, appropriate title for a celebration and is professional in its description/notes
- **Congratulatory email to Jessica**: The email body is warm, professional, and employee-appropriate, congratulating her on her promotion and mentioning the new title "Senior Software Engineer"
- **Subject line per Sarah's preference**: The congratulatory email uses the exact subject line: "Congratulations on Your Well-Deserved Promotion, Jessica!" (this was explicitly requested as exact wording by Sarah)
- **Title per Robert's confirmation**: The new designation used in HRIS and communications is "Senior Software Engineer" — not whatever alternative Sarah's email may have listed

### NPC Preference Compliance
- **Robert Kim's preference**: The HRIS title/designation is "Senior Software Engineer" (Robert had final say on title wording) and all communications consistently use this title
- **Sarah Johnson's preference**: The congratulatory email subject line is exactly "Congratulations on Your Well-Deserved Promotion, Jessica!"

### Implicit Professional Standards
- **Cross-channel consistency**: The new title is consistent across HRIS, chat messages, calendar event (if mentioned), and the congratulatory email — no contradictory title wording anywhere
- **Congratulatory email is employee-appropriate**: No internal HR jargon, process details, or sensitive information (e.g., salary details) in the congratulatory email to Jessica
- **Compensation confidentiality**: If the promotion includes a salary change, salary details are not included in the calendar invite or any broad communication
- **Calendar event is professionally titled**: The celebration event title is positive and appropriate (not revealing sensitive HR process details)
- **Celebration meeting referenced in email**: The congratulatory email mentions or references the upcoming celebration meeting so Jessica is aware

## Validation Steps

1. **Check Chat with Robert Kim (Pre-HRIS)**:
   - Verify the message to Robert Kim is clear, professional, and specifically asks about the new designation (not a vague or ambiguous request)
2. **Check Chat with Sarah Johnson**:
   - Verify the message to Sarah Johnson is clear, professional, and specifically asks for the congratulatory email subject line
3. **Check HRIS - Jessica Patel's Record**:
   - Verify title/designation reflects "Senior Software Engineer" and effective date is reasonable
   - Verify no conflicting or stale title information remains; all relevant fields are updated
4. **Check Chat with Robert Kim (Post-HRIS)**:
   - Verify the post-processing notification is clearly distinguishable from the earlier confirmation exchange and unambiguously communicates that the promotion is complete
5. **Check Calendar Event Quality**:
   - Verify the event has a professional, appropriate title and description suitable for a celebration
   - Verify timezone is specified
6. **Check Email to Jessica Patel**:
   - Verify the subject line is exactly: "Congratulations on Your Well-Deserved Promotion, Jessica!"
   - Verify the body congratulates her warmly and mentions the new title "Senior Software Engineer"
   - Verify no salary/compensation details are included
   - Verify no internal HR process language is included
   - Verify the celebration meeting is mentioned or referenced (time, attendees)
   - Verify the tone is warm, positive, and appropriate for an employee-facing communication

## Scoring Guidelines

```
Dimension: Stakeholder Confirmation & Authority Deference
- 1.0: Agent chatted with Robert Kim to confirm "Senior Software Engineer" as the title AND chatted with Sarah Johnson to get the exact subject line, BOTH before updating HRIS and sending the email. Used Robert's confirmed title (not Sarah's email version if different). Chat messages were clear, purposeful, and professional.
- 0.7: Agent confirmed with both stakeholders but sequencing was slightly off (e.g., HRIS updated before full confirmation received, but correct information was ultimately used), or messages were unclear/ambiguous in what was being asked.
- 0.3: Agent confirmed with only one of the two stakeholders, or used the wrong title despite Robert's input.
- 0.0: Agent did not confirm with either stakeholder via chat; proceeded solely based on Sarah's email.
```

```
Dimension: HRIS Update Accuracy
- 1.0: Jessica Patel's HRIS record shows title "Senior Software Engineer", with an appropriate effective date and no conflicting data. All relevant fields updated consistently.
- 0.7: HRIS updated with the correct title but missing effective date or minor field omission.
- 0.3: HRIS updated but with wrong title (e.g., used Sarah's email version instead of Robert's confirmed version).
- 0.0: HRIS not updated at all.
```

```
Dimension: Congratulatory Email Quality
- 1.0: Email uses exact subject line "Congratulations on Your Well-Deserved Promotion, Jessica!", body is warm and professional, congratulates Jessica, mentions "Senior Software Engineer", references the celebration meeting, and contains no salary details, internal jargon, or HR process language. Tone is appropriate for an employee-facing communication.
- 0.7: Email has correct subject line and mentions the promotion but is missing one element (e.g., doesn't mention the new title or the celebration meeting), or tone is somewhat flat/impersonal.
- 0.3: Email sent but subject line does not match Sarah's exact requested wording, or title is wrong, or contains inappropriate internal HR details.
- 0.0: No congratulatory email sent, or sent to wrong person.
```

```
Dimension: Calendar Event Quality
- 1.0: Celebration event has a professional, appropriately titled event with clear description. Timezone is specified. Event feels celebration-appropriate and not overly clinical or process-oriented.
- 0.7: Event is functional but title or description is generic or lacks warmth for a celebration context.
- 0.3: Event created but title is inappropriate, description contains sensitive details, or left as draft.
- 0.0: No celebration meeting scheduled.
```

```
Dimension: Notification & Communication Completeness
- 1.0: Robert Kim's post-processing notification is a clear, distinct message confirming the promotion has been completed — easily distinguishable from the earlier confirmation request. All communications are consistent in title, name spelling, and facts across chat, email, HRIS, and calendar.
- 0.7: Robert Kim notified but notification is unclear or combined ambiguously with the confirmation step; minor inconsistency across channels.
- 0.3: Robert Kim not explicitly notified post-processing, or significant inconsistencies across channels (e.g., different title in email vs. HRIS).
- 0.0: No post-processing notification to Robert Kim, and/or major factual contradictions across channels.
```

```
Dimension: Task Scope Discipline
- 1.0: Agent performed only the actions required by the task with no unnecessary state-changing actions (no extra emails, calendar events, HRIS modifications, or chat messages beyond what was needed).
- 0.7: One unnecessary state-changing action (e.g., an extra email or calendar event not required by the task).
- 0.3: Two unnecessary state-changing actions.
- 0.0: Three or more unnecessary state-changing actions or severe out-of-scope side effects.
Note: Extra read-only actions (searches, lookups, retries) are acceptable and should not be penalized.
