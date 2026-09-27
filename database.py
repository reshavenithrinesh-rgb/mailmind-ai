import sqlite3
from pathlib import Path


DATABASE_PATH = Path("data/emails.db")


def get_connection():
    DATABASE_PATH.parent.mkdir(exist_ok=True)
    return sqlite3.connect(DATABASE_PATH)


def create_table():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            subject TEXT,
            body TEXT,
            category TEXT,
            priority TEXT,
            generated_reply TEXT,
            status TEXT,
            received_at TEXT
        )
    """)

    connection.commit()
    connection.close()


def add_email(
    sender,
    subject,
    body,
    category="Unclassified",
    priority="Normal",
    generated_reply="",
    status="Pending",
    received_at=""
):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO emails (
            sender,
            subject,
            body,
            category,
            priority,
            generated_reply,
            status,
            received_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sender,
        subject,
        body,
        category,
        priority,
        generated_reply,
        status,
        received_at
    ))

    connection.commit()
    connection.close()


def get_all_emails():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            sender,
            subject,
            body,
            category,
            priority,
            generated_reply,
            status,
            received_at
        FROM emails
        ORDER BY id DESC
    """)

    emails = cursor.fetchall()
    connection.close()

    return emails

def update_email(email_id, generated_reply, status):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE emails
        SET generated_reply = ?, status = ?
        WHERE id = ?
    """, (
        generated_reply,
        status,
        email_id
    ))

    connection.commit()
    connection.close()