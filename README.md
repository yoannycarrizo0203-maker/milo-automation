# MILO - Approval-Gated Business Texting

## Configuration & Requirements

### Twilio Configuration
1. **Webhook URL**: `[YOUR_BASE_URL]/twilio/inbound` (POST)
2. **Owner Commands**: The owner sends commands (A/R/E) to the *same* business number. The system detects the `OWNER_PHONE_NUMBER` sender to route it as a command.

### Environment Variables (`.env`)
Required variables for the execution layer:

- `TWILIO_ACCOUNT_SID`: Twilio Account String.
- `TWILIO_AUTH_TOKEN`: Twilio Auth Token.
- `TWILIO_PHONE_NUMBER`: The business phone number (Sender).
- `OWNER_PHONE_NUMBER`: The human reviewer's E.164 phone number.
- `DATABASE_PATH`: Path to SQLite DB file (e.g., `execution/milo.db`).
- `BASE_URL`: Public URL for webhooks (e.g., ngrok or prod URL).
- `OPENAI_API_KEY`: Required for AI classification and drafting.


### Dependencies
- `twilio`: For API interaction.
- `flask`: Webhook server.
- `openai`: AI features.

## Deployment (Render)
**Recommended Hosting**: Render Web Service with Persistent Disk.

### 1. Configuration table (Environment Variables)
| Variable | Value / Description |
| :--- | :--- |
| `TWILIO_ACCOUNT_SID` | Production SID |
| `TWILIO_AUTH_TOKEN` | Production Token |
| `TWILIO_PHONE_NUMBER` | Business Sender ID |
| `OWNER_PHONE_NUMBER` | Reviewer E.164 Number |
| `OPENAI_API_KEY` | `sk-...` |
| `BASE_URL` | `https://[app].onrender.com` |
| `DATABASE_PATH` | `/data/milo.db` (Must use persistent disk path) |
| `ENABLE_SENDING` | `true` (Default `false` for safety) |
| `PYTHON_VERSION` | `3.11.0` |

### 2. Setup Steps
1. Create New Web Service (Python).
2. Attach **Persistent Disk** mounted at `/data`.
3. Set Build Command: `pip install -r requirements.txt`.
4. Set Start Command: `python execution/run.py`.
5. Add Environment Variables.

### 3. Go-Live Checklist
- [ ] `ENABLE_SENDING` set to `false` initially.
- [ ] Webhook set to `[BASE_URL]/twilio/inbound`.
- [ ] `/health` endpoint returns 200.
- [ ] Test flow: Inbound -> Draft -> Approval -> "SEND_BLOCKED" (Audit).
- [ ] Switch `ENABLE_SENDING` to `true` for live traffic.
