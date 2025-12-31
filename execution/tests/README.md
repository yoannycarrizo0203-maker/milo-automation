# Testing Strategy

## Smoke Tests (Pre-Live Gate)
Run these tests before enabling production webhooks.

1. **Ingest Deduplication**
   - **Action**: Send same `MessageSid` twice to webhook.
   - **Assert**: DB count for that ID == 1. Second call returns 200.

2. **Paused Thread Routing**
   - **Action**: Manually set `thread_controls.paused = True`. Send inbound message.
   - **Assert**: Inbound status == `RECEIVED` (Not `DRAFT_PENDING_APPROVAL`). No draft generated.

3. **Approval Gating (Safety)**
   - **Action**: Create message with `status=DRAFT_PENDING_APPROVAL`. Run Polling Loop.
   - **Assert**: Twilio API is **NOT** called. Status remains `DRAFT_PENDING_APPROVAL`.

4. **Send Failure Handling**
   - **Action**: Mock Twilio Client to raise Exception. Set message `APPROVED_TO_SEND`. Run Polling Loop.
   - **Assert**: Status becomes `FAILED_SEND`. Audit log contains error.

## Manual Acceptance
- Verify SMS notification arrives at `OWNER_PHONE_NUMBER`.
- Verify replying "APPROVE" updates DB status.
