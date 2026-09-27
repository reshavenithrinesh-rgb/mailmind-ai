import os
import base64
import html
import re
from email.mime.text import MIMEText
from email.utils import parseaddr

import streamlit as st

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google import genai


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Automatic Mail Responder",
    page_icon="📧",
    layout="wide"
)


# ============================================================
# CONFIGURATION
# ============================================================

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CREDENTIALS_FILE = os.path.join(
    BASE_DIR,
    "credentials.json"
)

TOKEN_FILE = os.path.join(
    BASE_DIR,
    "token.json"
)


# ============================================================
# SECURE CLOUD SECRETS
# ============================================================

# Local:
#   Uses GEMINI_API_KEY environment variable.
#
# Streamlit Cloud:
#   Uses GEMINI_API_KEY from Streamlit Secrets.

try:
    GEMINI_API_KEY = st.secrets.get(
        "GEMINI_API_KEY",
        os.getenv("GEMINI_API_KEY")
    )
except Exception:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")


# ------------------------------------------------------------
# Recreate Google OAuth files from Streamlit Secrets
# ------------------------------------------------------------

try:

    if "CREDENTIALS_JSON" in st.secrets:

        credentials_json = st.secrets["CREDENTIALS_JSON"]

        if not os.path.exists(CREDENTIALS_FILE):

            with open(
                CREDENTIALS_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(credentials_json)


    if "TOKEN_JSON" in st.secrets:

        token_json = st.secrets["TOKEN_JSON"]

        if not os.path.exists(TOKEN_FILE):

            with open(
                TOKEN_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(token_json)

except Exception as e:

    st.warning(
        f"Cloud credential setup warning: {e}"
    )


# ============================================================
# SESSION STATE
# ============================================================

if "gmail_service" not in st.session_state:
    st.session_state.gmail_service = None

if "emails" not in st.session_state:
    st.session_state.emails = []

if "email_states" not in st.session_state:
    st.session_state.email_states = {}

if "test_emails" not in st.session_state:
    st.session_state.test_emails = []


# ============================================================
# CUSTOM STYLE
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 40px;
        font-weight: 700;
        margin-bottom: 5px;
    }

    .subtitle {
        color: #9aa0a6;
        font-size: 16px;
        margin-bottom: 25px;
    }

    .reply-box {
        padding: 20px;
        border-radius: 12px;
        background-color: #075985;
        margin-top: 15px;
        white-space: pre-wrap;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SESSION EMAIL STATE
# ============================================================

def get_email_state(email_id):

    if email_id not in st.session_state.email_states:

        st.session_state.email_states[email_id] = {
            "reply": "",
            "status": "Pending",
            "edited": False,
            "sent": False
        }

    return st.session_state.email_states[email_id]


# ============================================================
# GMAIL AUTHENTICATION
# ============================================================

def get_gmail_service():

    creds = None

    # --------------------------------------------------------
    # Load existing token
    # --------------------------------------------------------

    if os.path.exists(TOKEN_FILE):

        try:

            creds = Credentials.from_authorized_user_file(
                TOKEN_FILE,
                GMAIL_SCOPES
            )

        except Exception:

            creds = None

    # --------------------------------------------------------
    # Refresh expired token
    # --------------------------------------------------------

    if creds and creds.expired and creds.refresh_token:

        try:

            creds.refresh(Request())

            # Save refreshed token
            with open(
                TOKEN_FILE,
                "w",
                encoding="utf-8"
            ) as token:

                token.write(
                    creds.to_json()
                )

        except Exception:

            creds = None

    # --------------------------------------------------------
    # Login if required
    # --------------------------------------------------------

    if not creds or not creds.valid:

        if not os.path.exists(CREDENTIALS_FILE):

            st.error(
                "Google OAuth credentials are not configured.\n\n"
                "Please add CREDENTIALS_JSON and TOKEN_JSON "
                "to Streamlit Cloud Secrets."
            )

            st.stop()

        st.info(
            "Google Gmail authentication is required."
        )

        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE,
            GMAIL_SCOPES
        )

        creds = flow.run_local_server(
            port=0
        )

        with open(
            TOKEN_FILE,
            "w",
            encoding="utf-8"
        ) as token:

            token.write(
                creds.to_json()
            )

    # --------------------------------------------------------
    # Create Gmail service
    # --------------------------------------------------------

    try:

        service = build(
            "gmail",
            "v1",
            credentials=creds
        )

        return service

    except Exception as e:

        st.error(
            f"Could not connect to Gmail: {e}"
        )

        st.stop()


# ============================================================
# GET EMAIL HEADER
# ============================================================

def get_header(headers, name):

    for header in headers:

        if header.get(
            "name",
            ""
        ).lower() == name.lower():

            return header.get(
                "value",
                ""
            )

    return ""


# ============================================================
# DECODE GMAIL BODY
# ============================================================

def decode_body(data):

    if not data:
        return ""

    try:

        decoded = base64.urlsafe_b64decode(
            data + "=" * (-len(data) % 4)
        )

        return decoded.decode(
            "utf-8",
            errors="ignore"
        )

    except Exception:

        return ""


# ============================================================
# REMOVE HTML
# ============================================================

def clean_html(text):

    if not text:
        return ""

    text = html.unescape(text)

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"</p>",
        "\n",
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r"<[^>]+>",
        "",
        text
    )

    return text.strip()


