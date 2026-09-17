# Aid Nordic policy on the use of AI

Document AI-2026-01. Owner: Director of Operations. Applies to all use of AI systems by Aid Nordic staff and to AI systems operated on Aid Nordic's behalf.

## 1. Purpose

Aid Nordic uses AI tools where they help staff do their work well and where the risks are understood and managed. This policy sets the conditions. It applies to general productivity tools and to purpose-built systems such as the identity alert triage tool.

## 2. Principles

- People remain accountable. An AI system informs a decision; a named person makes it.
- Data minimisation. AI systems receive the least data needed for the task.
- Transparency. People affected by an AI-assisted decision are told that AI was involved.
- Proportionality. Automated action is limited to low-impact, reversible steps.
- Review. AI systems are evaluated before use and monitored while in use.

## 3. Approved and prohibited uses

### 3.1 Approved

Drafting and summarising documents, translation, coding assistance, analysis of synthetic or aggregated data, and purpose-built systems that have completed the review in section 6.

### 3.2 Prohibited

Entering beneficiary personal data, protection case notes or unredacted incident reports into any AI tool that has not been approved for that data. Using AI output as the sole basis for a decision that affects a person's employment, safety or access to services.

## 4. AI-assisted security decisions

### 4.1 Scope

This section applies to AI systems that read security alerts and propose responses, including the identity alert triage tool.

### 4.2 Human approval

Any action that blocks an account, revokes sessions or resets credentials requires approval from a named member of the IT Security team before it is executed. The AI system may propose the action and prepare the evidence. It may not execute it. Actions that only require the user to re-authenticate may be executed automatically and are reviewed weekly.

### 4.3 Escalation

Where the system cannot match a case to a documented rule, it must hand the case to a person rather than guess. A proposal must cite the policy section it relies on. A proposal without a citation is treated as an escalation.

### 4.4 Data handling

The system works on pseudonymous user and device identifiers. IP addresses are masked before the system sees them. Alert content and model responses are not captured in monitoring traces; only timing, token counts and outcome codes are recorded. Travel register data is limited to destination, dates and approver.

### 4.5 Evidence

Each proposal records the alert, the travel register entry, the device state and the rule applied, so that an analyst can check the reasoning without re-running the system.

## 5. Disclosure to users

### 5.1 When a user is contacted

When a staff member is contacted as a result of an AI-assisted security decision, the message states that the decision was prepared with AI assistance and reviewed by the IT Security team. It gives a way to reach a person.

### 5.2 Plain language

Messages to users describe what was observed and what to do next in plain language. They do not include technical identifiers, IP addresses or the internal risk score.

### 5.3 Right to query

A staff member may ask for a person to review any AI-assisted decision that affected their account. IT Security responds within two working days.

## 6. Review before use

A purpose-built AI system is evaluated against a test set with known correct outcomes before it is used on live data, and again after any change to its instructions, tools or underlying model. Results are kept with the system's documentation. A system that falls below the agreed thresholds is not used until it is corrected.

## 7. Monitoring in use

AI systems in use are monitored for availability, latency, cost and outcome distribution. A sudden change in the share of cases blocked or escalated is investigated. Monitoring data is retained for 12 months.

## 8. Responsibilities

The system owner keeps this policy's requirements in the system's design and documentation. The Head of IT Security approves security-related systems. The Director of Operations owns this policy and reviews it annually.
