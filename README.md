# Personal Finance Dashboard

A personal finance app built with Python and Streamlit that ingests transaction CSVs from Chase, Amex, and Venmo, stores them in a local SQLite database, and visualizes spending through an interactive dashboard.

---

## Features

- **Multi-source CSV import** — Chase Checking, Chase Credit, Amex Credit, and Venmo, via the dashboard UI or CLI
- **Automatic deduplication** — safe to re-import overlapping date ranges
- **Keyword-based categorization** — configurable via `config/categories.yaml` or the in-app Categories page
- **Two-tier category hierarchy** — categories (Food, Lifestyle, etc.) and subcategories (Dining Out, Coffee, etc.)
- **Manual category override** — edit any transaction's subcategory directly from the dashboard table, protected from future recategorization
- **Spending trend chart** — stacked bar chart by month, switchable between category and subcategory view
- **Monthly breakdown** — donut pie chart and horizontal bar chart for any selected month
- **Transaction table** — searchable, filterable, with inline subcategory editing
- **Three themes** — Arctic (light), Linear/Notion Dark, Dracula
- **Desktop shortcut** — one double-click to launch the app (Mac)

---

## Project Structure

```
personal_finances/
│
├── app/
│   ├── dashboard.py          # Streamlit dashboard (home + dashboard view)
│   └── pages/
│       ├── 1_Import.py       # CSV import UI
│       └── 2_Categories.py   # Category and keyword management UI
│
├── config/
│   └── categories.yaml       # Subcategory keyword rules and category mapping
│
├── finance/                  # Core Python package
│   ├── db.py                 # SQLite schema and connection
│   ├── importer.py           # Parse → categorize → insert pipeline
│   ├── categorizer.py        # Keyword matching and bank category fallback
│   └── parsers/
│       ├── chase_checking.py
│       ├── chase_credit.py
│       ├── amex.py
│       └── venmo.py
│
├── scripts/
│   ├── import_csv.py         # CLI import entry point
│   └── recategorize.py       # Reapply categorization to existing transactions
│
├── data/
│   ├── raw/                  # Drop CSV exports here for CLI import (gitignored)
│   └── db/                   # SQLite database (gitignored)
│
├── notebooks/                # Scratch space for exploration
├── Launch Finance App.command # Desktop shortcut (Mac)
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd personal_finances
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Initialize the database

```bash
python finance/db.py
```

---

## Importing Transactions

### Option A — Dashboard UI (recommended)

Launch the app and go to the **Import** page. Upload one or more CSVs, select the source type, and click Import. The app parses, categorizes, and deduplicates automatically.

**Venmo note:** Venmo only allows monthly CSV exports. Download one file per month and import each separately.

### Option B — CLI

Download CSV exports from your bank websites and drop them into `data/raw/`, then run:

```bash
python scripts/import_csv.py data/raw/your_file.csv chase_checking
python scripts/import_csv.py data/raw/your_file.csv chase_credit
python scripts/import_csv.py data/raw/your_file.csv amex
python scripts/import_csv.py data/raw/your_file.csv venmo
```

Duplicate transactions are automatically skipped based on a hash of each transaction's key fields. It is safe to overlap date ranges when downloading new exports.

---

## Running the Dashboard

```bash
source .venv/bin/activate
streamlit run app/dashboard.py
```

### Desktop shortcut (Mac)

To add a one-click launcher to your Desktop, create a symlink pointing to the `.command` file in the repo:

```bash
ln -s "/absolute/path/to/personal_finances/Launch Finance App.command" ~/Desktop/
```

Replace `/absolute/path/to/personal_finances` with wherever you cloned the repo. For example:

```bash
ln -s "/Users/yourname/Documents/Projects/personal_finances/Launch Finance App.command" ~/Desktop/
```

Double-click the shortcut from Finder to launch the app. Note: the symlink must point to the original file inside the repo — copying the file to your Desktop directly will not work.

Or double-click `Launch Finance App.command` from Finder (Mac only).

---

## Categorization

### Editing via the UI

Go to the **Categories** page in the app to add, rename, or delete subcategories, change parent categories, edit keywords, and update colors — all without touching the YAML directly. Use **Save & Recategorize** to apply changes to existing transactions immediately.

### Editing via YAML

Categories are defined in `config/categories.yaml`. Each subcategory entry includes:

- `category` — the parent category it rolls up to
- `color` — hex color used in charts
- `keywords` — list of substrings matched against transaction descriptions (case-insensitive)
- `amount_keywords` — optional list of description + amount pairs for precise matching

Example:

```yaml
  Dining Out:
    category: Food
    color: "#FF8E53"
    keywords:
      - restaurant
      - chipotle
      - wingstop

  Bills & Utilities:
    category: Required Expenses
    color: "#E74C3C"
    keywords:
      - att
      - verizon
    amount_keywords:
      - description: apple.com/bill
        amount: 2.99
```

**Categorization order:**
1. `FORCE_UNCATEGORIZED` patterns (always bypass matching)
2. Amount-specific keyword rules
3. Regular keyword matching (first match wins, in yaml order)
4. Bank-provided category fallback (`BANK_CATEGORY_MAP` in `categorizer.py`)
5. `Uncategorized`

After editing `categories.yaml` directly, run:

```bash
python scripts/recategorize.py
```

This reprocesses all transactions that have not been manually categorized. The Categories page in the app can do this for you via the **Save & Recategorize** button.

---

## Category Hierarchy

| Category | Subcategories |
|---|---|
| Food | Groceries, Food & Drink, Dining Out, Coffee |
| Income | Salary |
| Vices | Smoke Shop, Bars/Nightclubs, Gambling, Alcohol at Home |
| Transportation | Transportation, Auto Services |
| Shopping | Shopping, Home Essentials |
| Lifestyle | Health & Fitness, Entertainment, Travel, Personal Care |
| Required Expenses | Bills & Utilities, Rent, Student Loans, Car Payment |
| Other | Professional Development, Fines & Fees, Taxes, Miscellaneous |
| Uncategorized | Venmo Zelle & Paypal, Transfer, ATM & Cash, Uncategorized |
| Excluded | Excluded (hidden from dashboard) |

---

## Monthly Workflow

1. Download transaction CSVs from Chase, Amex, and Venmo
2. Upload each file on the **Import** page and select the correct source type
3. Launch the dashboard and review new `Uncategorized` transactions
4. Assign subcategories manually from the transaction table as needed
5. Optionally update keywords on the **Categories** page and click **Save & Recategorize**

---

## Data Privacy

All data is stored locally in `data/db/finance.db`. The `data/` directory is gitignored and no financial data is ever committed to the repository.