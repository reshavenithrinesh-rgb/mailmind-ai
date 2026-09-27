def classify_email(subject, body):
    """
    Classify an email based on its subject and body.
    """

    text = f"{subject} {body}".lower()

    # Job / Recruitment
    job_keywords = [
        "job",
        "career",
        "interview",
        "recruitment",
        "hiring",
        "resume",
        "vacancy",
        "offer letter"
    ]

    # Meeting
    meeting_keywords = [
        "meeting",
        "appointment",
        "schedule",
        "call",
        "conference",
        "discussion"
    ]

    # Complaint
    complaint_keywords = [
        "complaint",
        "problem",
        "issue",
        "not working",
        "disappointed",
        "refund",
        "wrong"
    ]

    # Enquiry
    enquiry_keywords = [
        "enquiry",
        "inquiry",
        "information",
        "details",
        "question",
        "can you tell",
        "please explain"
    ]

    # Academic
    academic_keywords = [
        "college",
        "university",
        "assignment",
        "exam",
        "project",
        "faculty",
        "student",
        "marks"
    ]

    # Personal
    personal_keywords = [
        "family",
        "birthday",
        "friend",
        "vacation",
        "personal"
    ]

    if any(keyword in text for keyword in job_keywords):
        category = "Job / Recruitment"

    elif any(keyword in text for keyword in meeting_keywords):
        category = "Meeting"

    elif any(keyword in text for keyword in complaint_keywords):
        category = "Complaint"

    elif any(keyword in text for keyword in enquiry_keywords):
        category = "Enquiry"

    elif any(keyword in text for keyword in academic_keywords):
        category = "Academic"

    elif any(keyword in text for keyword in personal_keywords):
        category = "Personal"

    else:
        category = "General"

    priority = detect_priority(text)

    return category, priority


def detect_priority(text):
    """
    Determine email priority.
    """

    high_priority_keywords = [
        "urgent",
        "immediately",
        "emergency",
        "as soon as possible",
        "deadline today",
        "important",
        "critical"
    ]

    medium_priority_keywords = [
        "tomorrow",
        "deadline",
        "meeting",
        "interview",
        "request"
    ]

    if any(keyword in text for keyword in high_priority_keywords):
        return "High"

    elif any(keyword in text for keyword in medium_priority_keywords):
        return "Medium"

    else:
        return "Low"
def generate_reply(category, subject, body):
    """
    Generate a basic automatic reply based on email category.
    """

    if category == "Job / Recruitment":

        reply = """Dear Sir/Madam,

Thank you for contacting me regarding the opportunity.

I appreciate the information and will review the details carefully. 
I will get back to you with my confirmation as soon as possible.

Regards,
User"""

    elif category == "Meeting":

        reply = """Hello,

Thank you for your meeting request.

I have received your message and will review the proposed schedule. 
I will confirm my availability shortly.

Regards,
User"""

    elif category == "Complaint":

        reply = """Dear Sir/Madam,

Thank you for bringing this issue to my attention.

I have received your complaint and will review the matter carefully. 
I will get back to you with an appropriate response as soon as possible.

Regards,
Support Team"""

    elif category == "Enquiry":

        reply = """Hello,

Thank you for your enquiry.

I have received your request and will review the information. 
I will get back to you with the required details shortly.

Regards,
Support Team"""

    elif category == "Academic":

        reply = """Dear Sir/Madam,

Thank you for your message regarding the academic matter.

I have received your request and will review the details. 
I will respond with the required information shortly.

Regards,
Student"""

    elif category == "Personal":

        reply = """Hello,

Thank you for your message.

I have received your email and will get back to you soon.

Regards,
User"""

    else:

        reply = """Hello,

Thank you for your email.

I have received your message and will review it. 
I will get back to you as soon as possible.

Regards,
User"""

    return reply

if __name__ == "__main__":

    subject = "Interview Invitation"

    body = """
    You have been shortlisted for an interview.
    Please confirm your availability.
    """

    category, priority = classify_email(
        subject,
        body
    )

    reply = generate_reply(
        category,
        subject,
        body
    )

    print("Category:", category)
    print("Priority:", priority)

    print("\nGenerated Reply:")
    print(reply)