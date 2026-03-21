# Task Rubric: People Management - Coordinate Sensitive Cross-Department Leadership Training for Role Transitions

## Task Overview
The agent must handle a sensitive request from Robert Kim regarding Emma Thompson's readiness for a management role. This involves gathering information from Rachel Foster and Victoria Wells, scheduling two calendar events with specific framing, providing Rachel with context about cross-department friction, and responding to Robert with an acknowledgment of his concerns and information about targeted coaching — all while maintaining a supportive, non-judgmental tone about employee advancement.

## Success Criteria

### Information Gathering
- Agent's outreach to Rachel Foster is professional and clearly asks about the specific coaching support Emma needs (not vague or presumptive)
- Agent's outreach to Victoria Wells is professional and clearly asks how the alignment discussion with Robert should be framed
- Agent waits for and meaningfully incorporates Rachel's and Victoria's responses before taking downstream actions (events, messages), rather than proceeding with assumptions

### Calendar Events — Quality of Content & Framing
- **Leadership Development Session**: The session description substantively includes all three of Rachel Foster's requested focus areas: (1) understanding engineering sprint cadences, (2) establishing shared KPIs across design and engineering, (3) building credibility through technical empathy — not just listed perfunctorily but described in a way that would be useful context for attendees
  - The event title and description use supportive, developmental framing — language should convey growth opportunity, not remediation, performance concern, or deficiency
  - The description is professional and clear enough that attendees understand the session's purpose without revealing the complaint origin
- **Cross-Team Collaboration Alignment**: The description meaningfully incorporates Victoria Wells's preferred framing — mentioning how engineering leadership can better support cross-functional program transitions and establish clear handoff protocols
  - The description reads as a constructive, forward-looking collaboration discussion rather than a complaint response or confrontation

### Chat Message to Rachel Foster
- The chat DM to Rachel Foster clearly communicates that the coaching needs relate to cross-department friction, giving her enough actionable context to tailor the session effectively
- The message is concise and professional — it provides the friction context without over-sharing internal HR deliberations, Robert's complaint, or sensitive details about Emma's perceived shortcomings

### Response to Robert Kim
- The response to Robert Kim:
  - Acknowledges his concerns about Emma in a way that validates his input without amplifying negativity
  - Informs him that leadership is implementing targeted coaching to improve cross-departmental collaboration
  - Maintains a supportive tone regarding Emma's advancement — does not disparage Emma or frame the coaching as remedial/punitive
  - Does NOT reveal that Robert's specific complaint triggered the coaching (maintains sensitivity about the causal chain)
  - Is professional and reassuring, conveying that the situation is being handled constructively

### Privacy & Sensitivity
- Communications to/about Emma Thompson do not reveal that Robert raised concerns about her readiness
- The Leadership Development Session calendar invite does not contain language suggesting Emma is underperforming or not ready (no terms like "performance concern," "remedial," "not ready," etc.)
- No internal HR deliberation details are shared with Emma
- All chat messages are sent as individual DMs

### Cross-Channel Consistency
- Names are spelled consistently across all communications
- Dates and times referenced in chat/email match the calendar events
- Meeting purposes described in messages align with calendar event descriptions — no contradictory framing across channels

### Scope Discipline
- The agent stays within the scope of the task and does not perform unnecessary state-changing actions beyond what is required (two calendar events, chat DM to Rachel, response to Robert, and necessary outreach to Rachel and Victoria)
- Extra read-only actions (lookups, searches, retries) are acceptable and should not be penalized
- Each confirmed unnecessary state-changing action (extra emails, messages, calendar events, or updates not required by the task) reduces the score in this dimension

## Validation Steps

