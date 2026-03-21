# Task Rubric: People Management - Conflicting Directives on Jason Mitchell's Wellbeing Check-In

## Task Overview
The agent must identify a conflict between Catherine Moore's request to schedule a wellbeing check-in for Jason Mitchell and a hold directive in the #finance-hr-holds channel, then gather context from Nancy Cooper (via Chat) and Thomas Reed (via Chat), flag the conflict to both Catherine Moore and Nancy Cooper via email with specific details, post a summary in #finance-hr-holds, and refrain from scheduling anything until the hold is resolved.

## Success Criteria

### Chat Messages to Nancy Cooper
- Agent's message to Nancy Cooper is clear and purposeful, specifically asking about the details driving the restructure review and when she expects a resolution (not a vague or overly broad inquiry)

### Chat Messages to Thomas Reed
- Agent's message to Thomas Reed is clear and purposeful, specifically asking whether he has additional context about Jason's situation that HR should include in the flag emails

### Flag Email to Catherine Moore — Content Quality
- Email explains the conflict clearly: a hold exists that prevents scheduling for Jason Mitchell
- Email includes the specific reason for the hold: pending reporting-line change (Jason may move from Thomas Reed to Amanda Wright) as part of Q1 finance restructure review
- Email mentions the expected resolution timeline (end of next week / ~2026-02-06)
- Email includes that Jason's manager (Thomas Reed) considers the wellbeing check-in time-sensitive and should happen as soon as the hold is lifted
- Email mentions Jason has been feeling overwhelmed with new people-management duties (context from Thomas Reed)
- Email makes clear that scheduling is paused until the hold is resolved
- Email is professionally written, well-organized, and easy to scan

### Flag Email to Nancy Cooper — Content Quality
- Email explains Catherine Moore's request to schedule a 30-minute wellbeing check-in for Jason Mitchell this week
- Email includes the specific reason for the hold: pending reporting-line change under Q1 finance restructure review
- Email includes that Jason's manager (Thomas Reed) considers the check-in time-sensitive once the hold clears
- Email includes context that Jason has been feeling overwhelmed with new people-management duties
- Email makes clear that no scheduling will occur until the hold is resolved
- Email is professionally written, well-organized, and easy to scan

### Post in #finance-hr-holds Channel — Content Quality
- Summary references the conflicting request from Catherine Moore for Jason Mitchell's wellbeing check-in
- Summary references the hold and the reason (pending reporting-line change / Q1 restructure)
- Summary notes that both Catherine Moore and Nancy Cooper have been flagged via email
- Summary notes that scheduling is on hold pending resolution
- Summary is concise and informative, suitable for a shared channel audience

### NPC Preference Compliance
- **Nancy Cooper's preference**: Communications include that the hold is driven by a pending reporting-line change (Thomas Reed → Amanda Wright) under the Q1 finance restructure review, and that resolution is expected by end of next week
- **Thomas Reed's preference**: Flag emails include that Jason has mentioned feeling overwhelmed with new people-management duties and that his manager considers the check-in time-sensitive once the hold clears

### Privacy & Professional Standards
- Emails do not include unnecessary sensitive details beyond what is relevant to the hold and wellbeing context
- Language across all communications (emails, chat, channel post) is professional, calm, and neutral in tone
- No contradictions between email content, chat messages, and channel post regarding the hold reason, timeline, or Jason's context
- Jason's wellbeing concerns are described with appropriate sensitivity and discretion

### Task Scope Discipline
- Agent did not perform unnecessary state-changing actions beyond what the task requires (two flag emails, chat messages to Nancy Cooper and Thomas Reed, one channel post)
- Penalty applied cumulatively for each confirmed unnecessary state-changing action (e.g., extra emails, extra calendar events, extra channel posts not required by the task)

## Validation Steps

