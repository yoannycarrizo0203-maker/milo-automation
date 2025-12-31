# 10 Scope and Guardrails

## In-Scope Messages
- Scheduling requests.
- Pricing inquiries (standard rate card).
- Service availability checks.
- FAQs (location, hours, basic policy).

## Out-of-Scope Messages
- Complex complaints or legal threats.
- Custom quoting or negotiation.
- Emergency or safety issues.
- Personal messages to staff.

## Human-Only Escalation Rules
- If sentiment is **Negative/Hostile** -> Flag for manual review, do not draft.
- If intent is **Unknown** -> Flag for manual review.
- If message contains "manager", "urgent", "emergency" -> Flag for high-priority manual review.

## Language Handling
- **English (EN)**: Default.
- **Spanish (ES)**: Detect if user speaks Spanish -> Switch draft language to Spanish.
- **Other**: If detected -> Flag for manual review (TODO: Add other languages later).

## Uncertainty Principle
- **Default Action**: If unsure, **DO NOTHING** (No external outbound message).
- **Required Action**: Generate an internal alert/queue item for human review.
- Flag for human attention.
- Better to be silent and wait for a human than to send a wrong or hallucinated response.