1. **Check Information Gathering Quality**: Verify that outreach to Rachel and Victoria was professional, clearly scoped, and that their responses were incorporated into downstream actions
2. **Check Calendar — Leadership Development Session Description Quality**: Confirm the description substantively covers all three of Rachel's focus areas and uses supportive/developmental framing with no hint of performance concerns
3. **Check Calendar — Cross-Team Collaboration Alignment Description Quality**: Confirm the description incorporates Victoria's preferred framing about cross-functional program transitions and handoff protocols
4. **Check Chat with Rachel Foster**: Verify the DM mentions cross-department friction as context, is actionable, and does not over-share sensitive details
5. **Check Response to Robert Kim**: Verify the message acknowledges concerns, mentions targeted coaching for cross-departmental collaboration, uses supportive/professional tone, and does not reveal that his complaint triggered the coaching
6. **Privacy Check**: Review all Emma-facing communications for any leaked information about Robert's concerns or language suggesting performance deficiency
7. **Cross-Channel Consistency Check**: Verify names, dates, and meeting framing are consistent across all communications
8. **Scope Discipline Check**: Confirm no unnecessary state-changing actions were taken beyond what the task requires

## Scoring Guidelines

```
Dimension: Information Gathering & Stakeholder Engagement
- 1.0: Agent contacts both Rachel Foster and Victoria Wells with clear, professional outreach, receives their preferences, and fully incorporates them into subsequent actions (all 3 of Rachel's focus areas in the session description; Victoria's exact framing and description content in the alignment meeting)
- 0.7: Agent contacts both but only partially incorporates their stated preferences (e.g., 1-2 of Rachel's focus areas, or Victoria's handoff protocols language is absent)
- 0.3: Agent contacts only one of the two stakeholders, or contacts both but largely ignores their responses in downstream actions
- 0.0: Agent does not reach out to either Rachel or Victoria before taking action

Dimension: Calendar Event Content Quality & NPC Preferences
- 1.0: Both event descriptions are substantive, professional, and fully incorporate NPC preferences — Rachel's 3 focus areas are clearly articulated in the Leadership session; Victoria's framing about cross-functional transitions and handoff protocols is present in the Alignment meeting; titles and descriptions use appropriate, constructive framing
- 0.7: Both events exist with generally appropriate framing but descriptions are missing some NPC-requested content or are somewhat generic/thin
- 0.3: Descriptions are largely missing NPC-requested content, or framing is inappropriate (e.g., hints at performance issues)
- 0.0: No meaningful event descriptions, or descriptions fundamentally misrepresent the meetings' purposes

Dimension: Pre-Session Context to Rachel & Response to Robert
- 1.0: Chat DM to Rachel clearly mentions cross-department friction with enough context to be actionable; response to Robert acknowledges concerns, mentions targeted coaching for cross-departmental collaboration, and maintains a supportive, reassuring tone about Emma's development without revealing the complaint triggered the coaching
- 0.7: Both communications exist but one is missing key content (e.g., Rachel's message is vague about friction, or Robert's response doesn't mention coaching) or tone is somewhat clinical/impersonal
- 0.3: Only one of the two communications contains meaningful content, or both are significantly incomplete
- 0.0: Neither communication sent with meaningful content

Dimension: Sensitivity, Privacy & Professional Framing
- 1.0: Emma-facing communications use developmental/supportive framing with no hint of performance concern or complaint origin; Robert's complaint is not revealed to Emma; no internal HR context leaked; chat modality follows task + seed data; consistent professional framing across all channels
- 0.7: Generally appropriate framing but minor sensitivity lapse (e.g., slightly clinical language in Emma's invite that could be read as evaluative, or minor inconsistency across channels)
- 0.3: Significant privacy or sensitivity breach (e.g., Emma's invite hints at concerns, or Robert is told details that should remain internal, or framing across channels is contradictory)
- 0.0: Major breach — Emma is told Robert complained, or calendar invite explicitly references performance concerns, or confidential details widely shared

Dimension: Scope Discipline
- 1.0: No unnecessary state-changing actions beyond the required communications and calendar events
- 0.7: One unnecessary state-changing action (e.g., an extra email or calendar event not required by the task)
- 0.3: Two unnecessary state-changing actions
- 0.0: Three or more unnecessary state-changing actions or severe out-of-scope side effects
