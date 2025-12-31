# 30 Workflows

## Happy Path (Normal Flow)
1. **Receive**: Webhook triggers script.
2. **Log**: Save raw message to DB (`Status=RECEIVED`).
3. **Analyze**: Helper script determines Intent/Sentiment.
4. **Draft**:
   - **Media Check**: If `Media` exists OR `Body` is empty -> Status=`NEEDS_REVIEW` (No auto-draft).
   - If Intent = Known & Sentiment != Negative: Generate draft.
   - Save draft to DB (`Status=DRAFTED`).
5. **Notify**: Alert human (via Dashboard/Slack/SMS) that draft is ready.
6. **Review**:
   - Human clicks "Approve".
   - DB updates to `Status=APPROVED`.
7. **Send**:
   - **Polling Job** (Cron) queries DB for `Status=APPROVED`.
   - Script picks up message -> sends via Twilio.
   - DB updates to `Status=SENT`.

## Manual Approval Loop
- Dashboard shows list of `DRAFTED` messages.
- Options:
  - **Approve**: Proceed to send.
  - **Edit**: Modify text -> Approve -> Send.
  - **Reject**: Mark as `REJECTED` -> No message sent. Archive thread.

## Rejection Flow
- If draft is `REJECTED`:
  - Log rejection reason (optional).
  - Stop automation for this thread.
  - Move thread to "Manual Intervention" queue.

## Orchestration Routing Rules (Inbound -> Status)
- **Rule 1: Duplication Check**
  - IF `MessageSid` exists -> STOP (Return 200).
- **Rule 2: Thread Status Check**
  - IF Thread is `PAUSED_THREAD` -> Status=`RECEIVED` (Log only, do not draft).
- **Rule 3: Media/Body Check**
  - IF `Media` is present OR `Body` is empty -> Status=`NEEDS_REVIEW`.
- **Rule 4: Language Detection**
  - IF Language Confidence < Threshold -> Status=`NEEDS_REVIEW`.
  - IF Language != EN/ES -> Status=`NEEDS_REVIEW`.
- **Rule 5: Sentiment Check**
  - IF Sentiment == NEGATIVE -> Status=`NEEDS_REVIEW`.
- **Rule 6: Intent Check**
  - IF Intent == UNKNOWN -> Status=`NEEDS_REVIEW`.
- **Rule 7: Happy Path**
  - IF All checks pass -> Generate Draft -> Status=`DRAFT_PENDING_APPROVAL`.

## Execution Contracts
### 1. Webhook Ingest (Entrypoint)
- **Inputs**: Twilio standard payload (`From`, `To`, `Body`, `MessageSid`, `NumMedia`, `MediaUrl{i}`).
- **Outputs**: HTTP 200 OK (Empty TwiML).
- **Idempotency**: Query `messages` table for `id == MessageSid`. If found, Log "Duplicate" & Exit.
- **Write**: Insert new record into `messages` (`status=RECEIVED`, `type=INBOUND`). Write `audit_log` event.

### 2. Polling Loop (Sender)
- **Criteria**: `SELECT * FROM messages WHERE status = 'APPROVED_TO_SEND'`.
- **Action**: Loop through results. For each:
  - Call Twilio API to send.
  - IF Success: Update `status='SENT'`, `timestamp=NOW`. Log audit.
  - IF Error: Update `status='FAILED_SEND'`. Log audit with error details.
  - IF Error: Update `status='FAILED_SEND'`. Log audit with error details.
  - **Sleep**: Poll every exactly 15 seconds.

### Polling Ownership
- **Logic Owner**: `execution/jobs/job_03_act.py` contains the `run_polling_loop` function and business logic.
- **Runtime Owner**: `execution/run.py` is responsible for spawning the daemon thread that executes the loop on startup.

## Owner Approval Mechanism (MVP)
- **Channel**: SMS to `OWNER_PHONE_NUMBER`.
- **Content**: "Draft for [Sender]: '[Preview]...' Reply APPROVE, REJECT, or [New Text]."
- **Actions**:
  - **APPROVE**: System marks status `APPROVED_TO_SEND`.
  - **REJECT**: System marks status `REJECTED` (Thread stops).
  - **EDIT/New Text**: System creates NEW draft version (`status=DRAFT_PENDING_APPROVAL `), updates DB, and re-sends approval request.
- **Timeout**:
  - No auto-send.
  - If > 24h, send internal alert "Draft Expired".
  - Status remains `DRAFT_PENDING_APPROVAL` until acted upon.

