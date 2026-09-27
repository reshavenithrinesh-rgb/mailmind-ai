from google import genai

client = genai.Client()


def generate_email_reply(email_text):
    prompt = f"""
You are a professional email assistant.

Read the email below and write a polite, professional reply.

Email:
{email_text}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    return response.text


if __name__ == "__main__":
    test_email = """
Subject: Interview Invitation

Hello,

You have been shortlisted for an interview.
Please confirm your availability for tomorrow at 11 AM.

Regards,
HR Team
"""

    reply = generate_email_reply(test_email)

    print("\nAI Reply:\n")
    print(reply)