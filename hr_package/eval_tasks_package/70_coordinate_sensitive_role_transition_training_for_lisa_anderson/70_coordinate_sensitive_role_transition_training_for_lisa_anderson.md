# Task Rubric: People Management - Coordinate Sensitive Role Transition Training for Lisa Anderson

## Task Overview
The agent must coordinate Lisa Anderson's role transition from Onboarding Specialist to Recruiting Coordinator in Talent Acquisition by: (1) sending David Thompson an empathetic acknowledgment email, (2) scheduling a 30-minute transition planning meeting between David Thompson and Michael Chen this week, (3) gathering training module requirements from Sarah Johnson and Michael Chen via chat, and (4) emailing Lisa Anderson the complete combined list of training modules.

## Success Criteria

### Explicit Requirements

**Email to David Thompson:**
- An email was sent to david.thompson@amazon.com
- The email expresses empathy/understanding regarding losing Lisa mid-cycle
- The email thanks David for his support during the handoff/transition
- The tone is professional and warm, acknowledging his frustration or concern

**Calendar: Transition Planning Meeting:**
- A 30-minute calendar event is scheduled between David Thompson and Michael Chen
- The meeting occurs during the week of 2026-02-01 (i.e., between Feb 1–7, 2026, given Sunday start, or Feb 2–6 for business days)
- Both david.thompson@amazon.com and michael.chen@amazon.com are invited/attendees
- The meeting description or title relates to transition planning for Lisa Anderson's role change

**Chat with Sarah Johnson:**
- The agent sent a chat message to Sarah Johnson asking for the list of training modules Lisa needs
- Sarah Johnson's response was received containing: Recruiting Compliance Fundamentals, Interviewing Best Practices, Diversity Sourcing Strategies, and Offer Letter Processing

**Chat with Michael Chen:**
- The agent sent a chat message to Michael Chen asking whether he has additional onboarding requirements for Lisa's new role
- Michael Chen's response was received containing: ATS Power User Certification and Candidate Experience Standards Training

**Email to Lisa Anderson:**
- An email was sent to lisa.anderson@amazon.com
- The email contains ALL six training modules combined from both Sarah Johnson and Michael Chen:
  1. Recruiting Compliance Fundamentals
  2. Interviewing Best Practices
  3. Diversity Sourcing Strategies
  4. Offer Letter Processing
  5. ATS Power User Certification
  6. Candidate Experience Standards Training
- No modules are missing from the combined list
- The email clearly communicates that these are required training modules for her new role as Recruiting Coordinator in Talent Acquisition

### NPC Preference Compliance
- Sarah Johnson's four training modules are all included in the final email to Lisa
- Michael Chen's two additional requirements (ATS Power User Certification and Candidate Experience Standards Training) are all included in the final email to Lisa
- Both sets of requirements are treated as equally valid and combined (no authority conflict here — Sarah is VP and Michael is a manager, but their requirements are additive, not conflicting)

### Implicit Professional Standards
- **Correct sequencing**: The agent gathered training requirements from both Sarah Johnson and Michael Chen BEFORE emailing Lisa Anderson the training list (not the other way around)
- **HRIS update**: Lisa Anderson's HRIS record should be updated to reflect her new role (Recruiting Coordinator), new department/team (Talent Acquisition under Michael Chen), or at minimum a note about the transition — role transitions must be reflected in the system of record
- **Cross-channel consistency**: Lisa's name, role title, and training module names are consistent across all communications (chat, email, calendar)
- **Privacy/audience awareness**: The email to Lisa does not include internal deliberation details, David Thompson's upset feelings, or other sensitive context she shouldn't see
- **Contact verification**: Emails were sent to the correct addresses per HRIS records (david.thompson@amazon.com, lisa.anderson@amazon.com)
- **Inbox check**: The agent should have checked for David Thompson's incoming email expressing upset about losing Lisa

## Validation Steps

1. **Check email to David Thompson**: Verify an email exists sent to david.thompson@amazon.com. Confirm it contains empathetic language and thanks him for support during the handoff.

2. **Check calendar event**: Verify a calendar event exists with 30-minute duration, scheduled between Feb 2–6, 2026 (business days this week). Confirm both david.thompson@amazon.com and michael.chen@amazon.com are attendees. Confirm the event title/description references transition planning or Lisa Anderson.

3. **Check chat with Sarah Johnson**: Verify a chat message was sent to Sarah Johnson asking about training modules. Verify the agent received her response listing four modules.

4. **Check chat with Michael Chen**: Verify a chat message was sent to Michael Chen asking about additional onboarding requirements. Verify the agent received his response listing two additional modules.

5. **Check email to Lisa Anderson**: Verify an email exists sent to lisa.anderson@amazon.com. Confirm ALL six training modules are listed. Confirm the email provides context about her new role.

6. **Check HRIS**: Verify Lisa Anderson's record has been updated to reflect the role change (new title, new manager/reporting line, or transition notes).

7. **Verify sequencing**: Confirm that the chat messages to Sarah Johnson and Michael Chen were sent BEFORE the email to Lisa Anderson was sent.

## Scoring Guidelines

```
Dimension: Email to David Thompson (Empathetic Acknowledgment)
- 1.0: Email sent to correct address with empathetic tone, acknowledgment of the difficulty of losing Lisa mid-cycle, and explicit thanks for his support during the handoff. Professional and warm.
- 0.7: Email sent to correct address with thanks but lacks genuine empathy about the mid-cycle disruption, or is overly formulaic.
- 0.3: Email sent but is perfunctory, missing either empathy or thanks, or sent to wrong address.
- 0.0: No email sent to David Thompson.
```

```
Dimension: Calendar Meeting (Transition Planning)
- 1.0: 30-minute meeting scheduled with both David Thompson and Michael Chen as attendees, occurring on a business day during the week of Feb 1-7 2026, with clear title/description referencing the transition.
- 0.7: Meeting scheduled with both correct attendees but wrong duration, or title is vague/missing context about the transition, or slightly outside the specified week.
- 0.3: Meeting created but missing one attendee, or significantly wrong duration, or scheduled outside the week.
- 0.0: No meeting scheduled.
```

```
Dimension: Information Gathering via Chat & Training Email to Lisa
- 1.0: Agent chatted with Sarah Johnson to get the 4 training modules AND chatted with Michael Chen to get his 2 additional requirements BEFORE emailing Lisa. The email to Lisa at lisa.anderson@amazon.com contains all 6 modules clearly listed, with appropriate context about her new role. No internal-only or sensitive information leaked in Lisa's email.
- 0.7: Agent gathered from both sources and emailed Lisa, but 1 module is missing or slightly misnamed, OR sequencing was partially off (e.g., emailed Lisa before one chat response came back), OR email lacks clear role context.
- 0.3: Agent contacted only one of the two sources (Sarah or Michael) and emailed Lisa an incomplete list, OR emailed Lisa without chatting with either source first.
- 0.0: No email sent to Lisa, or no chat messages sent to gather training requirements.
```

```
Dimension: HRIS Update & Professional Standards
- 1.0: Lisa Anderson's HRIS record is updated to reflect her new role (Recruiting Coordinator), new reporting line (Michael Chen), or at minimum a documented note about the transition. Contact information was verified from HRIS. Cross-channel consistency maintained.
- 0.5: Partial HRIS update (e.g., note added but role/title not changed), or HRIS not updated but all other professional standards met (correct addresses, consistent information, proper sequencing).
- 0.0: No HRIS update attempted and other professional standards (e.g., wrong email addresses, inconsistent information) also violated.
