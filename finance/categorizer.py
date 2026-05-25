import yaml
from pathlib import Path


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "categories.yaml"


BANK_CATEGORY_MAP = {
    "transportation-auto services":             "Auto Services",
    "fees & adjustments-fees & adjustments":    "Bills & Utilities",
    "fees & adjustments":                       "Bills & Utilities",
    "business services-other services":         "Bills & Utilities",
    "business services-banking services":       "Bills & Utilities",
    "business services-printing & publishing":  "Bills & Utilities",
    "business services-conferences & training": "Bills & Utilities",
    "other-government services":                "Bills & Utilities",
    "professional services":                    "Bills & Utilities",
    "restaurant-bar & café":                    "Dining Out",
    "restaurant-restaurant":                    "Dining Out",
    "entertainment-other entertainment":        "Entertainment",
    "entertainment-theatrical events":          "Entertainment",
    "entertainment-general events":             "Entertainment",
    "entertainment-sports events":              "Entertainment",
    "entertainment-theme parks":                "Entertainment",
    "entertainment-general attractions":        "Entertainment",
    "entertainment-associations":               "Entertainment",
    "merchandise & supplies-groceries":         "Groceries",
    "groceries":                                "Groceries",
    "business services-health care services":   "Health & Fitness",
    "health & wellness":                        "Health & Fitness",
    "business services-office supplies":        "Shopping",
    "merchandise & supplies-clothing stores":   "Shopping",
    "merchandise & supplies-general retail":    "Shopping",
    "merchandise & supplies-internet purchase": "Shopping",
    "merchandise & supplies-mail order":        "Shopping",
    "merchandise & supplies-department stores": "Shopping",
    "merchandise & supplies-arts & jewelry":    "Shopping",
    "merchandise & supplies-sporting goods stores": "Shopping",
    "merchandise & supplies-music & video":     "Shopping",
    "merchandise & supplies-book stores":       "Shopping",
    "transportation-parking charges":           "Transportation",
    "transportation-fuel":                      "Transportation",
    "transportation-vehicle leasing & purchase":"Transportation",
    "transportation-rail services":             "Transportation",
    "travel-lodging":                           "Travel",
    "travel-airline":                           "Travel",
    "travel-travel agencies":                   "Travel",
    "other-miscellaneous":                      "Uncategorized",
    "other-education":                          "Uncategorized",
    "other-charities":                          "Uncategorized",
    "personal":                                 "Uncategorized",
}


def load_categories() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)["categories"]
    
    
FORCE_UNCATEGORIZED = [
    "offer:",
]


def categorize(description: str, amount: float = None, chase_category: str = None, amex_category: str = None) -> str:
    categories = load_categories()
    description_lower = description.lower()

    # Force uncategorized for specific patterns regardless of bank category
    for pattern in FORCE_UNCATEGORIZED:
        if pattern.lower() in description_lower:
            return "Uncategorized"

    # First pass: check amount-specific rules
    if amount is not None:
        for category_name, config in categories.items():
            for rule in config.get("amount_keywords", []):
                desc_match = rule["description"].lower() in description_lower
                amount_match = abs(abs(amount) - abs(rule["amount"])) < 0.01
                if desc_match and amount_match:
                    return category_name

    # Second pass: regular keyword matching
    for category_name, config in categories.items():
        if category_name == "Uncategorized":
            continue
        for keyword in config.get("keywords", []):
            if keyword.lower() in description_lower:
                return category_name

    # Fall back to bank-provided category
    if chase_category and str(chase_category).lower() not in ("nan", "none", ""):
        normalized = BANK_CATEGORY_MAP.get(chase_category.lower())
        if normalized:
            return normalized
        return chase_category

    if amex_category and str(amex_category).lower() not in ("nan", "none", ""):
        normalized = BANK_CATEGORY_MAP.get(amex_category.lower())
        if normalized:
            return normalized
        return amex_category

    return "Uncategorized"


def get_category_colors() -> dict[str, str]:
    """Returns a dict of {category_name: color} for use in visualizations."""
    categories = load_categories()
    return {name: config.get("color", "#BDC3C7") for name, config in categories.items()}


