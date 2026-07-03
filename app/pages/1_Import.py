"""
Import page — drop into app/ alongside dashboard.py.

Integration options:
  A) Single-file dashboard: paste the render_import_page() call into a
     st.sidebar.radio() nav block.
  B) Multipage (pages/ folder): save as app/pages/1_Import.py and
     replace the render_import_page() call at the bottom with a direct call.

The page uses only stdlib + packages already in the project stack.
"""

import io
import sys
import tempfile
import traceback
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Path bootstrap — makes `finance` importable regardless of working directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent  # personal_finances/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from finance.importer import import_file  # noqa: E402  (import after path fix)

# ---------------------------------------------------------------------------
# Source type config
# ---------------------------------------------------------------------------
SOURCE_OPTIONS = {
    "Chase Checking": "chase_checking",
    "Chase Credit": "chase_credit",
    "American Express": "amex",
    "Venmo": "venmo",
}


# ---------------------------------------------------------------------------
# Core render function
# ---------------------------------------------------------------------------
def render_import_page() -> None:
    st.header("📥 Import Transactions")
    st.caption(
        "Upload one or more CSVs. Each file is processed independently — "
        "duplicates are skipped automatically via hash deduplication."
    )

    # ── Source selector ──────────────────────────────────────────────────────
    source_label = st.selectbox(
        "Account / source type",
        options=["Select file source"] + list(SOURCE_OPTIONS.keys()),
        help="All uploaded files in this batch will be treated as this source type. "
             "Import files from different sources separately.",
    )

    if source_label == "Select file source":
        source_key = None
    else:
        source_key = SOURCE_OPTIONS[source_label]

    # ── File uploader ────────────────────────────────────────────────────────
    uploaded_files = st.file_uploader(
        "Choose CSV file(s)",
        type=["csv"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if not uploaded_files:
        st.info("No files selected yet.")
        return

    st.write(f"**{len(uploaded_files)} file(s) ready** — source: *{source_label}*")

    if source_key is None:
        st.warning("Please select a file source before importing.")
        return

    # ── Import button ────────────────────────────────────────────────────────
    if st.button("Import", type="primary", use_container_width=True):
        _run_import(uploaded_files, source_key)


# ---------------------------------------------------------------------------
# Import runner
# ---------------------------------------------------------------------------
def _run_import(uploaded_files, source_key: str) -> None:
    total_added = 0
    total_dupes = 0
    errors = []

    progress = st.progress(0, text="Starting import…")
    results_container = st.container()

    for i, uploaded_file in enumerate(uploaded_files):
        file_label = uploaded_file.name
        progress.progress(
            (i + 1) / len(uploaded_files),
            text=f"Processing {file_label}…",
        )

        try:
            added, dupes = _import_single(uploaded_file, source_key)
            total_added += added
            total_dupes += dupes
            with results_container:
                if added > 0:
                    st.success(f"**{file_label}** — {added} imported, {dupes} duplicate(s) skipped")
                else:
                    st.warning(f"**{file_label}** — 0 new rows (all {dupes} were duplicates)")

        except Exception as exc:  # noqa: BLE001
            errors.append((file_label, exc))
            with results_container:
                st.error(f"**{file_label}** — failed: {exc}")
                with st.expander("Traceback"):
                    st.code(traceback.format_exc())

    progress.empty()

    # ── Summary ──────────────────────────────────────────────────────────────
    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("New transactions", total_added)
    col2.metric("Duplicates skipped", total_dupes)
    col3.metric("Files with errors", len(errors))

    if total_added > 0:
        st.balloons()
        # Clear cached data so the dashboard reflects new transactions
        st.cache_data.clear()
        st.success(
            f"✅ Done! {total_added} transaction(s) added. "
            "Switch to the Dashboard tab to see updated charts."
        )


def _import_single(uploaded_file, source_key: str) -> tuple[int, int]:
    """Write the uploaded file to a temp path and call import_file()."""
    suffix = Path(uploaded_file.name).suffix or ".csv"
    raw_bytes = uploaded_file.read()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name

    # import_file() is expected to return (added: int, duplicates: int).
    # If your importer returns something different, adjust the adapter below.
    result = import_file(tmp_path, source_key)
    return _parse_result(result)


def _parse_result(result) -> tuple[int, int]:
    """
    Adapter: normalise whatever import_file() returns into (added, dupes).

    Handles three common return styles:
      • (added, dupes)          — tuple/list of two ints
      • {"added": n, ...}       — dict with at least an "added" key
      • int                     — just the count of added rows
    """
    if isinstance(result, (tuple, list)) and len(result) >= 2:
        return int(result[0]), int(result[1])
    if isinstance(result, dict):
        added = int(result.get("added", result.get("inserted", 0)))
        dupes = int(result.get("duplicates", result.get("skipped", 0)))
        return added, dupes
    if isinstance(result, int):
        return result, 0
    # Fallback — can't determine counts
    return 0, 0


# ---------------------------------------------------------------------------
# Entrypoint (multipage mode: python runs this file directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__" or "streamlit" in sys.modules:
    render_import_page()