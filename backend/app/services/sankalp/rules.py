"""Fixed lists from the business logic: categories, call groups, statuses (Annex B), outcomes, questions, codes.

Status texts are kept exactly as in the document (with its en dash) so reports read the same as the Excel workbooks.
"""

# ---- Section 4.1: category of the person met (fixed: the calling rules depend on it) ----
CATEGORIES: dict[str, str] = {
    "lead": "Lead",
    "prospect": "Prospect",
    "dsa_connector": "DSA/Connector",
    "contact_point": "Contact Point",
    "existing_customer": "Existing Customer",
    "existing_applicant": "Existing Applicant",
}

# ---- Section 5.1: call group ----
CALL_GROUP: dict[str, str] = {
    "lead": "lead", "prospect": "lead",
    "dsa_connector": "dsa_cp", "contact_point": "dsa_cp",
    "existing_customer": "none", "existing_applicant": "none",
}
LEAD_CATEGORIES = {"lead", "prospect"}

# ---- Annex B: statuses ----
ALLOCATE = "Allocate"
NC_NO_NUMBER = "Not called – no valid number"
NC_REPEAT = "Not called – repeat entry by same SO"
NC_DUPLICATE = "Not called – duplicate entry"
NC_BEING_CALLED = "Not called – number already being called"
NC_SPOKEN = "Not called – spoken within 30 days"
NC_KNOWN = "Not called – known contact"
NOT_CALLED = [NC_NO_NUMBER, NC_REPEAT, NC_DUPLICATE, NC_BEING_CALLED, NC_SPOKEN, NC_KNOWN]

IN_RETRY = "In retry"
DISCARDED_9 = "Discarded – 9 unanswered"
DISCARDED_INVALID = "Discarded – invalid number"
CLOSED_NO_ANSWER = "Closed – no answer"
REJECTED_REFUSED = "Rejected – refused to talk"

VALIDATED = "Validated"
VALIDATED_DIFFERENT = "Validated – different person"
VALIDATED_NO_VISIT = "Validated – visit not confirmed"
VALIDATED_CONVERTED = "Validated – converted from DSA/CP"
ALREADY_IN_PROCESS = "Already in process"
NOT_COUNTED_LAP = "Not counted – LAP"
AMBER_MISSING = "Amber – answers missing"
AMBER_KNOWS_SO = "Amber – knows SO"
AMBER_WRONG_PERSON = "Amber – wrong person"
RED = "Red"

DSA_GREEN = "DSA/CP – Green"
DSA_NA = "DSA/CP – NA"
DSA_AMBER = "DSA/CP – Amber"
DSA_RED = "DSA/CP – Red"
DSA_NO_RAG = "DSA/CP – no RAG"

LOGGED_IN = "Logged in"
OUTCOME_REJECTED = "Rejected"
LOGIN_BEFORE_ENTRY = "Login on/before entry date (not counted)"

ALL_STATUSES = NOT_CALLED + [IN_RETRY, DISCARDED_9, DISCARDED_INVALID, CLOSED_NO_ANSWER, REJECTED_REFUSED,
                             VALIDATED, VALIDATED_DIFFERENT, VALIDATED_NO_VISIT, VALIDATED_CONVERTED,
                             ALREADY_IN_PROCESS, NOT_COUNTED_LAP, AMBER_MISSING, AMBER_KNOWS_SO, AMBER_WRONG_PERSON,
                             RED, DSA_GREEN, DSA_NA, DSA_AMBER, DSA_RED, DSA_NO_RAG]
LEAD_OUTCOMES = [LOGGED_IN, OUTCOME_REJECTED, LOGIN_BEFORE_ENTRY]

RAGS = ["PENDING", "NA", "RED", "AMBER", "RNR", "GREEN"]


def is_validated(status: str | None) -> bool:
    return bool(status) and status.startswith(VALIDATED)


# ---- Section 7.1: attempts ----
SLOTS = ["09-10", "10-11", "11-12", "12-01", "01-02", "02-03", "03-04", "04-05", "05-06", "06-07"]
CONNECTED = "Connected"
RNR = "RNR"
BUSY = "Busy"
SWITCHED_OFF = "Switched off"
NOT_REACHABLE = "Not reachable"
INVALID_NUMBER = "Invalid number"
WRONG_PERSON = "Wrong person"
CALLBACK = "Callback requested"
REFUSED = "Refused to talk"
OUTCOMES = [CONNECTED, RNR, BUSY, SWITCHED_OFF, NOT_REACHABLE, INVALID_NUMBER, WRONG_PERSON, CALLBACK, REFUSED]
UNANSWERED = {RNR, BUSY, SWITCHED_OFF, NOT_REACHABLE}

