from datetime import datetime, timezone
import uuid
from execution.utils.db import get_db_connection
from execution.utils.logging import logger

def ingest_message(payload):
    """
    Ingests an inbound message from Twilio webhook.
    Idempotent based on MessageSid.
    """
    message_sid = payload.get('MessageSid')
    sender = payload.get('From')
    body = payload.get('Body')
    num_media = int(payload.get('NumMedia', 0))
    media_url = payload.get('MediaUrl0') # Keep it simple for MVP
    
    conn = get_db_connection()
    c = conn.cursor()
    
    # Idempotency Check
    c.execute("SELECT id FROM messages WHERE id = ?", (message_sid,))
    if c.fetchone():
        logger.info(f"Duplicate MessageSid {message_sid}. Ignoring.")
        conn.close()
        return
        
    # Thread Control Check
    # Thread ID is just the sender phone number for MVP
    thread_id = sender
    c.execute("SELECT paused FROM thread_controls WHERE thread_id = ?", (thread_id,))
    row = c.fetchone()
    if row and row['paused']:
        logger.info(f"Thread {thread_id} is PAUSED. Logging only.")
        # We still save it, but we might want a different status? 
        # Directive says "Status=RECEIVED (Log only, do not draft)".
        # We'll save as RECEIVED, enrich job handles the "do not draft" logic via paused check logic or we handle it here?
        # Logic says: "Enrich routes messages". So we save as RECEIVED here.
        pass

    media_json = "{}" 
    if num_media > 0 and media_url:
        media_json = f'{{"url": "{media_url}"}}'

    # Insert
    try:
        now_ui = datetime.now(timezone.utc).isoformat()
        c.execute("""
            INSERT INTO messages (id, thread_id, sender, receiver, body, media, status, type, timestamp, draft_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            message_sid,
            thread_id,
            sender,
            payload.get('To'),
            body,
            media_json,
            "RECEIVED",
            "INBOUND",
            now_ui,
            0 # Inbound ver is 0
        ))
        
        # Audit Log
        audit_id = str(uuid.uuid4())
        c.execute("INSERT INTO audit_log (id, event, actor, metadata, timestamp) VALUES (?, ?, ?, ?, ?)",
                  (audit_id, "MESSAGE_RECEIVED", "SYSTEM", f'{{"sid": "{message_sid}"}}', now_ui))
        
        conn.commit()
        logger.info(f"Ingested message {message_sid} from {sender}")
        
    except Exception as e:
        logger.error(f"Error ingesting message: {e}")
    finally:
        conn.close()
