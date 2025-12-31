import time
import uuid
from datetime import datetime, timezone
from execution.utils.db import get_db_connection
from execution.utils.logging import logger
from execution.connectors.twilio import TwilioConnector
from execution.config import POLLING_INTERVAL, ENABLE_SENDING

twilio = TwilioConnector()

def run_polling_loop():
    """
    Poller that checks for APPROVED_TO_SEND messages and sends them.
    Runs indefinitely (blocking), so should be threaded.
    """
    logger.info(f"Starting Polling Loop... Sending Enabled: {ENABLE_SENDING}")
    while True:
        try:
            process_outbound_queue()
        except Exception as e:
            logger.error(f"Polling loop crash: {e}")
        
        time.sleep(POLLING_INTERVAL)

def process_outbound_queue():
    conn = get_db_connection()
    c = conn.cursor()
    
    # Criteria: APPROVED_TO_SEND
    c.execute("SELECT * FROM messages WHERE status = 'APPROVED_TO_SEND'")
    rows = c.fetchall()
    
    if rows:
        logger.info(f"Found {len(rows)} messages to send.")
    
    for row in rows:
        msg_id = row['id']
        receiver = row['receiver']
        body = row['body']
        
        # Kill Switch Check
        if not ENABLE_SENDING:
            logger.warning(f"SEND BLOCKED (Kill Switch) for {msg_id}")
            now_ui = datetime.now(timezone.utc).isoformat()
            
            # Log Audit
            audit_id = str(uuid.uuid4())
            c.execute("INSERT INTO audit_log (id, event, actor, metadata, timestamp) VALUES (?, ?, ?, ?, ?)",
                      (audit_id, "SEND_BLOCKED_KILL_SWITCH", "SYSTEM", f'{{"msg_id": "{msg_id}"}}', now_ui))
            
            # Reset status to stop loop
            c.execute("UPDATE messages SET status = 'NEEDS_REVIEW' WHERE id = ?", (msg_id,))
            conn.commit()
            continue

        try:
            # Send
            sid = twilio.send_sms(receiver, body)
            
            # Update DB
            now_ui = datetime.now(timezone.utc).isoformat()
            new_status = 'SENT'
            
            c.execute("UPDATE messages SET status = ?, timestamp = ? WHERE id = ?", (new_status, now_ui, msg_id))
            
            # Audit
            audit_id = str(uuid.uuid4())
            c.execute("INSERT INTO audit_log (id, event, actor, metadata, timestamp) VALUES (?, ?, ?, ?, ?)",
                      (audit_id, "MESSAGE_SENT", "SYSTEM", f'{{"sid": "{sid}", "msg_id": "{msg_id}"}}', now_ui))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to send {msg_id}: {e}")
            c.execute("UPDATE messages SET status = 'FAILED_SEND' WHERE id = ?", (msg_id,))
            conn.commit()
            
    conn.close()
