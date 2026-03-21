# Weaver Enterprises People Management Seed Data

This directory contains seed data for the Weaver Enterprises People Management scenario.

## Directory Structure

- `org_chart.md` - Organizational chart for all departments (Talent Acquisition, Engineering, Finance, Operations)
- `recruitment_hiring_policy.md` - Recruiting and hiring policies and procedures
- `interview_process.md` - Interview guidelines and legal do/don'ts
- `interview_process_per_job.md` - Detailed interview stages for each open job requisition
- `onboarding_policy.md` - New-hire onboarding policy and timeline
- `offer_template.md` - Offer letter template
- `candidate_faq.md` - Candidate-facing FAQ (high-level)
- `401K_policy.md` - 401(k) policy details
- `health_insurance_plan.md` - Health plan summary of benefits and coverage
- `compensation_bands.json` - Compensation bands for the scenario
- `skills.md` - HR best practices and behaviors the agent should follow
- `../candidate_seed/` - Candidate and job requisition seed data
  - `candidates.json` - Candidate pipeline data (30 candidates)
  - `resumes/` - Candidate resume files
  - `frappe_seed/` - Frappe HRMS seed data
    - `employee_records/` - Employee records (25 employees)
    - `job_requisitions/` - Job requisition documents (10 open positions)

## Calendar Seeding

Calendar events (interview schedules) can be seeded in two ways:

### 1. Per-Task Seeding (Recommended)

Add `seed_calendar_events` to task JSON files:

```json
{
  "seed_calendar_events": [
    {
      "account": "patricia_lee",
      "calendar_id": "default",
      "summary": "Phone Screen - Maya Kumar",
      "description": "Phone screen interview for Software Development Engineer position",
      "start": "2026-01-25T10:00:00Z",
      "end": "2026-01-25T10:30:00Z",
      "uid": "interview-001"
    }
  ]
}
```

### 2. Environment Variable Seeding

Set `CALDAV_SEED_EVENTS` environment variable in the `baikal-seed` container (JSON array format).

## Email Seeding

Emails can be seeded in two ways:

### 1. Per-Task Seeding (Recommended)

Add `seed_emails` to task JSON files:

```json
{
  "seed_emails": [
    {
      "from_profile_id": "michael_chen",
      "to_addr": "candidate@email.com",
      "subject": "Interview Confirmation - Software Development Engineer",
      "body_text": "Dear Candidate,\n\nYour interview has been scheduled...",
      "body_html": "<p>Dear Candidate,</p><p>Your interview has been scheduled...</p>"
    }
  ]
}
```

### 2. Environment Variable Seeding

Set `MAILHOG_SEED_EMAILS` environment variable in the `mailhog-seed` container (JSON array format).

## Employee Directory

### Executive Leadership

| Name | Title | Email |
|------|-------|-------|
| Sarah Johnson | VP of Talent Acquisition | sarah.johnson@weaverenterprises.com |
| Victoria Wells | VP of Engineering | victoria.wells@weaverenterprises.com |
| Catherine Moore | Chief Financial Officer | catherine.moore@weaverenterprises.com |
| Nancy Cooper | Operations Director | nancy.cooper@weaverenterprises.com |

### Talent Acquisition Department

| Name | Title | Email |
|------|-------|-------|
| Sarah Johnson | VP of Talent Acquisition | sarah.johnson@weaverenterprises.com |
| Michael Chen | Talent Acquisition Manager | michael.chen@weaverenterprises.com |
| Emily Davis | Senior Recruiter | emily.davis@weaverenterprises.com |
| Patricia Lee | Scheduling Specialist | patricia.lee@weaverenterprises.com |
| David Thompson | Onboarding Manager | david.thompson@weaverenterprises.com |
| Lisa Anderson | Onboarding Specialist | lisa.anderson@weaverenterprises.com |
| Jennifer Martinez | Recruiting Operations Manager | jennifer.martinez@weaverenterprises.com |
| Maria Garcia | Recruiting Coordinator | maria.garcia@weaverenterprises.com |
| Jessica Patel | Recruiting Coordinator | jessica.patel@weaverenterprises.com |
| Samantha Lewis | University Recruiter | samantha.lewis@weaverenterprises.com |

### Engineering Department

| Name | Title | Email |
|------|-------|-------|
| Victoria Wells | VP of Engineering | victoria.wells@weaverenterprises.com |
| Daniel Harris | Principal Engineer | daniel.harris@weaverenterprises.com |
| Robert Kim | Engineering Manager | robert.kim@weaverenterprises.com |
| James Brown | Senior Software Engineer | james.brown@weaverenterprises.com |
| Kevin Nguyen | Software Engineer | kevin.nguyen@weaverenterprises.com |
| Priya Sharma | Data Engineer | priya.sharma@weaverenterprises.com |
| Marcus Robinson | DevOps Engineer | marcus.robinson@weaverenterprises.com |
| Alex Wong | Frontend Engineer | alex.wong@weaverenterprises.com |