# ---- Section 7.2: questions once connected (Lead group) ----
NAME_CHECK = ["Same person", "Same person, different spelling", "Different person – same family", "Different person"]
VISIT = ["Yes", "Don't recall", "No"]
RELATIONSHIP = ["No", "Yes – the same officer", "Yes – another employee"]
LOAN_NEED = ["Home purchase", "Self-construction", "Plot + construction", "Improvement or extension",
             "Balance transfer", "BT + construction", "BT + LAP", "LAP", "Not looking for a loan"]
TIMELINE = ["Within 15 days", "15 days–1 month", "1–3 months", "After 3 months", "Not decided"]
INCOME = ["Salaried", "Self-employed", "Agriculture", "Other"]
DOCUMENTS = ["Yes", "Partly", "No", "File already logged with Aham"]
NEXT_STEP = ["SO / branch visit", "Call centre to continue", "Not now"]
PURPOSE = ["Discuss eligibility", "Collect documents", "Property visit"]
OWN_CONTRIBUTION = ["Fully", "Partly", "Not yet", "Prefer not to say"]
LAP_NEEDS = {"LAP", "BT + LAP"}
NO_LOAN = "Not looking for a loan"

# ---- Section 7.3: DSA/CP group ----
DSA_RAG = ["Green", "NA", "Amber", "Red"]

# ---- Section 12: actions ----
ACT_CORRECT_NUMBER = "Correct customer number"
ACT_DSA_FOLLOWUP = "DSA/CP follow-up"
ACT_VISIT = "Visit customer"
ACT_COLLECT_DOCS = "Collect documents"
ACT_FOLLOW_UP_LEAD = "Follow up lead"
LEAD_ACTIONS = {ACT_VISIT, ACT_COLLECT_DOCS, ACT_FOLLOW_UP_LEAD}
CC_CALLBACK = "Callback"
CC_TAKE_FORWARD = "Take case forward"
CC_FOLLOW_UP = "Follow-up"

# ---- Section 12.4: branch answer codes (code -> (meaning, which date is asked for or None)) ----
BRANCH_CODES: dict[str, tuple[str, str | None]] = {
    "1": ("Logged in", None),
    "2": ("Category wrong", None),
    "3": ("RNR: customer not answering the branch", None),
    "R1": ("Rejected: property or legal issue that cannot be cured", None),
    "R2": ("Rejected: eligibility or income", None),
    "R3": ("Rejected: credit score", None),
    "R4": ("Rejected: loan taken elsewhere", None),
    "R5": ("Rejected: customer not interested", None),
    "R6": ("Rejected: outside branch area", None),
    "A1": ("Documents pending: KYC", "Login date"),
    "A2": ("Documents pending: income proof", "Login date"),
    "A3": ("Documents pending: property documents", "Login date"),
    "A4": ("Documents pending: part of property documents", "Login date"),
    "A5": ("Documents pending: application", "Login date"),
    "B": ("Login fee or IMD pending", "Login date"),
    "C1": ("Papers ready, login pending: loan amount under negotiation", "Login date"),
    "C2": ("Papers ready, login pending: rate of interest", "Login date"),
    "C3": ("Papers ready, login pending: date of login", "Login date"),
    "D": ("On hold: the customer must resolve a legal issue", "Follow-up date"),
    "E1": ("Customer asked for time: family issue", "Follow-up date"),
    "E2": ("Customer asked for time: out of station", "Follow-up date"),
    "F1": ("Visit pending: BM visit", "Visit date"),
    "F2": ("Visit pending: pre-PD promised", "Visit date"),
}
REJECT_CODES = {"R1", "R2", "R3", "R4", "R5", "R6"}
GREEN_CHANNEL_PROTECTED = {"R2", "R3"}
CONSTRUCTION_NEEDS = {"Self-construction", "Improvement or extension"}
PURCHASE_NEEDS = {"Home purchase", "Plot + construction"}

# ---- Section 13.3: tracker ----
TRACKER_OWNERS = ["branch", "call_centre", "done"]
TRACKER_RETURN_GREEN = "Return to branch – green channel"
TRACKER_OUTCOMES = ["Reopen for calling", "Rejected", "Logged in", TRACKER_RETURN_GREEN]