# ============================================================
# EXTRACT EMAIL BODY
# ============================================================

def extract_body(payload):

    if not payload:
        return ""

    mime_type = payload.get(
        "mimeType",
        ""
    )

    body = payload.get(
        "body",
        {}
    )

    data = body.get(
        "data"
    )

    # --------------------------------------------------------
    # Plain text
    # --------------------------------------------------------

    if mime_type == "text/plain" and data:

        return decode_body(data)

    # --------------------------------------------------------
    # HTML
    # --------------------------------------------------------

    if mime_type == "text/html" and data:

        return clean_html(
            decode_body(data)
        )

    # --------------------------------------------------------
    # Multipart
    # --------------------------------------------------------

    parts = payload.get(
        "parts",
        []
    )

    plain_text = ""
    html_text = ""

    for part in parts:

        part_mime = part.get(
            "mimeType",
            ""
        )

        part_body = part.get(
            "body",
            {}
        )

        part_data = part_body.get(
            "data"
        )

        if part_mime == "text/plain" and part_data:

            plain_text += decode_body(
                part_data
            )

        elif part_mime == "text/html" and part_data:

            html_text += decode_body(
                part_data
            )

        elif part.get("parts"):

            nested = extract_body(
                part
            )

            if nested:

                plain_text += nested

    if plain_text.strip():

        return plain_text.strip()

    if html_text.strip():

        return clean_html(
            html_text
        )

    return ""


# ============================================================
# FETCH REAL GMAIL INBOX
# ============================================================

def fetch_gmail_emails(
    service,
    max_results=25
):

    emails = []

    try:

        response = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=max_results
            )
            .execute()
        )

        messages = response.get(
            "messages",
            []
        )

        if not messages:

            return []

        for message in messages:

            message_id = message["id"]

            try:

                full_message = (
                    service.users()
                    .messages()
                    .get(
                        userId="me",
                        id=message_id,
                        format="full"
                    )
                    .execute()
                )

                payload = full_message.get(
                    "payload",
                    {}
                )

                headers = payload.get(
                    "headers",
                    []
                )

                sender = get_header(
                    headers,
                    "From"
                )

                subject = get_header(
                    headers,
                    "Subject"
                )

                date = get_header(
                    headers,
                    "Date"
                )

                message_id_header = get_header(
                    headers,
                    "Message-ID"
                )

                references = get_header(
                    headers,
                    "References"
                )

                body = extract_body(
                    payload
                )

                snippet = full_message.get(
                    "snippet",
                    ""
                )

                email_data = {

                    "id": message_id,

                    "thread_id":
                        full_message.get(
                            "threadId",
                            ""
                        ),

                    "from": sender,

                    "subject":
                        subject
                        if subject
                        else "(No Subject)",

                    "date": date,

                    "message_id_header":
                        message_id_header,

                    "references":
                        references,

                    "body":
                        body
                        if body
                        else snippet,

                    "snippet":
                        snippet,

                    "label_ids":
                        full_message.get(
                            "labelIds",
                            []
                        )
                }

                emails.append(
                    email_data
                )

                get_email_state(
                    message_id
                )

            except Exception as e:

                print(
                    f"Could not read message "
                    f"{message_id}: {e}"
                )

        return emails

    except HttpError as e:

        st.error(
            f"Gmail API error: {e}"
        )

        return []


