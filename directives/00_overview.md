# 00 Overview

## System Purpose
MILO is an **approval-gated business texting automation** system designed to handle inbound messages, draft appropriate responses, and ensure *no message is sent without explicit human approval*.

## What Milo Does
- Ingests inbound messages from Twilio.
- Classifies intent and sentiment.
- Drafts responses based on templates or LLM logic.
- Queues drafts for human review.
- Sends approved messages via Twilio.
- Logs all actions for audit.

## What Milo Does NOT Do
- Auto-send messages without approval (Hard constraint).
- Handle voice calls.
- Process payments directly.
- Engage in long-form "chat" without a clear business goal.

## High-Level Flow
1. **Ingest**: Webhook receives message -> stored in DB (Incoming).
2. **Draft**: System analyzes content -> generates draft response -> stored in DB (Draft).
3. **Approve**: Human reviews draft -> approves/edits/rejects -> stored in DB (Approved/Rejected).
4. **Send**: System picks up approved message -> sends via Twilio -> stored in DB (Sent).

## Explicit Constraint
> **NO MESSAGE IS EVER SENT WITHOUT A HUMAN "Y" FLAG IN THE APPROVAL COLUMN.**

## Configuration & Requirements
### Environment Variables (`.env`)
- `TWILIO_ACCOUNT_SID`: Twilio Account String.
- `TWILIO_AUTH_TOKEN`: Twilio Auth Token.
- `TWILIO_PHONE_NUMBER`: The business phone number (Sender).
- `OWNER_PHONE_NUMBER`: The human reviewer's E.164 phone number.
- `DATABASE_PATH`: Path to SQLite DB file (e.g., `execution/milo.db`).
- `BASE_URL`: Public URL for webhooks (e.g., ngrok or prod URL).
- `OPENAI_API_KEY`: For LLM generation.

### Dependencies
- `twilio`: For API interaction.
- `flask` or `fastapi`: For Webhook server.
- `sqlite3`: Native Python support.

