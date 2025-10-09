"""
Emails.py (FIXED)
Email processing with proper error handling and send_reply function
"""

import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from Logs import EliteLogger

logger = EliteLogger()


def classify_email(subject, body):
    """
    Simple email classification
    TODO: Replace with AI classification
    """
    text = (subject or "") + " " + (body or "")
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["appointment", "meeting", "schedule", "book"]):
        return "lead"
    return "non-lead"


def send_email(account, to_email, subject, body):
    """
    Send an email using the configured account
    Args:
        account: Email config dict with provider, smtp settings, credentials
        to_email: Recipient email address
        subject: Email subject
        body: Email body text
    """
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = account["email"]
        msg["To"] = to_email

        if account["provider"] == "gmail":
            with smtplib.SMTP_SSL(account["smtp_host"], account["smtp_port"]) as server:
                server.login(account["email"], account["password"])
                server.sendmail(account["email"], [to_email], msg.as_string())
                logger.success(f"Email sent to {to_email} via Gmail")
        else:  # Outlook
            with smtplib.SMTP(account["smtp_host"], account["smtp_port"]) as server:
                server.starttls()
                server.login(account["email"], account["password"])
                server.sendmail(account["email"], [to_email], msg.as_string())
                logger.success(f"Email sent to {to_email} via Outlook")
        
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}", context={"error": str(e)})
        return False


def send_reply(account, to_email, subject, body):
    """
    Alias for send_email for backward compatibility
    """
    return send_email(account, to_email, subject, body)


def process_email(account):
    """
    Fetch unseen emails from the inbox, classify them,
    and return actions based on content.
    Args:
        account: Email config dict with provider, imap settings, credentials
    Returns:
        List of email dicts with sender, subject, body, classification
    """
    try:
        mail = imaplib.IMAP4_SSL(account["imap_host"])
        mail.login(account["email"], account["password"])
        mail.select("inbox")

        status, messages = mail.search(None, "UNSEEN")
        results = []

        if status != "OK":
            logger.warning("No unseen messages found")
            mail.logout()
            return results

        message_nums = messages[0].split()
        
        if not message_nums:
            logger.info("Inbox is empty")
            mail.logout()
            return results

        for num in message_nums:
            try:
                status, msg_data = mail.fetch(num, "(RFC822)")
                
                if status != "OK":
                    continue
                    
                msg = email.message_from_bytes(msg_data[0][1])

                sender = msg["from"]
                subject = msg["subject"] or "(No Subject)"
                body = ""

                # Extract body
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            try:
                                body = part.get_payload(decode=True).decode(errors="ignore")
                                break
                            except:
                                continue
                else:
                    try:
                        body = msg.get_payload(decode=True).decode(errors="ignore")
                    except:
                        body = ""

                classification = classify_email(subject, body)
                
                results.append({
                    "from": sender,
                    "subject": subject,
                    "body": body,
                    "classification": classification
                })
                
                logger.info(f"Processed email from {sender} - {classification}")
                
            except Exception as e:
                logger.error("Error processing individual email", context={"error": str(e)})
                continue

        mail.logout()
        return results
        
    except Exception as e:
        logger.error("Email processing error", context={"error": str(e)})
        return []