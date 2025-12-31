import threading
import flask
from flask import request, jsonify
from execution.utils.logging import logger
from execution.utils.db import init_db
from execution.config import BASE_URL, OWNER_PHONE_NUMBER
from execution.jobs.job_01_ingest import ingest_message
from execution.jobs.job_02_enrich import process_enrichment
from execution.jobs.job_03_act import run_polling_loop

app = flask.Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/twilio/inbound', methods=['POST'])
def inbound_webhook():
    """
    Handle inbound messages from Twilio.
    Supports both Customer Ingest AND Owner Commands (Single Number).
    """
    try:
        data = request.values.to_dict()
        sender = data.get('From')
        logger.info(f"Inbound Webhook: {data.get('MessageSid')} from {sender}")
        
        # Check if Owner
        if sender == OWNER_PHONE_NUMBER:
            logger.info("Sender is Owner. Processing as Command.")
            return process_owner_command(data)
        
        # 1. Ingest
        ingest_message(data)
        
        # 2. Enrich (Synchronous for MVP simplicity)
        process_enrichment()
        
        return "", 200
    except Exception as e:
        logger.error(f"Webhook Error: {e}")
        return "", 500

@app.route('/twilio/owner', methods=['POST'])
def owner_webhook():
    """
    Optional: Direct endpoint for Owner Commands.
    """
    try:
        data = request.values.to_dict()
        return process_owner_command(data)
    except Exception as e:
        logger.error(f"Owner Webhook Error: {e}")
        return "", 500

def process_owner_command(data):
    """
    Core logic for handling A/R/E commands.
    """
    sender = data.get('From')
    body = data.get('Body', '').strip()
    
    # Double check sender just in case (though caller should have checked)
    if sender != OWNER_PHONE_NUMBER:
        logger.warning(f"Unauthorized Command from {sender}")
        return "", 403
        
    logger.info(f"Owner Command: {body}")
    
    # Parse logic
    # A <id> | R <id> | E <id> <text>
    parts = body.split(' ', 2)
    cmd = parts[0].upper()
    
    if len(parts) < 2:
            logger.info("Invalid command format")
            return "", 200 
            
    msg_id = parts[1]
    
    from execution.utils.db import get_db_connection
    conn = get_db_connection()
    c = conn.cursor()
    
    if cmd == 'A':
        # Approve
        c.execute("UPDATE messages SET status = 'APPROVED_TO_SEND' WHERE id = ?", (msg_id,))
        logger.info(f"Owner APPROVED {msg_id}")
    elif cmd == 'R':
        # Reject
        c.execute("UPDATE messages SET status = 'REJECTED' WHERE id = ?", (msg_id,))
        logger.info(f"Owner REJECTED {msg_id}")
    elif cmd == 'E' and len(parts) == 3:
        # Edit
        new_text = parts[2]
        c.execute("SELECT draft_version FROM messages WHERE id = ?", (msg_id,))
        row = c.fetchone()
        if row:
            new_ver = row['draft_version'] + 1
            c.execute("UPDATE messages SET body = ?, status = 'DRAFT_PENDING_APPROVAL', draft_version = ? WHERE id = ?", 
                        (new_text, new_ver, msg_id))
            logger.info(f"Owner EDITED {msg_id}")
    
    conn.commit()
    conn.close()
    
    return "", 200

def main():
    logger.info("MILO System Starting...")
    
    # 1. DB Init
    init_db()
    
    # 2. Start Polling Thread
    t = threading.Thread(target=run_polling_loop, daemon=True)
    t.start()
    
    # 3. Start Server
    # MVP: Debug=False, Port=5000
    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()
