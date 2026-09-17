# Aid Nordic identity incident playbook

Document IP-2026-03. Owner: Head of IT Security. Applies to all Entra ID and Defender identity alerts raised against Aid Nordic staff accounts.

## 1. Purpose and scope

This playbook sets out how identity alerts are triaged and which response is taken for each alert type and context. It is written to be followed by an analyst or by an AI-assisted triage tool. Where the two disagree, the analyst decides.

A response proposed by an automated tool is a proposal. It becomes an action only when the conditions in section 4 are met.

## 2. Alert types

- `impossible_travel`: two sign-ins from locations that cannot be reached in the elapsed time.
- `unfamiliar_location`: a sign-in from a country or city not seen for the account in the last 90 days.
- `new_device`: a sign-in from a device not previously seen for the account.
- `leaked_credentials`: the account's credentials found in a breach, paste or marketplace.
- `mfa_fatigue`: a burst of MFA push prompts in a short window, typically not approved by the user.
- `token_anomaly`: a session or refresh token used from an unexpected device, IP or location.

## 3. Disposition rules

Dispositions are `dismiss`, `require_mfa`, `block_and_revoke` and `escalate_human`. Severity is `low`, `medium`, `high` or `critical`. Apply the first rule that matches, reading top to bottom within the alert's type. Rules 3.4, 3.5 and 3.6 take precedence over any travel context.

### 3.1 Explained by approved travel

If an `impossible_travel`, `unfamiliar_location` or `new_device` alert is fully explained by an approved trip in the travel register, on the user's registered device, and the device is compliant, the disposition is `dismiss` with severity `low`. Fully explained means the sign-in date falls within the trip dates and the sign-in location matches the trip destination.

### 3.2 Unfamiliar location or device with no trip

If an `unfamiliar_location` or `new_device` alert has no approved trip covering the date and location, the disposition is `require_mfa` with severity `medium`. The user must re-authenticate with a phishing-resistant method and, for `new_device`, IT verifies the device before it is allowed to keep a session.

### 3.3 Impossible travel with no trip

If an `impossible_travel` alert has no approved trip covering the second location, the disposition is `block_and_revoke` with severity `high`. All sessions are revoked and the password is reset before the account is re-enabled.

### 3.4 Leaked credentials

A `leaked_credentials` alert is always `block_and_revoke` with severity `critical`. An approved trip, a compliant device or a recent successful MFA does not change this. This disposition always requires human approval (section 4).

### 3.5 MFA fatigue

An `mfa_fatigue` alert is always `block_and_revoke` with severity `high`. A burst of prompts means the password is already known to someone else. Travel does not explain it.

### 3.6 Token anomaly

A `token_anomaly` alert is always `block_and_revoke` with severity `high`. If the token was used from a non-compliant or unregistered device, record this in the evidence. Travel does not explain a token being used from a location the device was not in.

### 3.7 Trip boundary

If a sign-in from the trip destination falls within 48 hours before the trip start or within 48 hours after the trip end, the disposition is `require_mfa` with severity `medium`. Early arrivals and delayed departures are common and are not treated as compromise, but the user must re-authenticate.

### 3.8 Unregistered device during approved travel

If a `new_device` alert occurs during an approved trip and the device is not registered to the user, the disposition is `escalate_human` with severity `medium`. This is usually a personal device, which the travel security policy does not permit for work data. The analyst contacts the traveller before any block.

### 3.9 Location not on the itinerary during approved travel

If a sign-in during an approved trip comes from a location that is neither the home country nor the trip destination, the disposition is `escalate_human` with severity `medium`. Transit hubs and neighbouring cities are common causes, but the tool cannot verify the route.

### 3.10 VPN or anonymiser egress

If the sign-in IP resolves to a VPN provider or anonymiser and no other rule in 3.3 to 3.6 applies, the disposition is `escalate_human` with severity `low`. Staff in some duty stations use VPNs legitimately. The analyst confirms with the traveller.

## 4. Approval

`block_and_revoke` always requires approval from a named member of the IT Security team before it is executed. `leaked_credentials` always requires approval, whatever the disposition. An automated tool must mark these cases `requires_approval: true` and must not execute them.

`dismiss` and `require_mfa` may be executed without prior approval but are logged and reviewed weekly.

`escalate_human` is not an action. It hands the case to the on-call analyst with the evidence collected so far.

## 5. User communication

Every disposition other than `dismiss` includes a message to the user. The message states what was observed, what has been done or is proposed, and what the user should do next. It uses plain language, does not include IP addresses or technical identifiers, and states that the decision was prepared with AI assistance and reviewed by the IT Security team, as required by the AI use policy.

## 6. Evidence and logging

Each triage record lists the evidence used: the alert, the travel register entry, the device compliance state and the playbook section applied. Records use pseudonymous user and device identifiers. IP addresses are stored with the last octet masked. Records are retained for 12 months.
