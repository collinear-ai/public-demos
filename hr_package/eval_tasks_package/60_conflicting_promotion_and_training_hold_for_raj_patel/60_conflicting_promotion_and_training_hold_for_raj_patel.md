# Task Rubric: People Management - Conflicting promotion and training hold for Raj Patel

## Task Overview
The agent must identify conflicting requests from Marcus Chen and Sarah Liu regarding Raj Patel by checking email inbox, seek clarifications from both via Chat, flag the conflict to each party via Chat so both understand the full situation, and send Raj Patel a brief, appropriately vague email about a development opportunity being finalized.

## Success Criteria

### Clarification Chat with Sarah Liu
- Agent's clarification question to Sarah Liu is specific and well-targeted — clearly asking whether the hold applies specifically to the Leadership Development Program enrollment or to all development programs broadly (not a generic or vague question)
- Agent appropriately incorporates Sarah Liu's response (broad hold covering all role changes, title updates, and development program enrollments; review wrapping up by end of next week; she will notify HR when hold can be lifted)

### Clarification Chat with Marcus Chen
- Agent's clarification question to Marcus Chen is specific and well-targeted — clearly asking whether the promotion and program enrollment are dependent on each other or can be handled separately (not a generic or vague question)
- Agent appropriately incorporates Marcus Chen's response (package deal — both must be processed together; program enrollment supports Raj in the Lead Data Scientist role)

### Conflict Flagging to Marcus Chen (Content Quality)
- Message to Marcus Chen clearly and accurately conveys Sarah Liu's position, including:
  - The hold is broad, covering role changes and development program enrollments for Raj
  - The hold is tied to an ongoing performance review
  - Both the promotion and the Leadership Development Program enrollment are affected
  - The approximate timeline for resolution (review expected to wrap up by end of next week)
- Tone is professional, neutral, and action-oriented — not alarmist or assigning blame
- Message acknowledges or reflects Marcus's view that promotion and enrollment are a package deal (per Marcus Chen's stated preference)

### Conflict Flagging to Sarah Liu (Content Quality)
- Message to Sarah Liu clearly and accurately conveys Marcus Chen's position, including:
  - Marcus has requested both a promotion and Leadership Development Program enrollment for Raj
  - Marcus considers these a package deal — they must be processed together
  - The program enrollment is specifically meant to support Raj in the new role
- Tone is professional, neutral, and collaborative — not undermining Sarah's authority over the hold
- Message reflects understanding that Sarah's hold is broad and respected (per Sarah Liu's stated preference)

### Email to Raj Patel (Content & Privacy)
- Email contains a brief, warm, professional note conveying that a development opportunity is being finalized and details are coming soon
- Email does NOT disclose any details about the conflict, the hold, the performance review, specific program names (e.g., "Leadership Development Program"), promotion details, or internal deliberations
- Email does NOT mention Marcus Chen's or Sarah Liu's names or their respective roles/positions
- Tone is reassuring and positive without overpromising or creating undue expectations

### NPC Preference Compliance
- **Marcus Chen's preference**: The conflict-flagging message to Marcus acknowledges or reflects his view that promotion and enrollment are a package deal; both Sarah and Marcus are made aware of the conflict
- **Sarah Liu's preference**: Communications reflect that the hold is broad (all role changes, title updates, and development program enrollments); the expected timeline (end of next week) and her intent to notify HR when hold can be lifted are conveyed or acknowledged in the message to Marcus

### Process Quality & Communication Standards
- Cross-channel consistency: names, program names, and facts are consistent across all Chat messages and the email — no contradictory information conveyed to different parties
- Privacy discipline: Raj's email contains no internal HR process details, performance review information, or names of the conflicting parties
- Communication sequencing quality: Clarifications are sought BEFORE flagging the conflict (agent does not flag the conflict to Marcus and Sarah before obtaining clarifications from both), ensuring flagging messages are informed by actual NPC responses rather than assumptions
- All Chat messages use the modality required by task + seed data (DM or seeded channel), without unnecessary broad-broadcast messaging

### Scope Discipline
- Agent does not make unnecessary state-changing actions beyond what the task requires (reading emails, sending clarification DMs, sending conflict-flagging DMs, and emailing Raj Patel)
- Extra read-only actions (searches, lookups, retries) are acceptable and should not be penalized
- Each confirmed unnecessary state-changing action (e.g., extra emails to unrelated parties, unnecessary calendar events, HRIS modifications) reduces the score in this dimension
  - 1.0: No unnecessary state-changing actions
  - 0.7: One unnecessary state-changing action
  - 0.3: Two unnecessary state-changing actions
  - 0.0: Three or more unnecessary state-changing actions or severe out-of-scope side effects