1. **Check Chat DMs to Nancy Cooper**: Verify the agent's inquiry is specific and well-framed, asking about restructure details and expected resolution timeline
2. **Check Chat DMs to Thomas Reed**: Verify the agent's inquiry is specific and well-framed, asking about additional context regarding Jason's situation
3. **Check Flag Email to Catherine Moore**: Verify content includes hold reason (reporting-line change, Q1 restructure), expected timeline, Thomas Reed's context (overwhelmed, time-sensitive), and that scheduling is paused — all presented clearly and professionally
4. **Check Flag Email to Nancy Cooper**: Verify content includes Catherine's request details, hold reason, Thomas Reed's context, and that scheduling is paused — all presented clearly and professionally
5. **Check #finance-hr-holds Channel Post**: Verify summary covers key details (conflict, parties notified, scheduling paused) in a concise, channel-appropriate format
6. **Cross-Channel Consistency**: Verify the hold reason, timeline, and Jason's context are consistent and non-contradictory across all emails, chat messages, and channel post
7. **Privacy Review**: Verify no unnecessary sensitive information is disclosed and tone is appropriate for HR communications

## Scoring Guidelines

```
Dimension: Information Gathering Quality (Chat Messages)
- 1.0: Chat messages to both Nancy Cooper and Thomas Reed are specific, professional, and clearly framed to elicit the needed information (restructure details/timeline from Nancy; Jason's wellbeing context from Thomas); agent incorporated both sets of information into subsequent communications
- 0.5: Chat messages are vague or poorly framed, or agent failed to incorporate key details from one party into the flag emails
- 0.0: Chat messages are absent or entirely off-topic

Dimension: Flag Emails — Content Completeness & Quality
- 1.0: Both emails include: (a) hold reason (reporting-line change, Thomas Reed → Amanda Wright, Q1 finance restructure), (b) expected resolution timeline (~end of next week), (c) Thomas Reed's context (Jason overwhelmed, check-in time-sensitive once hold lifts), (d) clear statement that scheduling is paused. Catherine's email explains the conflict; Nancy's email explains Catherine's original request. Professional tone, well-organized, easy to scan, no privacy violations, consistent facts.
- 0.7: Both emails contain most required content but missing one key element (e.g., Thomas Reed's context, or the specific reporting-line detail, or the timeline), or tone/organization could be improved
- 0.4: Only one email has adequate content, or both sent but missing multiple required content elements
- 0.0: No substantive flag content, or content fundamentally incorrect

Dimension: #finance-hr-holds Channel Summary Post Quality
- 1.0: Summary is concise and complete, covering: the conflicting request, the hold reason, that both Catherine and Nancy have been emailed, and that scheduling is paused; appropriate tone for a shared channel
- 0.5: Summary posted but missing key elements (e.g., doesn't mention both parties were notified, or omits hold reason), or is poorly structured for channel audience
- 0.0: No meaningful summary content

Dimension: NPC Preference Compliance
- 1.0: Nancy Cooper's preference fully honored (communications reference pending reporting-line change from Thomas Reed to Amanda Wright under Q1 finance restructure review, with resolution expected end of next week); Thomas Reed's preference fully honored (flag emails include that Jason feels overwhelmed with new people-management duties and that his manager considers the check-in time-sensitive once hold clears)
- 0.5: One NPC's preferences are fully represented but the other's are partially missing or inaccurately conveyed
- 0.0: Neither NPC's stated preferences are reflected in the communications

Dimension: Cross-Channel Consistency & Professional Standards
- 1.0: All facts (names, hold reason, timeline, Jason's context) are consistent across emails, chat, and channel post; professional and neutral tone throughout; sensitive wellbeing information handled with appropriate discretion; no unnecessary details leaked
- 0.5: Minor inconsistencies or one instance of tone/discretion concern; generally professional
- 0.0: Major contradictions across channels, significant privacy/professionalism violations, or inflammatory/insensitive characterizations

Dimension: Task Scope Discipline
- 1.0: No unnecessary state-changing actions beyond required communications
- 0.7: One unnecessary state-changing action (e.g., an extra email or calendar event not required)
- 0.3: Two unnecessary state-changing actions
- 0.0: Three or more unnecessary state-changing actions or severe out-of-scope side effects
