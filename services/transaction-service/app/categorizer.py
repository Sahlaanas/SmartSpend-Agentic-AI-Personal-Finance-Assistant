import re

# category -> keywords. Order matters: the first category that matches wins.
RULES: dict[str, list[str]] = {
    "Groceries": ["bigbasket", "blinkit", "zepto", "dmart", "grocery", "supermarket", "reliance fresh", "more retail"],
    "Food": ["swiggy", "zomato", "restaurant", "cafe", "dominos", "pizza", "kfc", "mcdonalds", "starbucks", "hotel", "bakery"],
    "Transport": ["uber", "ola", "rapido", "petrol", "fuel", "irctc", "metro", "bpcl", "hpcl", "iocl", "fastag"],
    "Shopping": ["amazon", "flipkart", "myntra", "ajio", "meesho", "nykaa", "croma"],
    "Bills": ["electricity", "kseb", "recharge", "jio", "airtel", "vodafone", "bsnl", "broadband", "gas", "water bill"],
    "Entertainment": ["netflix", "spotify", "hotstar", "prime video", "bookmyshow", "cinema", "pvr"],
    "Health": ["pharmacy", "apollo", "medplus", "hospital", "clinic", "diagnostics"],
    "Rent": ["rent"],
}

# \b makes sure "ola" matches the word "ola" but not "cola"
_PATTERNS = {
    category: re.compile(r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\b")
    for category, keywords in RULES.items()
}


def categorize(description: str) -> str:
    text = description.lower()
    for category, pattern in _PATTERNS.items():
        if pattern.search(text):
            return category
    return "Other"                                                                                                   

# Every category an expense can have ("Total" only exists for budgets)
CATEGORIES = [*RULES.keys(), "Other"]


def match_category(name: str) -> str | None:
    """'food' -> 'Food'. Returns None when the name is not a known category."""
    for category in CATEGORIES:
        if category.lower() == name.strip().lower():
            return category
    return None           