# ============================================================
# GEMINI AI REPLY
# ============================================================

def generate_ai_reply(
    sender,
    subject,
    body
):

    if not GEMINI_API_KEY:

        return None, (
            "GEMINI_API_KEY is not available."
        )

    try:

        client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        prompt = f"""
You are an AI email assistant.

Write a professional and natural reply to the email below.

Rules:
- Be polite.
- Be concise.
- Do not invent facts.
- Answer only using information available in the email.
- Do not mention that you are an AI.
- Do not add unnecessary explanations.
- Return ONLY the email body.
- Do not include a subject line.

Sender:
{sender}

Subject:
{subject}

Email:
{body}
"""

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )

        reply = response.text.strip()

        if not reply:

            return None, (
                "Gemini returned an empty reply."
            )

        return reply, None

    except Exception as e:

        return None, (
            f"Gemini error: {e}"
        )


# ============================================================
# SEND REAL GMAIL REPLY
# ============================================================

def send_gmail_reply(
    service,
    original_email,
    reply_text
):

    try:

        sender = original_email["from"]

        sender_name, sender_email = parseaddr(
            sender
        )

        if not sender_email:

            return False, (
                "Could not determine "
                "sender email address."
            )

        subject = original_email["subject"]

        if not subject.lower().startswith("re:"):

            reply_subject = (
                f"Re: {subject}"
            )

        else:

            reply_subject = subject

        message = MIMEText(
            reply_text,
            "plain",
            "utf-8"
        )

        message["To"] = sender_email

        message["Subject"] = reply_subject

        original_message_id = (
            original_email.get(
                "message_id_header",
                ""
            )
        )

        references = (
            original_email.get(
                "references",
                ""
            )
        )

        # ----------------------------------------------------
        # Gmail threading headers
        # ----------------------------------------------------

        if original_message_id:

            message["In-Reply-To"] = (
                original_message_id
            )

            if references:

                message["References"] = (
                    references
                    + " "
                    + original_message_id
                )

            else:

                message["References"] = (
                    original_message_id
                )

        # ----------------------------------------------------
        # Encode message
        # ----------------------------------------------------

        raw_message = (
            base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()
        )

        send_body = {
            "raw": raw_message,
            "threadId":
                original_email["thread_id"]
        }

        sent_message = (
            service.users()
            .messages()
            .send(
                userId="me",
                body=send_body
            )
            .execute()
        )

        return True, sent_message.get(
            "id",
            ""
        )

    except HttpError as e:

        return False, (
            f"Gmail send error: {e}"
        )

    except Exception as e:

        return False, str(e)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title(
        "📧 Navigation"
    )

    page = st.radio(
        "Go to",
        [
            "Dashboard",
            "Email Inbox",
            "Add Test Email"
        ]
    )

    st.divider()

    st.caption(
        "Automatic Mail Responder"
    )

    st.caption(
        "AI-powered email management system"
    )


# ============================================================
# DASHBOARD
# ============================================================