### Finance Department

| Name | Title | Email |
|------|-------|-------|
| Catherine Moore | Chief Financial Officer | catherine.moore@weaverenterprises.com |
| Thomas Reed | Finance Manager | thomas.reed@weaverenterprises.com |
| Amanda Wright | Financial Analyst | amanda.wright@weaverenterprises.com |
| Jason Mitchell | Senior Accountant | jason.mitchell@weaverenterprises.com |

### Operations Department

| Name | Title | Email |
|------|-------|-------|
| Nancy Cooper | Operations Director | nancy.cooper@weaverenterprises.com |
| Christopher Taylor | Operations Lead | christopher.taylor@weaverenterprises.com |
| Ryan O'Connor | Operations Analyst | ryan.oconnor@weaverenterprises.com |

## Open Job Requisitions

| Requisition ID | Title | Positions | Hiring Manager |
|----------------|-------|-----------|----------------|
| REQ-2026-001 | Software Development Engineer | 3 | Robert Kim |
| REQ-2026-002 | Product Manager | 2 | Sarah Johnson |
| REQ-2026-003 | Data Scientist | 2 | Robert Kim |
| REQ-2026-004 | UX Designer | 2 | Michael Chen |
| REQ-2026-005 | Technical Program Manager | 2 | Nancy Cooper |
| REQ-2026-006 | Senior Data Engineer | 2 | Robert Kim |
| REQ-2026-007 | Machine Learning Engineer | 2 | Robert Kim |
| REQ-2026-008 | Engineering Manager | 1 | Victoria Wells |
| REQ-2026-009 | UX Researcher | 1 | Michael Chen |
| REQ-2026-010 | Senior Software Development Engineer | 3 | Robert Kim |

See `interview_process_per_job.md` for detailed interview stages for each requisition.

## Interview Rooms

- **Conference Room A** - Main interview room, capacity 6
- **Conference Room B** - Secondary interview room, capacity 4
- **Video Conference Room** - Equipped for remote interviews
- **Panel Interview Room** - Large room for panel interviews, capacity 10

## Interview Schedule Templates

| Interview Type | Duration |
|----------------|----------|
| Recruiter Screen | 30 minutes |
| Phone Screen | 60 minutes |
| Technical Interview | 60-75 minutes |
| Behavioral Interview | 45 minutes |
| Panel Interview | 60-90 minutes |
| Design Exercise | 90 minutes |

See `interview_process.md` for recommended interview structure and legal guidelines.

---

## What Can and Cannot Be Seeded

### CAN Be Seeded (Pre-populated Before Task Starts)
| Type | How | Notes |
|------|-----|-------|
| **Emails** | `seed_emails` in task JSON | Appears in agent's inbox |
| **Calendar Events** | `seed_calendar_events` in task JSON | Events on NPC calendars |
| **Chat Channels** | `seed_group_channels` in task JSON | Pre-existing channel membership + history context |
| **NPC Secrets** | `npcs[].secret` in task JSON | Info NPCs reveal when asked via Chat |
| **HRIS Data** | Frappe seed files | Employee records, candidates, requisitions |

### CANNOT Be Seeded
| Type | Why | Alternative |
|------|-----|-------------|
| **DM History** | Direct-message threads cannot be pre-seeded | Use `seed_emails`, NPC secrets, or seeded channels |

### Task Design Implications

**Tasks must NOT assume:**
- Existing DM history the agent can read at task start
- Ability for the agent to create channels/groups

**Tasks MAY assume (when seeded):**
- Existing channel context/messages in `seed_group_channels`
- Use of explicitly named channels already present in seed data

**If task needs info from someone:**
1. Use `seed_emails` (email from the NPC forwarding relevant info)
2. Add an NPC `secret` (agent asks via Chat, NPC replies)
3. Include directly in task description

### Multi-Person Decisions

For panel interviews, debriefs, or group decisions:
- **Each decision-maker should have their own NPC secret**
- Secrets should reflect individual perspectives/feedback
- This ensures agent must consult each relevant stakeholder

Example for 3-person interview panel:
```json
{
  "npcs": [
    {"id": "michael_chen", "secret": "I thought the candidate was strong on system design but needs more depth on algorithms."},
    {"id": "emily_davis", "secret": "Good culture fit, but I have concerns about their experience with our scale."},
    {"id": "sarah_johnson", "secret": "I'd recommend a hire - their leadership experience outweighs the technical gaps."}
  ]
}
```
