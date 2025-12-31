import uuid
import json
from datetime import datetime, timezone
from execution.utils.db import get_db_connection
from execution.utils.logging import logger
from execution.config import openai_client, OPENAI_MODEL, MAX_TOKENS, OPENAI_TIMEOUT

def process_enrichment():
    """
    Scans for RECEIVED messages and generates drafts using OpenAI.
    """
    conn = get_db_connection()
    c = conn.cursor()
    
    # Find RECEIVED messages
    c.execute("SELECT * FROM messages WHERE status = 'RECEIVED' AND type = 'INBOUND'")
    rows = c.fetchall()
    
    for row in rows:
        msg_id = row['id']
        sender = row['sender']
        body = row['body'] or ""
        media = row['media']
        thread_id = row['thread_id']
        
        # Thread Paused Check
        c.execute("SELECT paused FROM thread_controls WHERE thread_id = ?", (thread_id,))
        tc = c.fetchone()
        if tc and tc['paused']:
             logger.info(f"Thread {thread_id} paused. Routing {msg_id} to NEEDS_REVIEW.")
             update_status(conn, msg_id, "NEEDS_REVIEW")
             continue

        # Rule 3: Media/Body Check
        if media != "{}" or not body.strip():
            logger.info(f"Message {msg_id} has media or empty body. Routing to NEEDS_REVIEW.")
            update_status(conn, msg_id, "NEEDS_REVIEW")
            continue
            
        # AI Classification & Drafting
        try:
            if not openai_client:
                 raise Exception("OpenAI Client not initialized (Missing Key)")

            # 1. Classification
            classification = classify_message(body)
            
            lang = classification.get("language", "UNCLEAR")
            confidence = classification.get("language_confidence", 0.0)
            risk = classification.get("risk", "HIGH") # Fail safe
            risk_reason = classification.get("risk_reason", "NONE")
            intent = classification.get("intent", "UNKNOWN")
            
            logger.info(f"Classified {msg_id}: Lang={lang} ({confidence}), Risk={risk} ({risk_reason}), Intent={intent}")

            # Guardrails (Strict)
            # Language Check
            if lang not in ["EN", "ES"] or lang == "UNCLEAR":
                logger.info(f"Language {lang} not supported/unclear. Needs Review.")
                update_status(conn, msg_id, "NEEDS_REVIEW")
                continue
                
            if confidence < 0.75:
                 logger.info(f"Language Confidence Low ({confidence}). Needs Review.")
                 update_status(conn, msg_id, "NEEDS_REVIEW")
                 continue

            # Risk Check
            if risk == "HIGH":
                logger.info(f"Risk HIGH ({risk_reason}) for {msg_id}. Needs Review.")
                update_status(conn, msg_id, "NEEDS_REVIEW")
                continue
            
            # Intent Check    
            if intent == "UNKNOWN":
                logger.info(f"Intent UNKNOWN for {msg_id}. Needs Review.")
                update_status(conn, msg_id, "NEEDS_REVIEW")
                continue
                
            # 2. Drafting
            draft_body = generate_draft(body, lang, intent)

            # Generate Draft
            draft_id = str(uuid.uuid4())
            now_ui = datetime.now(timezone.utc).isoformat()
        
            # Save Draft
            c.execute("""
                INSERT INTO messages (id, thread_id, in_reply_to_id, sender, receiver, body, media, status, type, timestamp, draft_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                draft_id,
                thread_id,
                msg_id,
                "SYSTEM", 
                sender,   
                draft_body,
                "{}",
                "DRAFT_PENDING_APPROVAL",
                "DRAFT",
                now_ui,
                1
            ))
            
            update_status(conn, msg_id, "DRAFT_PENDING_APPROVAL") 
            logger.info(f"Generated draft {draft_id} for message {msg_id}")

        except Exception as e:
            logger.error(f"AI Enrichment failed for {msg_id}: {e}")
            update_status(conn, msg_id, "NEEDS_REVIEW")
            
    conn.commit()
    conn.close()

def classify_message(body):
    """
    Returns strict JSON: {language, language_confidence, risk, risk_reason, intent}
    """
    system_prompt = """You are a classification engine. Analyze the inbound text.
Return ONLY a JSON object with keys:
- language: "EN", "ES", or "UNCLEAR"
- language_confidence: Float 0.0 to 1.0
- risk: "LOW" (normal business) or "HIGH" (harmful, legal threat, emergency, sensitive)
- risk_reason: "PAYMENT", "LEGAL", "HARASSMENT", "MEDICAL", "MINOR", "REFUND", "THREAT", "OTHER", "NONE"
- intent: "KNOWN" (scheduling, pricing, faq) or "UNKNOWN" (confusing, unrelated)
"""
    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": body}
        ],
        max_tokens=MAX_TOKENS,
        temperature=0,
        timeout=OPENAI_TIMEOUT
    )
    
    content = response.choices[0].message.content.strip()
    if content.startswith("```json"):
        content = content[7:-3]
    return json.loads(content)

def generate_draft(body, lang, intent):
    """
    Generates a polite business reply.
    """
    lang_instruction = "English" if lang == "EN" else "Spanish"
    
    system_prompt = f"""You are a helpful business assistant. Write a polite, neutral reply in {lang_instruction}.
Rules:
1. Reference business context generically (do not invent facts).
2. Ask NO MORE than ONE question.
3. If intent is KNOWN but details are missing, end with a simple next step (e.g. "What day/time works for you?").
4. Keep it short (1-2 sentences).
"""
    response = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": body}
        ],
        max_tokens=MAX_TOKENS,
        temperature=0.3,
        timeout=OPENAI_TIMEOUT
    )
    return response.choices[0].message.content.strip()

def update_status(conn, msg_id, status):
    c = conn.cursor()
    c.execute("UPDATE messages SET status = ? WHERE id = ?", (status, msg_id))