if page == "Dashboard":

    st.markdown(
        '<div class="main-title">'
        '📧 Automatic Mail Responder'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="subtitle">'
        'AI-powered Gmail email management system'
        '</div>',
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # Gmail connection
    # --------------------------------------------------------

    try:

        service = get_gmail_service()

        st.session_state.gmail_service = service

        st.success(
            "✅ Gmail connected successfully"
        )

    except Exception as e:

        st.error(
            f"Gmail connection failed: {e}"
        )

    st.divider()

    st.subheader(
        "How it works"
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.info(
            "📥\n\n"
            "**1. Read Gmail**\n\n"
            "The application reads emails "
            "from your real Gmail Inbox."
        )

    with col2:

        st.info(
            "🤖\n\n"
            "**2. Generate AI Reply**\n\n"
            "Gemini analyzes the email and "
            "creates a professional reply."
        )

    with col3:

        st.info(
            "✏️\n\n"
            "**3. Edit & Review**\n\n"
            "You can modify the AI-generated "
            "reply before sending."
        )

    st.divider()

    st.subheader(
        "📊 Session Statistics"
    )

    all_emails = st.session_state.emails

    total = len(all_emails)

    generated = 0
    sent = 0
    rejected = 0
    pending = 0

    for email in all_emails:

        state = get_email_state(
            email["id"]
        )

        if state["reply"]:

            generated += 1

        if state["sent"]:

            sent += 1

        elif state["status"] == "Rejected":

            rejected += 1

        else:

            pending += 1

    c1, c2, c3, c4 = st.columns(4)

    with c1:

        st.metric(
            "Emails",
            total
        )

    with c2:

        st.metric(
            "AI Replies",
            generated
        )

    with c3:

        st.metric(
            "Sent",
            sent
        )

    with c4:

        st.metric(
            "Pending",
            pending
        )

    st.divider()

    if st.button(
        "📥 Load Gmail Inbox",
        use_container_width=True
    ):

        service = get_gmail_service()

        with st.spinner(
            "Reading Gmail Inbox..."
        ):

            st.session_state.emails = (
                fetch_gmail_emails(
                    service,
                    max_results=25
                )
            )

        st.success(
            f"Loaded "
            f"{len(st.session_state.emails)} "
            f"email(s)."
        )

        st.rerun()


# ============================================================
# EMAIL INBOX
# ============================================================

elif page == "Email Inbox":

    st.markdown(
        '<div class="main-title">'
        '📥 Email Inbox'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        "Real emails from your Gmail Inbox"
    )

    # --------------------------------------------------------
    # Gmail connection
    # --------------------------------------------------------

    service = get_gmail_service()

    st.session_state.gmail_service = service

    # --------------------------------------------------------
    # Refresh
    # --------------------------------------------------------

    col1, col2 = st.columns(
        [1, 5]
    )

    with col1:

        refresh = st.button(
            "🔄 Refresh Inbox",
            use_container_width=True
        )

    # --------------------------------------------------------
    # Fetch emails
    # --------------------------------------------------------

    if (
        refresh
        or not st.session_state.emails
    ):

        with st.spinner(
            "Reading your Gmail Inbox..."
        ):

            st.session_state.emails = (
                fetch_gmail_emails(
                    service,
                    max_results=25
                )
            )

    emails = st.session_state.emails

    st.write(
        f"**Showing {len(emails)} email(s)**"
    )

    # --------------------------------------------------------
    # No email
    # --------------------------------------------------------

    if not emails:

        st.warning(
            "No emails were found in your Gmail Inbox."
        )

        st.info(
            "Make sure the email is actually "
            "in the Inbox of the Google account "
            "you connected."
        )

        st.stop()

    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    search = st.text_input(
        "🔎 Search emails",
        placeholder=(
            "Search by sender, subject or message..."
        )
    )

    if search:

        search_lower = search.lower()

        filtered_emails = [

            email

            for email in emails

            if (
                search_lower
                in email["from"].lower()

                or

                search_lower
                in email["subject"].lower()

                or

                search_lower
                in email["body"].lower()
            )
        ]

    else:

        filtered_emails = emails

    st.write(
        f"**Found {len(filtered_emails)} "
        f"matching email(s)**"
    )

    st.divider()

    # --------------------------------------------------------
    # Display emails
    # --------------------------------------------------------

    for index, email in enumerate(
        filtered_emails
    ):

        sender_name, sender_address = parseaddr(
            email["from"]
        )

        display_sender = (
            sender_name
            if sender_name
            else sender_address
        )

        state = get_email_state(
            email["id"]
        )

        # ----------------------------------------------------
        # Email expander
        # ----------------------------------------------------

        with st.expander(
            f"✉️ {index + 1} | "
            f"{email['subject']}"
        ):

            # ------------------------------------------------
            # Email information
            # ------------------------------------------------

            col1, col2 = st.columns(2)

            with col1:

                st.write(
                    f"**From:** "
                    f"{email['from']}"
                )

                st.write(
                    f"**Sender:** "
                    f"{display_sender}"
                )

                st.write(
                    f"**Subject:** "
                    f"{email['subject']}"
                )

            with col2:

                st.write(
                    f"**Date:** "
                    f"{email['date']}"
                )

                if state["sent"]:

                    st.success(
                        "Status: Reply Sent"
                    )

                elif state["status"] == "Rejected":

                    st.error(
                        "Status: Rejected"
                    )

                elif state["reply"]:

                    st.info(
                        "Status: Reply Ready"
                    )

                else:

                    st.warning(
                        "Status: Pending"
                    )

            st.divider()

            # ------------------------------------------------
            # Original email
            # ------------------------------------------------

            st.subheader(
                "📝 Email Body"
            )

            st.write(
                email["body"]
            )

            st.divider()

            # ------------------------------------------------
            # GENERATE AI REPLY
            # ------------------------------------------------

            if (
                not state["reply"]
                and not state["sent"]
                and state["status"] != "Rejected"
            ):

                generate_button = st.button(
                    "🤖 Generate AI Reply",
                    key=(
                        f"generate_"
                        f"{email['id']}"
                    ),
                    use_container_width=True
                )

                if generate_button:

                    with st.spinner(
                        "Gemini is generating "
                        "a professional reply..."
                    ):

                        reply, error = (
                            generate_ai_reply(
                                email["from"],
                                email["subject"],
                                email["body"]
                            )
                        )

                    if error:

                        st.error(
                            f"Gemini error: {error}"
                        )

                    else:

                        state["reply"] = reply

                        state["edited"] = False

                        state["status"] = "Pending"

                        st.success(
                            "✅ AI reply generated successfully."
                        )

                        st.rerun()

            # ------------------------------------------------
            # EDITABLE AI REPLY
            # ------------------------------------------------

            if (
                state["reply"]
                and not state["sent"]
                and state["status"] != "Rejected"
            ):

                st.subheader(
                    "🤖 AI Generated Reply"
                )

                st.caption(
                    "✏️ You can edit this reply "
                    "before sending it."
                )

                edited_reply = st.text_area(
                    "Edit your reply:",
                    value=state["reply"],
                    height=260,
                    key=(
                        f"reply_editor_"
                        f"{email['id']}"
                    )
                )

                # ------------------------------------------------
                # Save edited reply
                # ------------------------------------------------

                save_col, reset_col = st.columns(2)

                with save_col:

                    save_reply = st.button(
                        "💾 Save Changes",
                        key=(
                            f"save_"
                            f"{email['id']}"
                        ),
                        use_container_width=True
                    )

                with reset_col:

                    reset_reply = st.button(
                        "↩️ Reset AI Reply",
                        key=(
                            f"reset_"
                            f"{email['id']}"
                        ),
                        use_container_width=True
                    )

                if save_reply:

                    if not edited_reply.strip():

                        st.error(
                            "Reply cannot be empty."
                        )

                    else:

                        state["reply"] = (
                            edited_reply.strip()
                        )

                        state["edited"] = True

                        st.success(
                            "✅ Your edited reply "
                            "has been saved."
                        )

                        st.rerun()

                if reset_reply:

                    with st.spinner(
                        "Generating a new AI reply..."
                    ):

                        new_reply, error = (
                            generate_ai_reply(
                                email["from"],
                                email["subject"],
                                email["body"]
                            )
                        )

                    if error:

                        st.error(
                            f"Gemini error: {error}"
                        )

                    else:

                        state["reply"] = new_reply

                        state["edited"] = False

                        st.success(
                            "🔄 AI reply reset."
                        )

                        st.rerun()

                # ------------------------------------------------
                # Preview
                # ------------------------------------------------

                st.subheader(
                    "👀 Reply Preview"
                )

                st.info(
                    state["reply"]
                )

                if state["edited"]:

                    st.caption(
                        "✏️ This reply has been edited "
                        "by you."
                    )

                else:

                    st.caption(
                        "🤖 This is the original "
                        "AI-generated reply."
                    )

                # ------------------------------------------------
                # Approve / Reject
                # ------------------------------------------------

                st.subheader(
                    "⚡ Review Reply"
                )

                approve_col, reject_col = (
                    st.columns(2)
                )

                with approve_col:

                    approve = st.button(
                        "✅ Approve & Send Reply",
                        key=(
                            f"approve_"
                            f"{email['id']}"
                        ),
                        use_container_width=True
                    )

                with reject_col:

                    reject = st.button(
                        "❌ Reject Reply",
                        key=(
                            f"reject_"
                            f"{email['id']}"
                        ),
                        use_container_width=True
                    )

                # ------------------------------------------------
                # SEND
                # ------------------------------------------------

                if approve:

                    if not state["reply"].strip():

                        st.error(
                            "Reply cannot be empty."
                        )

                    else:

                        with st.spinner(
                            "Sending reply through Gmail..."
                        ):

                            success, result = (
                                send_gmail_reply(
                                    service,
                                    email,
                                    state["reply"]
                                )
                            )

                        if success:

                            state["sent"] = True

                            state["status"] = (
                                "Sent"
                            )

                            st.success(
                                "🎉 Reply sent successfully!"
                            )

                            st.info(
                                "The edited reply was "
                                "sent through your real Gmail account."
                            )

                            st.rerun()

                        else:

                            st.error(
                                f"❌ Failed to send reply: "
                                f"{result}"
                            )

                # ------------------------------------------------
                # REJECT
                # ------------------------------------------------

                if reject:

                    state["status"] = (
                        "Rejected"
                    )

                    st.warning(
                        "❌ Reply rejected."
                    )

                    st.rerun()

            # ------------------------------------------------
            # SENT STATUS
            # ------------------------------------------------

            if state["sent"]:

                st.success(
                    "📤 This email has been replied to successfully."
                )

                st.subheader(
                    "📨 Sent Reply"
                )

                st.info(
                    state["reply"]
                )

            # ------------------------------------------------
            # REJECTED STATUS
            # ------------------------------------------------

            elif state["status"] == "Rejected":

                st.error(
                    "❌ This AI reply was rejected."
                )

                if st.button(
                    "🔄 Generate New Reply",
                    key=(
                        f"regenerate_"
                        f"{email['id']}"
                    ),
                    use_container_width=True
                ):

                    state["reply"] = ""

                    state["status"] = (
                        "Pending"
                    )

                    state["edited"] = False

                    st.rerun()


# ============================================================
# ADD TEST EMAIL
# ============================================================

elif page == "Add Test Email":

    st.markdown(
        '<div class="main-title">'
        '➕ Add Test Email'
        '</div>',
        unsafe_allow_html=True
    )

    st.write(
        "Create a local test email for "
        "testing AI generation."
    )

    sender = st.text_input(
        "Sender Email",
        value="test@example.com"
    )

    subject = st.text_input(
        "Subject",
        value="Interview Test"
    )

    body = st.text_area(
        "Email Body",
        value=(
            "Hello,\n\n"
            "I am interested in the interview "
            "opportunity. Please provide the "
            "interview details and schedule.\n\n"
            "Thank you."
        ),
        height=220
    )

    if st.button(
        "🧪 Process Test Email",
        use_container_width=True
    ):

        if not sender.strip():

            st.error(
                "Please enter a sender email."
            )

        elif not subject.strip():

            st.error(
                "Please enter a subject."
            )

        elif not body.strip():

            st.error(
                "Please enter the email body."
            )

        else:

            # ------------------------------------------------
            # Generate AI reply
            # ------------------------------------------------

            with st.spinner(
                "Generating AI reply..."
            ):

                reply, error = (
                    generate_ai_reply(
                        sender,
                        subject,
                        body
                    )
                )

            if error:

                st.error(
                    f"Gemini error: {error}"
                )

            else:

                test_id = (
                    f"test_"
                    f"{len(st.session_state.test_emails) + 1}"
                )

                test_email = {

                    "id": test_id,

                    "thread_id": "",

                    "from": sender,

                    "subject": subject,

                    "date": "Local Test Email",

                    "message_id_header": "",

                    "references": "",

                    "body": body,

                    "snippet": body,

                    "label_ids": []
                }

                st.session_state.test_emails.append(
                    test_email
                )

                st.success(
                    "✅ Test email processed successfully."
                )

                st.subheader(
                    "🤖 AI Generated Reply"
                )

                st.text_area(
                    "Generated reply:",
                    value=reply,
                    height=220,
                    key="test_generated_reply"
                )

                st.warning(
                    "⚠️ This is a local test email. "
                    "It does not have a real Gmail "
                    "message ID, so it cannot be sent "
                    "as a real Gmail reply."
                )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Automatic Mail Responder • "
    "AI-powered email management system"
)