# 20 Data Model

## Message Object
Core tracking object for every interaction.

- **ID**: UUID
- **Thread_ID**: String (Sender Phone Number E.164). Groups all interaction by user.
- **In_Reply_To_Message_ID**: UUID (Links outbound/draft to specific inbound ID).
- **Timestamp**: ISO8601
- **Type**: INBOUND | DRAFT | OUTBOUND
- **Draft_Version**: Integer (Default 1. Edits create new version; preserve original).
- **Sender**: Phone Number
- **Receiver**: Phone Number
- **Body**: Text content
- **Media**: JSON list of media URLs (if any)

- **Status**:
  - `RECEIVED` (Inbound only, initial state)
  - `NEEDS_REVIEW` (Human intervention required, auto-draft failed/skipped)
  - `DRAFT_PENDING_APPROVAL` (AI draft generated, waiting for human)
  - `APPROVED_TO_SEND` (Human verified, ready for polling job)
  - `REJECTED` (Human rejected draft, end of flow)
  - `SENT` (Successfully transmitted to Twilio)
  - `FAILED_SEND` (Twilio API error)
  - `PAUSED_THREAD` (Sender paused explicitly)

## Approval Object
- **Draft_ID**: UUID (Refers to Message Object)
- **Reviewer**: User identifier
- **Action**: APPROVE | REJECT | EDIT
- **Timestamp**: ISO8601
- **Notes**: Optional comment

## Audit Log Fields
- **Event_ID**: UUID
- **Timestamp**: ISO8601
- **Actor**: System | Human
- **Action**: "Generated Draft", "Sent Message", "Updated Directive", etc.
- **Details**: JSON payload of what changed

## Status Enums
- **Conversation State**: `ACTIVE`, `ARCHIVED`, `NEEDS_ATTENTION`
- **Sentiment**: `POSITIVE`, `NEUTRAL`, `NEGATIVE`, `UNKNOWN`

## Persistence Layer
- **Technology**: SQLite
- **Justification**:
  - **Reliability**: Single-file ACID compliance; zero network latency.
  - **Simplicity**: No external server setup; standard Python support.
  - **Auditability**: Easily queryable for history and debugging.

## Database Schema (Minimal Tables)
- **Table: `messages`**
  - `id` (TEXT PK)
  - `thread_id` (TEXT)
  - `in_reply_to_id` (TEXT FK)
  - `sender` (TEXT)
  - `receiver` (TEXT)
  - `body` (TEXT)
  - `media` (TEXT JSON)
  - `status` (TEXT ENUM)
  - `type` (TEXT ENUM)
  - `timestamp` (DATETIME)
  - `draft_version` (INT)

- **Table: `approvals`**
  - `id` (TEXT PK)
  - `draft_id` (TEXT FK)
  - `reviewer_phone` (TEXT)
  - `action` (TEXT ENUM: APPROVE, EDIT, REJECT)
  - `notes` (TEXT)
  - `timestamp` (DATETIME)

- **Table: `audit_log`**
  - `id` (TEXT PK)
  - `event` (TEXT)
  - `actor` (TEXT)
  - `metadata` (TEXT JSON)
  - `timestamp` (DATETIME)

- **Table: `thread_controls`**
  - `thread_id` (TEXT PK)
  - `paused` (BOOLEAN)
  - `paused_reason` (TEXT)
  - `last_updated` (DATETIME)