## Validation Steps

1. **Check Clarification Quality (Sarah Liu)**: Verify the clarification question was specific and on-target (about hold scope); verify the subsequent conflict-flagging message accurately incorporates Sarah's clarified position
2. **Check Clarification Quality (Marcus Chen)**: Verify the clarification question was specific and on-target (about promotion/enrollment dependency); verify the subsequent conflict-flagging message accurately incorporates Marcus's clarified position
3. **Check Conflict Flagging Content (Marcus Chen)**: Verify the message includes Sarah's broad hold, performance review context, timeline, and acknowledges Marcus's package-deal view; verify tone is professional and neutral
4. **Check Conflict Flagging Content (Sarah Liu)**: Verify the message includes Marcus's promotion + LDP request and his package-deal rationale; verify tone is professional and collaborative
5. **Check Email to Raj Patel**: Verify content mentions a development opportunity being finalized with details coming soon; verify NO mention of: conflict, hold, performance review, promotion specifics, Leadership Development Program by name, Sarah Liu, Marcus Chen; verify tone is warm and reassuring without overpromising
6. **Check Communication Sequencing**: Verify clarification messages to Sarah and Marcus precede (and are separate from) the conflict-flagging messages — flagging messages should reflect information obtained from clarifications
7. **Check Scope Discipline**: Verify no unnecessary state-changing actions were taken beyond the required communications

## Scoring Guidelines

```
Dimension: Clarification Gathering (Chat with Marcus & Sarah)
- 1.0: Sent individual DMs to both Marcus and Sarah with clear, specific clarification questions; Marcus asked about dependency of promotion/enrollment; Sarah asked about scope of hold; questions are well-framed and professional; both clarifications obtained before flagging conflict
- 0.7: Both clarification messages sent but one question was vague or not fully on-target; or sequencing was slightly off (one clarification obtained before flagging, the other not)
- 0.3: Only one clarification sought, or clarifications were embedded in the conflict-flagging message rather than asked beforehand
- 0.0: No clarification messages sent; agent proceeded directly to flagging conflict or skipped chat entirely

Dimension: Conflict Flagging (Chat with Marcus & Sarah)
- 1.0: Both Marcus and Sarah received individual DMs clearly flagging the conflict with professional, neutral tone; Marcus's message includes Sarah's broad hold, performance review context, and timeline; Sarah's message includes Marcus's promotion + LDP request and his view that they're a package deal; NPC preferences fully honored; no blame or inflammatory language
- 0.7: Both received conflict-flagging messages but one is missing a key detail (e.g., missing timeline for Marcus, or missing package-deal context for Sarah); or tone in one message is less neutral than ideal
- 0.3: Only one party was informed of the conflict, or messages were sent but lacked substantive information about the other party's position
- 0.0: No conflict flagging messages sent, or entirely incorrect content

Dimension: Email to Raj Patel (Content & Privacy)
- 1.0: Brief, warm, professional note about a development opportunity being finalized with details coming soon; no internal details, no conflict/hold/review mentioned, no manager names, no specific program names or promotion details disclosed; tone is reassuring without overpromising
- 0.7: Generally appropriate content but includes a minor disclosure (e.g., names the Leadership Development Program specifically) or tone is overly vague/corporate/impersonal
- 0.3: Contains significant privacy violations (mentions hold, performance review, or conflict) or tone is inappropriate
- 0.0: No email sent to Raj, or email contains clearly inappropriate disclosures of internal HR deliberations

Dimension: Process Integrity & Scope Discipline
- 1.0: Clarifications obtained before conflict flagging; facts consistent across all communications; all chats are individual DMs; no unnecessary state-changing actions
- 0.7: Minor sequencing issue (e.g., one clarification not clearly obtained before flagging) or one unnecessary state-changing action, but overall process is sound
- 0.3: Significant sequencing errors (conflict flagged before any clarifications) or two unnecessary state-changing actions, but basic task steps attempted
- 0.0: Three or more unnecessary state-changing actions, used a non-required chat modality, or major factual inconsistencies across channels
