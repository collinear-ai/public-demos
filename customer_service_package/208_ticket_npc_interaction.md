# Task Rubric: Test multi-customer ticket triage with engineering escalation

## Overview

Test the agent's ability to perform priority-based triage across two simultaneous customer issues of different severity and tier, coordinate an engineering escalation for the critical issue, and maintain complete audit trails in both tickets. This verifies cross-system integration (Helpdesk + Chat), priority judgment, engineering coordination, and multi-customer management under pressure.

## Success Criteria

### Enterprise Ticket (david.park — Urgent)
- Ticket created with exact subject 'API 500 Errors - Bulk Import Failure', priority 'Urgent', linked to david.park@parkindustries.com
- Ticket status set to 'In Progress' with comment 'Critical enterprise issue - immediate investigation'
- Agent messages david.park asking for error details (timestamps, payload sizes, endpoint URLs)
- David responds with technical details; agent updates ticket with this information
- Agent escalates to marcus.chen via Rocket.Chat with a well-prepared technical escalation including reproduction steps
- Marcus responds with timeline/assessment; agent updates ticket with engineering response
- Agent messages david.park with the engineering update and expected timeline
- Ticket comments form a complete audit trail: initial report → investigation → customer details → engineering escalation → engineering response → customer update

### SMB Ticket (alex.thompson — Medium)
- Ticket created with exact subject 'Dashboard Performance Issue', priority 'Medium', linked to alex.thompson@thompsondesign.co
- Ticket status set to 'Open' with comment 'Monitoring - non-critical performance report'
- Agent messages alex.thompson asking which dashboards are affected
- Alex responds with details; agent updates ticket with this information

### Triage & Cross-System Integration
- Enterprise ticket is handled first (agent starts with david.park before alex.thompson)
- Both tickets contain cross-references to their Rocket.Chat conversations (room IDs or conversation summaries in comments)
- Enterprise ticket shows the full escalation chain in comments
- Priority assignment reflects customer tier: Urgent for Enterprise, Medium for SMB

## Validation Steps

1. Verify ticket exists with subject 'API 500 Errors - Bulk Import Failure' for david.park@parkindustries.com
2. Verify enterprise ticket priority is 'Urgent' and status is 'In Progress'
3. Verify enterprise ticket has initial investigation comment
4. Verify DM history with david.park shows agent asking for details and David responding
5. Verify enterprise ticket was updated with David's additional technical details
6. Verify DM history with marcus.chen shows a technical escalation with reproduction steps and Marcus responding
7. Verify enterprise ticket was updated with Marcus's engineering response/timeline
8. Verify DM history with david.park shows agent relaying engineering update
9. Verify ticket exists with subject 'Dashboard Performance Issue' for alex.thompson@thompsondesign.co
10. Verify SMB ticket priority is 'Medium' and status is 'Open'
11. Verify DM history with alex.thompson shows agent asking for details and Alex responding
12. Verify SMB ticket was updated with Alex's response details
13. Verify enterprise ticket was created/handled before SMB ticket (timestamp check)
14. Verify both tickets have chat conversation references in their comments
15. Verify enterprise ticket comments form a complete audit trail (at least 4 distinct comment entries documenting the full lifecycle)

## Testing Requirements

- Use helpdesk tool server to retrieve both tickets and their comments
- Use Rocket.Chat tool server to retrieve DM histories with david.park, alex.thompson, and marcus.chen
- Compare ticket creation timestamps to verify priority-based triage ordering
- Analyze ticket comments for completeness of audit trail and cross-references
- Analyze engineering escalation message quality (should contain reproduction steps, not vague descriptions)

## Quality Criteria

- Enterprise ticket must reflect urgency in language and response speed
- Engineering escalation to marcus.chen must be well-prepared: include specific error details, reproduction steps, and customer impact — not a vague "customer is having issues" message
- Marcus should receive enough information to begin investigation without follow-up questions
- SMB ticket should be professional but appropriately lower urgency — no over-escalation
- Both tickets should be self-contained audit trails: anyone reading the ticket should understand the full history without needing to check Rocket.Chat
- Customer-facing messages should be empathetic and informative, not robotic
- David (Enterprise) should feel his issue is being treated as top priority
- Alex (SMB) should feel acknowledged even though their issue is lower priority

## Scoring Guidelines

Dimension: Enterprise Ticket Lifecycle
- Score 1.0: Ticket created with correct subject/priority/customer, status updated, contains 4+ comments documenting full lifecycle (investigation → customer details → engineering escalation → engineering response → customer update)
- Score 0.7-0.9: Ticket exists and mostly complete but missing one lifecycle step or a comment
- Score 0.4-0.6: Ticket exists but significant gaps in the audit trail or wrong priority/subject
- Score 0.0-0.3: Enterprise ticket not created or fundamentally incorrect

Dimension: Engineering Escalation Quality
- Score 1.0: Escalation to marcus.chen includes specific technical details from David's response, clear reproduction steps, and customer impact. Marcus responds and his input is captured in the ticket.
- Score 0.7-0.9: Escalation occurs but lacks some technical specifics or Marcus's response isn't fully captured in ticket
- Score 0.4-0.6: Escalation is vague or generic; doesn't leverage David's technical details
- Score 0.0-0.3: No engineering escalation attempted or escalation is unusable

Dimension: SMB Ticket Handling
- Score 1.0: Ticket created with correct subject/priority/customer, agent engages alex.thompson, collects details, and updates ticket
- Score 0.7-0.9: Ticket exists but missing customer conversation details or wrong priority
- Score 0.4-0.6: Ticket created but no meaningful customer interaction or ticket updates
- Score 0.0-0.3: SMB ticket not created

Dimension: Priority Triage & Cross-System Integration
- Score 1.0: Enterprise ticket handled first (timestamps confirm), both tickets have chat cross-references, priority assignments match customer tiers
- Score 0.7-0.9: Priorities correct but triage order unclear, or one ticket missing chat cross-reference
- Score 0.4-0.6: Priorities don't reflect tiers, or no evidence of triage-based ordering
- Score 0.0-0.3: No triage awareness — both treated equally or SMB handled first
