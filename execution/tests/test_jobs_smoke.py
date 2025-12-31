import unittest
import os
import sqlite3
import unittest.mock
from execution.jobs.job_01_ingest import ingest_message
from execution.jobs.job_02_enrich import process_enrichment
from execution.jobs.job_03_act import process_outbound_queue
from execution.utils.db import init_db, get_db_connection
import execution.config
import execution.connectors.twilio
from execution.connectors.twilio import TwilioConnector

# Mock Config
os.environ["DATABASE_PATH"] = ":memory:" 

class MvpSmokeTest(unittest.TestCase):
    
    def setUp(self):
        self.test_db = "execution/test_milo.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        
        # Monkey patch
        execution.config.DATABASE_PATH = self.test_db
        execution.utils.db.DATABASE_PATH = self.test_db
        # We need to ensure logic uses this path
        
        init_db()

    def tearDown(self):
        # Ensure file is released
        import gc
        gc.collect()
        if os.path.exists(self.test_db):
            try:
                os.remove(self.test_db)
            except PermissionError:
                pass 

    def test_ingest_deduplication(self):
        payload = {"MessageSid": "SM123", "From": "+15550001", "Body": "Test"}
        ingest_message(payload)
        ingest_message(payload) # Twice
        
        conn = get_db_connection()
        count = conn.execute("SELECT count(*) FROM messages WHERE id='SM123'").fetchone()[0]
        self.assertEqual(count, 1)
        conn.close()

    @unittest.mock.patch('execution.jobs.job_02_enrich.twilio_client.send_sms')
    @unittest.mock.patch('execution.jobs.job_02_enrich.openai_client')
    def test_enrich_creates_draft_and_notifies(self, mock_openai, mock_send_sms):
        # Config needs OWNER_PHONE_NUMBER
        with unittest.mock.patch('execution.jobs.job_02_enrich.OWNER_PHONE_NUMBER', '+1999999999'):
            # Mock Classification
            mock_classify = unittest.mock.Mock()
            choice_c = unittest.mock.Mock()
            choice_c.message.content = '{"language": "ES", "language_confidence": 0.9, "risk": "LOW", "risk_reason": "NONE", "intent": "KNOWN"}'
            mock_classify.choices = [choice_c]
            
            # Mock Drafting
            mock_draft = unittest.mock.Mock()
            choice_d = unittest.mock.Mock()
            choice_d.message.content = "Gracias. Un momento."
            mock_draft.choices = [choice_d]
            
            mock_openai.chat.completions.create.side_effect = [mock_classify, mock_draft]
            mock_send_sms.return_value = "SID_NOTIFY"

            ingest_message({"MessageSid": "SM_DRAFT_NOTIFY", "From": "+15550001", "Body": "Hola", "To": "+1000"})
            process_enrichment()
            
            # Verify Draft Created
            conn = get_db_connection()
            inbound = conn.execute("SELECT status FROM messages WHERE id='SM_DRAFT_NOTIFY'").fetchone()
            self.assertEqual(inbound['status'], 'DRAFT_PENDING_APPROVAL')
            
            # Verify Notification Sent
            mock_send_sms.assert_called_once()
            args, _ = mock_send_sms.call_args
            to_number, body = args
            self.assertEqual(to_number, '+1999999999')
            self.assertIn("DRAFT READY", body)
            self.assertIn("Gracias", body) # Draft content
            conn.close()

    @unittest.mock.patch('execution.jobs.job_02_enrich.twilio_client.send_sms')
    @unittest.mock.patch('execution.jobs.job_02_enrich.openai_client')
    def test_enrich_high_risk_notifies(self, mock_openai, mock_send_sms):
         with unittest.mock.patch('execution.jobs.job_02_enrich.OWNER_PHONE_NUMBER', '+1999999999'):
            # Mock Classification HIGH RISK
            mock_classify = unittest.mock.Mock()
            choice = unittest.mock.Mock()
            choice.message.content = '{"language": "EN", "language_confidence": 0.9, "risk": "HIGH", "risk_reason": "LEGAL", "intent": "KNOWN"}'
            mock_classify.choices = [choice]
            
            mock_openai.chat.completions.create.side_effect = [mock_classify]

            ingest_message({"MessageSid": "SM_RISK_NOTIFY", "From": "+15550004", "Body": "Urgent lawsuit"})
            process_enrichment()
            
            conn = get_db_connection()
            msg = conn.execute("SELECT status FROM messages WHERE id='SM_RISK_NOTIFY'").fetchone()
            self.assertEqual(msg['status'], 'NEEDS_REVIEW')
            
            # Verify Notification
            mock_send_sms.assert_called_once()
            args, _ = mock_send_sms.call_args
            to_number, body = args
            self.assertIn("NEEDS REVIEW", body)
            self.assertIn("Risk HIGH", body)
            self.assertIn("LEGAL", body)
            conn.close()
            
    @unittest.mock.patch('execution.jobs.job_02_enrich.twilio_client.send_sms')
    def test_enrich_notifications_idempotency(self, mock_send_sms):
         with unittest.mock.patch('execution.jobs.job_02_enrich.OWNER_PHONE_NUMBER', '+1999999999'):
             # Setup Audit Log with existing notification
             conn = get_db_connection()
             conn.execute("INSERT INTO messages (id, status, type, sender, body, thread_id, media) VALUES ('SM_DUP', 'RECEIVED', 'INBOUND', '+1555', 'Bad', '+1555', '{}')")
             conn.execute("INSERT INTO audit_log (id, event, actor, metadata, timestamp) VALUES ('1', 'OWNER_NOTIFIED_NEEDS_REVIEW', 'SYSTEM', '{\"msg_id\": \"SM_DUP\"}', '2025-01-01')")
             conn.commit()
             conn.close()
             
             # Process should route to review but SKIP notification
             process_enrichment()
             
             mock_send_sms.assert_not_called()


    @unittest.mock.patch('execution.jobs.job_02_enrich.openai_client')
    def test_enrich_low_confidence(self, mock_openai):
        # Mock Classification LOW CONFIDENCE
        mock_classify = unittest.mock.Mock()
        choice = unittest.mock.Mock()
        choice.message.content = '{"language": "ES", "language_confidence": 0.4, "risk": "LOW", "risk_reason": "NONE", "intent": "KNOWN"}'
        mock_classify.choices = [choice]
        
        mock_openai.chat.completions.create.side_effect = [mock_classify]

        ingest_message({"MessageSid": "SM_LOW", "From": "+15550005", "Body": "asdfg"})
        process_enrichment()
        
        conn = get_db_connection()
        msg = conn.execute("SELECT status FROM messages WHERE id='SM_LOW'").fetchone()
        self.assertEqual(msg['status'], 'NEEDS_REVIEW')
        conn.close()


    def test_paused_thread_routing(self):
        # Pause thread +15550002
        conn = get_db_connection()
        conn.execute("INSERT INTO thread_controls (thread_id, paused) VALUES (?, ?)", ("+15550002", True))
        conn.commit()
        conn.close()

        ingest_message({"MessageSid": "SM_PAUSE", "From": "+15550002", "Body": "Hello"})
        
        # Enrich should SKIP drafting and route to NEEDS_REVIEW
        process_enrichment()
        
        conn = get_db_connection()
        msg = conn.execute("SELECT status FROM messages WHERE id='SM_PAUSE'").fetchone()
        self.assertEqual(msg['status'], 'NEEDS_REVIEW')
        
        draft_count = conn.execute("SELECT count(*) FROM messages WHERE type='DRAFT'").fetchone()[0]
        self.assertEqual(draft_count, 0)
        conn.close()

    def test_approval_gating(self):
        # Create a DRAFT_PENDING_APPROVAL message
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO messages (id, status, type, body, receiver) 
            VALUES ('DRAFT_1', 'DRAFT_PENDING_APPROVAL', 'DRAFT', 'Hi', '+15550003')
        """)
        conn.commit()
        conn.close()

        # Run Polling (Act)
        # Should NOT send
        with unittest.mock.patch('execution.jobs.job_03_act.twilio.send_sms') as mock_send:
            process_outbound_queue()
            mock_send.assert_not_called()

    def test_send_failure_handling(self):
        # Create APPROVED message
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO messages (id, status, type, body, receiver) 
            VALUES ('DRAFT_SEND', 'APPROVED_TO_SEND', 'DRAFT', 'Hi', '+15550003')
        """)
        conn.commit()
        conn.close()

        # Mock Twilio to raise Exception & ENABLE_SENDING=True
        with unittest.mock.patch('execution.jobs.job_03_act.twilio.send_sms') as mock_send, \
             unittest.mock.patch('execution.jobs.job_03_act.ENABLE_SENDING', True):
             
            mock_send.side_effect = Exception("Twilio Down")
            process_outbound_queue()
        
        conn = get_db_connection()
        msg = conn.execute("SELECT status FROM messages WHERE id='DRAFT_SEND'").fetchone()
        self.assertEqual(msg['status'], 'FAILED_SEND')
        conn.close()


if __name__ == '__main__':
    unittest.main()
