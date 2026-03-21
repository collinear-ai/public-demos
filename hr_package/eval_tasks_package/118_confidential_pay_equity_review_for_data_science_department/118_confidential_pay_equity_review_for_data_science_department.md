# Task Rubric: People Management - Confidential Pay Equity Review for Data Science Department

## Task Overview
The agent must review a compensation breakdown for the Data Science team, identify employees whose salary falls below 90% of the median for their grade level, send a confidential summary email to Marcus Chen and Sarah Liu, confirm the meeting title with Marcus Chen via DM, schedule a 30-minute meeting with three stakeholders using the confirmed title, and DM Catherine Moore for additional compensation policy context to include in the email.

## Success Criteria

### Compensation Analysis & Email
- Correctly calculated the median salary for each grade level in the Data Science team
- Correctly identified all employees whose salary falls below 90% of the median for their grade level (no false positives or false negatives)
- The summary email includes for each flagged employee: **name, grade, current salary, grade median, and percentage gap** — presented clearly and easy to scan
- The percentage gap calculations are accurate
- The email includes Catherine Moore's compensation policy note: that employees flagged below 90% of their grade median are eligible for an off-cycle adjustment of up to 8% effective within 30 days of the review (or semantically equivalent language capturing these key details)
- The email treats the content as confidential (e.g., uses "confidential" language or equivalent marking)
- No compensation details are shared with unauthorized parties (e.g., not included in calendar invite descriptions, not sent to people outside Marcus, Sarah, and appropriate stakeholders)

### DM to Marcus Chen for Meeting Title Confirmation
- The DM to Marcus Chen is professionally worded and clearly asks what meeting title he wants for the calendar invite
- The agent honored Marcus Chen's exact stated preference: the meeting title "DS Pay Equity Review" — using that exact wording as Marcus specified

### DM to Catherine Moore for Policy Context
- The DM to Catherine Moore is professionally worded and clearly asks whether she has additional context on recent compensation policy changes
- Catherine's response about the off-cycle adjustment policy (up to 8%, within 30 days) was faithfully and accurately incorporated as a brief note at the end of the summary email to Marcus and Sarah

### Calendar Meeting
- The calendar invite description does not contain sensitive compensation details such as individual salary figures (privacy standard)
- The calendar invite description, if present, is professional and appropriately neutral

### Cross-Channel Consistency & Professional Standards
- Employee names are spelled consistently across email, chat, and calendar
- No individual salary figures appear in the calendar invite or any chat messages
- The email is professional in tone, well-organized, and appropriate for a confidential HR compensation review

## Validation Steps

1. **Verify salary analysis**: Cross-reference the flagged employees against the compensation data. For each grade level, compute the median salary, then check whether each employee's salary is below 90% of that median. Confirm all flagged employees are correct and none are missed.
2. **Inspect sent email content quality**: Confirm the email contains:
   - Each flagged employee's name, grade, current salary, grade median, and percentage gap — clearly formatted and accurate
   - A note at the end about Catherine Moore's policy context (off-cycle adjustment up to 8%, within 30 days) that faithfully represents what Catherine shared
   - Confidential framing/marking
   - No employees who should NOT be flagged are included
   - Professional, clear, and well-organized presentation
3. **Check DM quality to Marcus Chen**: Verify the DM is professional and clearly asks about the meeting title preference; confirm Marcus's exact title "DS Pay Equity Review" was used
4. **Check DM quality to Catherine Moore**: Verify the DM is professional and clearly asks about compensation policy context; confirm her response was accurately incorporated into the email
5. **Inspect calendar event privacy**: Verify the calendar invite description does not contain individual salary details or other sensitive compensation figures
6. **Verify confidentiality throughout**: Ensure no sensitive compensation data leaked into chat messages, calendar descriptions, or communications to unauthorized parties

## Scoring Guidelines

```
Dimension: Compensation Analysis Accuracy
- 1.0: All flagged employees are correctly identified with accurate median calculations, percentage gaps, and no false positives/negatives
- 0.7: Most flagged employees are correct but one calculation error or one missed/extra employee
- 0.3: Some correct identifications but multiple errors in median calculation or flagging logic
- 0.0: Analysis not performed, fundamentally wrong methodology, or no employees flagged/all employees incorrectly flagged

Dimension: Confidential Summary Email Quality
- 1.0: Email includes all required fields (name, grade, salary, median, gap) for each flagged employee in a clear, well-organized format; includes Catherine's policy note at the end faithfully capturing the off-cycle adjustment up to 8% within 30 days; marked confidential; professional tone appropriate for sensitive HR communication; no salary data leaked to unauthorized channels
- 0.7: Email contains most required fields but one data element per employee is missing or poorly formatted; or Catherine's note is vague/incomplete; or minor confidentiality issue (e.g., missing confidential marking but no actual leak)
- 0.3: Email missing multiple required fields, or Catherine's policy note entirely absent, or poorly organized and hard to interpret
- 0.0: No substantive pay equity analysis in the email, or contains no useful summary content

Dimension: Stakeholder Communication (DMs)
- 1.0: DM to Marcus Chen is professional and clearly asks for meeting title preference; Marcus's exact title "DS Pay Equity Review" is honored; DM to Catherine Moore is professional and clearly asks for policy context; Catherine's response is faithfully incorporated into the email
- 0.7: Both DMs sent and professional but one preference not fully followed (e.g., meeting title slightly different from Marcus's exact request, or Catherine's context only partially included)
- 0.3: DMs are unclear, unprofessional, or responses largely ignored
- 0.0: No meaningful stakeholder engagement via DMs; preferences disregarded

Dimension: Calendar Meeting Privacy & Professionalism
- 1.0: Calendar invite description is professional, appropriately neutral, and contains no sensitive compensation details (individual salaries, flagged employee names with pay data, etc.)
- 0.7: Calendar invite is mostly appropriate but contains a minor detail that could be considered sensitive
- 0.3: Calendar invite contains some identifiable compensation details or uses an inappropriate/alarming title
- 0.0: Calendar invite openly lists sensitive salary information or compensation findings

Dimension: Process Sequencing & Confidentiality Standards
- 1.0: Correct sequencing observed (DM to Marcus before scheduling; DM to Catherine before finalizing email); consistent employee names across channels; compensation data kept confidential throughout all channels
- 0.7: Minor sequencing issue or one minor inconsistency across channels
- 0.3: Multiple sequencing violations or data inconsistencies across channels
- 0.0: No attention to sequencing; sensitive data shared inappropriately; major inconsistencies

Dimension: Scope Discipline
- 1.0: Agent performed only necessary state-changing actions (emails to Marcus and Sarah, DMs to Marcus and Catherine, one calendar event); no unnecessary extra emails, messages, or calendar events
- 0.7: One unnecessary state-changing action (e.g., an extra email or message not required by the task)
- 0.3: Two unnecessary state-changing actions
- 0.0: Three or more unnecessary state-changing actions or severe out-of-scope side effects (e.g., sharing compensation data with unauthorized parties)
Note: Additional read-only actions (extra searches, lookups, retries) are acceptable and should not be penalized.
