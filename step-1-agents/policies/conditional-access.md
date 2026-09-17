# Aid Nordic conditional access standard

Document CA-2026-04. Owner: Head of IT Security. Describes the conditional access policies applied to Aid Nordic's Entra ID tenant and how they interact with travel.

## 1. Purpose

Conditional access decides, at each sign-in, whether the user may proceed, must satisfy extra controls, or is blocked. This standard describes the policies in force so that analysts and automated triage can reason about why an alert was raised and what control already applied.

## 2. Baseline policies

### 2.1 MFA for all users

Every interactive sign-in requires multi-factor authentication. Accepted methods are the authenticator app with number matching and FIDO2 hardware keys. SMS is accepted only for accounts flagged for migration and is blocked from named high-risk countries.

### 2.2 Compliant device required

Access to email, files and the case management system requires a device that is registered and reported compliant by device management. A non-compliant device is redirected to a remediation page and cannot open a session until compliance is restored.

### 2.3 Legacy authentication blocked

Protocols that cannot perform MFA are blocked for all users.

### 2.4 Sign-in frequency

Sessions on registered devices persist for 14 days. Sessions from unregistered devices are not permitted, and browser sessions on shared or kiosk devices expire after 1 hour.

## 3. Risk-based policies

### 3.1 Sign-in risk

Sign-ins rated medium risk by Entra ID Protection require re-authentication with MFA. Sign-ins rated high risk are blocked until an analyst has reviewed them. Impossible travel and unfamiliar sign-in properties normally rate medium; token anomalies and leaked credentials rate high.

### 3.2 User risk

Users rated high risk must change their password at next sign-in. Leaked credentials always raise user risk to high.

## 4. Named locations and travel

### 4.1 Named locations

Aid Nordic's offices in Copenhagen, Stockholm, Nairobi, Amman, Dhaka and Bogota, and the Aid Nordic VPN egress ranges, are named trusted locations. Sign-ins from a trusted location do not raise unfamiliar location alerts.

### 4.2 Travel register integration

The travel register is not enforced by conditional access. It is used after the fact by IT Security and by the triage tool to explain alerts. A traveller in an approved destination will still be asked to re-authenticate on arrival; the register is used to decide that no further action is needed.

### 4.3 Countries with additional controls

Sign-ins from countries where Aid Nordic has no programme and no approved travel are treated as unfamiliar and require MFA. Analysts may add a temporary country exception for the duration of an approved trip when the destination triggers repeated alerts.

## 5. What the triage tool may rely on

The triage tool may assume that a sign-in that completed did so with MFA and, for the applications in 2.2, from a compliant device at the time of sign-in. It may not assume that the person holding the device was the account owner. Device compliance recorded in the traveller register is the state at the last check-in and may lag by up to 24 hours.

## 6. Exceptions

Exceptions to this standard are approved by the Head of IT Security, are time-limited, and are recorded with the business reason. Travel is not an exception; it is handled by the travel security policy and the incident playbook.
