import re

EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

PHONE_PATTERN = re.compile(r'(?<![a-zA-Z0-9@.])(?:\(\+84\)|\+84|0)[\s.-]?\(?[35789]\d{1,2}\)?(?:[\s.-]?\d){6,7}\b')
LINKEDIN_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9\-_/]+', re.IGNORECASE)
GITHUB_PATTERN = re.compile(r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9\-_/]+', re.IGNORECASE)


def extract_emails(text):
    return EMAIL_PATTERN.findall(text)


def extract_phones(text):
    return PHONE_PATTERN.findall(text)


def extract_links(text):
    return {
        "linkedin": LINKEDIN_PATTERN.findall(text),
        "github": GITHUB_PATTERN.findall(text),
    }


def extract_contact_info(text):
    return {
        "emails": extract_emails(text),
        "phones": extract_phones(text),
        "links": extract_links(text),
    }


if __name__ == "__main__":
    from reader import extract_text

    text = extract_text("data/NGUYỄN TRỌNG LUÂN.docx")
    result = extract_contact_info(text)
    print(result)