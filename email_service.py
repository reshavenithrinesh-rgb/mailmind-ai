import os
import base64
from email.mime.text import MIMEText

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


# Gmail permissions
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# File paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")


def get_gmail_service():
    """
    Authenticate with Gmail API and return Gmail service.
    """

    creds = None

    # Load previously saved token
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES
        )

    # Refresh or create new authorization
    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE,
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        # Save token for future use
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return build(
        "gmail",
        "v1",
        credentials=creds
    )


def get_unread_emails():
    """
    Get unread emails from Gmail inbox.
    """

    service = get_gmail_service()

    results = service.users().messages().list(
        userId="me",
        labelIds=["INBOX", "UNREAD"],
        maxResults=20
    ).execute()

    messages = results.get("messages", [])

    emails = []

    for message in messages:

        msg = service.users().messages().get(
            userId="me",
            id=message["id"],
            format="full"
        ).execute()

        headers = msg["payload"].get("headers", [])

        sender = ""
        subject = ""

        for header in headers:

            if header["name"].lower() == "from":
                sender = header["value"]

            if header["name"].lower() == "subject":
                subject = header["value"]

        body = extract_email_body(msg["payload"])

        emails.append({
            "id": message["id"],
            "threadId": msg["threadId"],
            "sender": sender,
            "subject": subject,
            "body": body
        })

    return emails


def extract_email_body(payload):
    """
    Extract plain-text body from Gmail message payload.
    """

    body = ""

    if "parts" in payload:

        for part in payload["parts"]:

            if part["mimeType"] == "text/plain":

                data = part["body"].get("data")

                if data:
                    body = base64.urlsafe_b64decode(
                        data
                    ).decode(
                        "utf-8",
                        errors="ignore"
                    )

                    return body

            elif "parts" in part["body"]:

                body = extract_email_body(part)

                if body:
                    return body

    else:

        data = payload["body"].get("data")

        if data:
            body = base64.urlsafe_b64decode(
                data
            ).decode(
                "utf-8",
                errors="ignore"
            )

    return body


def send_reply(message_id, thread_id, reply_text):
    """
    Send a reply to an existing Gmail message.

    Parameters:
        message_id: Gmail message ID
        thread_id: Gmail thread ID
        reply_text: AI-generated reply text
    """

    service = get_gmail_service()

    # Get original email information
    original = service.users().messages().get(
        userId="me",
        id=message_id,
        format="metadata",
        metadataHeaders=["From", "Subject"]
    ).execute()

    headers = original["payload"]["headers"]

    sender = ""
    subject = ""

    for header in headers:

        if header["name"].lower() == "from":
            sender = header["value"]

        if header["name"].lower() == "subject":
            subject = header["value"]

    # Create reply email
    message = MIMEText(reply_text)

    message["To"] = sender

    if subject.lower().startswith("re:"):
        message["Subject"] = subject
    else:
        message["Subject"] = "Re: " + subject

    # Convert email to Gmail raw format
    raw_message = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    # Gmail API request body
    body = {
        "raw": raw_message,
        "threadId": thread_id
    }

    # Send email
    sent = service.users().messages().send(
        userId="me",
        body=body
    ).execute()

    return sent


def mark_as_read(message_id):
    """
    Mark a Gmail message as read.
    """

    service = get_gmail_service()

    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "removeLabelIds": ["UNREAD"]
        }
    ).execute()


def mark_as_unread(message_id):
    """
    Mark a Gmail message as unread.
    """

    service = get_gmail_service()

    service.users().messages().modify(
        userId="me",
        id=message_id,
        body={
            "addLabelIds": ["UNREAD"]
        }
    ).execute()


def test_gmail_connection():
    """
    Simple Gmail connection test.
    """

    try:
        service = get_gmail_service()

        profile = service.users().getProfile(
            userId="me"
        ).execute()

        print("Gmail connection successful!")
        print("Email:", profile.get("emailAddress"))

        return True

    except Exception as e:

        print("Gmail connection failed!")
        print("Error:", e)

        return False


if __name__ == "__main__":

    print("Testing Gmail connection...")

    test_gmail_connection()