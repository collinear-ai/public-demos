# Task Rubric: Test multi-customer de-escalation conversation flow

## Overview

Test the agent's ability to handle two simultaneous customer conversations with vastly different personas and expectations. The agent must de-escalate a frustrated, repeat-contact customer (karen.mitchell) while simultaneously providing premium enterprise-tier support to a VP (david.park). The agent must also leverage the knowledge base during conversations and demonstrate tier-appropriate communication styles.

## Success Criteria

- Frustrated customer de-escalation: Agent acknowledges Karen's frustration, takes ownership, and provides a concrete resolution path. Karen should progressively calm down over the conversation.
- Enterprise customer handling: Agent provides professional, urgent, premium-tier responses to David Park appropriate for a VP at a major enterprise account.
- Multi-turn depth: At least 5 conversation turns with karen.mitchell (karen -> agent -> karen -> agent -> karen -> agent -> karen -> agent -> karen -> agent -> karen)
- At least 3 conversation turns with david.park (david -> agent -> david -> agent -> david -> agent -> david)
- Concurrent handling: Both conversations must show interleaved timestamps — the agent must not complete one conversation entirely before starting the other
- Knowledge base usage: Agent searches the knowledge base at least once and references relevant articles or information in responses to customers
- Tier-appropriate communication: Agent demonstrates awareness of customer tiers — more formal/urgent tone for Enterprise, empathetic/ownership tone for frustrated SMB customer
- Persona consistency: Both NPCs maintain their personas throughout (Karen: starts frustrated, gradually calms; David: professional, high expectations, time-sensitive)

## Validation Steps

1. Retrieve Rocket.Chat DM history with karen.mitchell — verify at least 5 turns
2. Retrieve Rocket.Chat DM history with david.park — verify at least 3 turns
3. Verify Karen's conversation shows de-escalation arc: early messages frustrated/angry, later messages calmer/appreciative
4. Verify David's conversation shows enterprise-appropriate handling: urgency, professionalism, premium treatment
5. Check message timestamps to confirm conversations were handled concurrently (interleaved, not sequential)
6. Verify agent performed at least one knowledge base search via helpdesk tools
7. Verify agent referenced KB information in at least one customer response
8. Verify Karen's persona consistency: frustrated → acknowledged → calming → resolved (should not suddenly become happy without proper de-escalation)
9. Verify David's persona consistency: professional, high expectations, references account size or urgency

## Testing Requirements

- Use Rocket.Chat tool server to retrieve conversation histories for both DM rooms
- Use helpdesk tool server to check knowledge base search activity
- Analyze message timestamps across both conversations for concurrency evidence
- Analyze message content for de-escalation patterns and tier-appropriate language

## Quality Criteria

- Agent must acknowledge Karen's frustration explicitly (words like "understand", "frustrated", "apologize", "sorry") before attempting resolution
- Agent must not use dismissive language with Karen (no "just", "simply", or minimizing phrases)
- Agent must convey urgency and priority in responses to David (words like "priority", "immediately", "escalate", "team")
- Agent must not use generic/templated responses — responses should be contextually specific to each customer's issue
- Karen's mood should demonstrably shift across the conversation — early anger giving way to cooperation
- David should feel his enterprise status is recognized and respected
- KB references should be relevant to the actual issues discussed, not generic

## Scoring Guidelines

Dimension: De-escalation Effectiveness
- Score 1.0: Karen starts frustrated, agent de-escalates successfully over 5+ turns, Karen becomes cooperative/appreciative
- Score 0.7-0.9: De-escalation partially successful — Karen calms somewhat but agent misses key empathy steps or fewer than 5 turns
- Score 0.4-0.6: Agent engages Karen but fails to de-escalate — Karen remains frustrated or conversation is superficial
- Score 0.0-0.3: Agent ignores Karen's frustration, uses dismissive/generic responses, or conversation doesn't occur

Dimension: Enterprise Customer Handling
- Score 1.0: David receives premium, urgent, professional responses with 3+ turns showing tier-appropriate treatment
- Score 0.7-0.9: David gets professional responses but agent doesn't fully convey urgency or enterprise-tier awareness
- Score 0.4-0.6: Responses to David are generic and don't reflect enterprise priority
- Score 0.0-0.3: David's conversation is neglected or handled inappropriately

Dimension: Concurrent Multi-Customer Management
- Score 1.0: Both conversations interleaved with overlapping timestamps, neither customer left waiting excessively
- Score 0.7-0.9: Both conversations happen but mostly sequential rather than truly concurrent
- Score 0.4-0.6: One customer clearly deprioritized or left waiting for extended period
- Score 0.0-0.3: Only one customer conversation completed, or conversations not attempted

Dimension: Knowledge Base Integration
- Score 1.0: Agent searches KB and meaningfully references relevant articles in customer responses
- Score 0.7-0.9: Agent searches KB but references are generic or not well-integrated into responses
- Score 0.4-0.6: Agent searches KB but doesn't reference results in customer conversations
- Score 0.0-0.3: No KB search attempted
