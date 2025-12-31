# 40 Failure Modes

## Ingest Idempotency
- **Rule**: Deduplicate by Twilio `MessageSid`.
- **Action**: If `MessageSid` already exists in DB, ignore duplication. Return 200 OK to Twilio.

## Approval Timeout
- **Scenario**: Draft waits > X hours without review.
- **Action**: Alert human again (escalate priority). Do NOT auto-send. Do NOT auto-reject.

## Unknown Language
- **Scenario**: Language detection confidence < threshold.
- **Action**: Flag for manual review. Do not draft.

## Draft Generation Failure
- **Scenario**: LLM/Template script errors out.
- **Action**: Log error. Create empty draft with "Error generating response". Flag for manual review.

## Twilio Delivery Failure
- **Scenario**: API returns error (e.g., undeliverable).
- **Action**: Update status to `FAILED`. Alert human. Do not retry automatically (avoids spam loops).

## System Crash
- **Scenario**: DB or Server down.
- **Assumption**: Webhooks should retry (Twilio standard behavior).
- **Action**: Once up, process backlog in chronological order.
