"""
Signup/login validation — pure, rule-based, importable anywhere.

Every rule returns (ok, error_message) and the rules themselves are exported
so the frontend checklist can mirror them exactly.
"""

import re

# RFC-5322-practical: dot-atom local part (dots can't lead, trail, or repeat),
# then domain labels of letters/digits/hyphens.
EMAIL_RE = re.compile(
    r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*"
    r"@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z]{2,})+$"
)
# free-mail domains that typo-squatting / disposable abuse usually targets
DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "yopmail.com", "throwawaymail.com", "sharklasers.com", "trashmail.com",
}

PASSWORD_MIN_LEN = 8

# rule id -> (label shown in the UI checklist, test function)
PASSWORD_RULES = {
    "len":    (f"At least {PASSWORD_MIN_LEN} characters",
               lambda p: len(p) >= PASSWORD_MIN_LEN),
    "upper":  ("An uppercase letter (A-Z)",
               lambda p: re.search(r"[A-Z]", p) is not None),
    "lower":  ("A lowercase letter (a-z)",
               lambda p: re.search(r"[a-z]", p) is not None),
    "digit":  ("A number (0-9)",
               lambda p: re.search(r"\d", p) is not None),
    "special":("A special character (!@#$…)",
               lambda p: re.search(r"[^A-Za-z0-9]", p) is not None),
    "space":  ("No spaces", lambda p: " " not in p),
}

COMMON_PASSWORDS = {
    "password", "password1", "password123", "12345678", "123456789",
    "qwerty123", "qwerty123!", "iloveyou", "admin123", "welcome1",
    "letmein1", "abc12345", "p@ssw0rd", "passw0rd", "monkey123",
}


def validate_email(email):
    """Return (ok, error). Checks shape, length, domain sanity, disposable list."""
    email = (email or "").strip()
    if not email:
        return False, "Email is required."
    if len(email) > 254:
        return False, "Email is too long."
    if ".." in email:
        return False, "Email can't contain consecutive dots."
    if not EMAIL_RE.match(email):
        return False, "Enter a valid email, e.g. you@example.com."
    domain = email.rsplit("@", 1)[1].lower()
    if domain in DISPOSABLE_DOMAINS:
        return False, "Disposable email addresses are not allowed."
    return True, ""


def failed_password_rules(password):
    """List of rule ids the password does NOT satisfy (for the live checklist)."""
    return [rid for rid, (_label, test) in PASSWORD_RULES.items()
            if not test(password or "")]


def password_strength(password):
    """
    0-4 score mirroring common password meters (entropy-style, but rule-based
    and fully explainable). 4 = all rules + 12+ chars.
    """
    if not password:
        return 0
    failed = failed_password_rules(password)
    base = 4 - min(len(failed), 4)
    if len(password) >= 12 and not failed:
        return 4
    return base


STRENGTH_LABELS = ["Very weak", "Weak", "Fair", "Good", "Strong"]


def validate_password_pair(password, confirm, email=""):
    """Full server-side password validation for signup. Returns (ok, error)."""
    password = password or ""
    if failed_password_rules(password):
        return False, ("Password needs: " +
                       ", ".join(PASSWORD_RULES[r][0].lower()
                                 for r in failed_password_rules(password)) + ".")
    if password.lower() in COMMON_PASSWORDS:
        return False, "That password is too common — pick something less guessable."
    local = email.split("@")[0].lower() if email else ""
    if local and local in password.lower():
        return False, "Password can't contain your email name."
    if password != (confirm or ""):
        return False, "Passwords do not match."
    return True, ""
