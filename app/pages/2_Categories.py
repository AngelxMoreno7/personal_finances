"""
Categories management page — save as app/pages/2_Categories.py

Lets users:
  • Add / rename / delete subcategories
  • Change which parent category a subcategory belongs to
  • Edit keywords that trigger a subcategory
  • Change subcategory colors
  • Add / rename parent categories

All changes write back to config/categories.yaml.
An optional "Save & Recategorize" button re-runs categorization on all
non-manually-categorized transactions after saving.
"""

import sys
from pathlib import Path

import streamlit as st
import yaml

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # personal_finances/
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

YAML_PATH = PROJECT_ROOT / "config" / "categories.yaml"

# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_yaml() -> dict:
    with open(YAML_PATH, "r") as f:
        return yaml.safe_load(f)


def save_yaml(data: dict) -> None:
    with open(YAML_PATH, "w") as f:
        yaml.dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def get_categories(data: dict) -> list[str]:
    """Return sorted unique parent category names from all subcategories."""
    cats = set()
    for sub in data.get("categories", {}).values():
        if isinstance(sub, dict) and "category" in sub:
            cats.add(sub["category"])
    return sorted(cats)


def parse_keywords(raw: str) -> list[str]:
    """Split a textarea of keywords (one per line) into a clean list."""
    return [line.strip() for line in raw.strip().splitlines() if line.strip()]


def keywords_to_text(keywords: list) -> str:
    """Convert keyword list to newline-separated string for textarea."""
    return "\n".join(str(k) for k in (keywords or []))


# ---------------------------------------------------------------------------
# Session state init
# ---------------------------------------------------------------------------
def init_state():
    if "cat_data" not in st.session_state:
        st.session_state.cat_data = load_yaml()
    if "cat_dirty" not in st.session_state:
        st.session_state.cat_dirty = False
    if "cat_selected_sub" not in st.session_state:
        st.session_state.cat_selected_sub = None
    if "cat_new_parent" not in st.session_state:
        st.session_state.cat_new_parent = ""


# ---------------------------------------------------------------------------
# Save helpers
# ---------------------------------------------------------------------------
def save_changes(recategorize: bool = False):
    save_yaml(st.session_state.cat_data)
    st.session_state.cat_dirty = False
    if recategorize:
        _run_recategorize()


def _run_recategorize():
    try:
        from scripts.recategorize import recategorize_all
        recategorize_all()
        st.success("✅ Saved and recategorized all transactions.")
    except Exception as exc:
        st.error(f"Saved to YAML, but recategorize failed: {exc}")


# ---------------------------------------------------------------------------
# Main render
# ---------------------------------------------------------------------------
def render_categories_page():
    init_state()
    data = st.session_state.cat_data
    subcats = data.get("categories", {})

    st.header("🗂️ Manage Categories")
    st.caption("Changes are held in memory until you save. Closing the page without saving discards edits.")

    with st.expander("How does this page work? →", expanded=False):
        st.markdown("""
        #### Page layout
        The page is split into two panels. The **left panel** lists all your subcategories
        grouped under their parent category (e.g. *Food*, *Vices*, *Shopping*). Click any
        subcategory to open its editor in the **right panel**.

        #### Categories vs subcategories
        **Parent categories** are the top-level groupings (e.g. *Food*) — they act as headers
        in charts and filters. **Subcategories** are the actual labels assigned to transactions
        (e.g. *Groceries*, *Dining Out*, *Coffee*). Every subcategory belongs to one parent.

        #### Keywords
        Keywords are the phrases the app searches for inside your bank's transaction
        descriptions. When a transaction comes in, the app scans its description for any
        keyword in your list — if it finds a match, that transaction gets assigned to this
        subcategory. One keyword per line. Shorter, partial phrases work better than full
        descriptions (e.g. `trader joe` catches *TRADER JOE'S #123 ANAHEIM CA*).

        #### Amount-specific keywords
        Sometimes a transaction is too generic to categorize by description alone. For example,
        Zelle, Apple Cash, or Venmo payments often show up as something like *"Zelle payment to
        John"* — not helpful on its own. If you have a recurring expense sent through one of
        these services for a consistent dollar amount, you can pair the description with an exact
        amount so the app can reliably catch it (e.g. description: `zelle payment to landlord`,
        amount: `1500`).

        #### Editing safely
        Edits are safe to explore — nothing touches your YAML file until you press **Save**.
        Use **Discard** at any time to undo everything back to the last saved state.

        #### Save vs Save & Recategorize
        **Save** updates `categories.yaml` so future imports use your new keywords, but existing
        transactions in the database are not affected. **Save & Recategorize** does both — it
        saves the YAML and then re-scans all non-manually-categorized transactions against your
        updated keywords. Use this when you've added or fixed a keyword and want it to apply
        to transactions already in the app.
        """)

    # ── Dirty banner ─────────────────────────────────────────────────────────
    if st.session_state.cat_dirty:
        st.warning("⚠️ You have unsaved changes.")

    # ── Layout: left panel (list) | right panel (editor) ─────────────────────
    left, right = st.columns([1, 2], gap="large")

    # ════════════════════════════════════════════════════════════════════════
    # LEFT — subcategory list grouped by parent
    # ════════════════════════════════════════════════════════════════════════
    with left:
        st.subheader("Subcategories")

        # Group subcategories by parent
        grouped: dict[str, list[str]] = {}
        no_parent: list[str] = []
        for sub_name, sub_data in subcats.items():
            parent = sub_data.get("category") if isinstance(sub_data, dict) else None
            if parent:
                grouped.setdefault(parent, []).append(sub_name)
            else:
                no_parent.append(sub_name)

        # Render each group
        for parent in sorted(grouped.keys()):
            st.markdown(f"**{parent}**")
            for sub_name in sorted(grouped[parent]):
                color = subcats[sub_name].get("color", "#888888") if isinstance(subcats[sub_name], dict) else "#888888"
                label = f"🔹 {sub_name}"
                is_selected = st.session_state.cat_selected_sub == sub_name
                if st.button(
                    label,
                    key=f"select_{sub_name}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.cat_selected_sub = sub_name
                    st.rerun()

        if no_parent:
            st.markdown("**No parent assigned**")
            for sub_name in sorted(no_parent):
                is_selected = st.session_state.cat_selected_sub == sub_name
                if st.button(
                    f"🔹 {sub_name}",
                    key=f"select_{sub_name}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary",
                ):
                    st.session_state.cat_selected_sub = sub_name
                    st.rerun()

        st.divider()

        # ── Add new subcategory ───────────────────────────────────────────────
        st.markdown("**Add subcategory**")
        new_sub_name = st.text_input("Name", key="new_sub_name", placeholder="e.g. Subscriptions")
        if st.button("➕ Add", use_container_width=True):
            name = new_sub_name.strip()
            if not name:
                st.error("Enter a subcategory name.")
            elif name in subcats:
                st.error(f'"{name}" already exists.')
            else:
                subcats[name] = {"category": "", "color": "#888888", "keywords": []}
                st.session_state.cat_dirty = True
                st.session_state.cat_selected_sub = name
                st.rerun()

        st.divider()

        # ── Add new parent category ───────────────────────────────────────────
        st.markdown("**Add parent category**")
        st.caption("Parent categories are defined by being referenced in subcategories. Adding one here creates a placeholder subcategory you can rename.")
        new_parent_name = st.text_input("Parent name", key="new_parent_name", placeholder="e.g. Health")
        if st.button("➕ Add parent", use_container_width=True):
            pname = new_parent_name.strip()
            existing_parents = get_categories(data)
            if not pname:
                st.error("Enter a parent category name.")
            elif pname in existing_parents:
                st.error(f'"{pname}" already exists.')
            else:
                placeholder = f"{pname} - General"
                subcats[placeholder] = {"category": pname, "color": "#888888", "keywords": []}
                st.session_state.cat_dirty = True
                st.session_state.cat_selected_sub = placeholder
                st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # RIGHT — editor for selected subcategory
    # ════════════════════════════════════════════════════════════════════════
    with right:
        selected = st.session_state.cat_selected_sub

        if not selected or selected not in subcats:
            st.info("← Select a subcategory to edit it.")
        else:
            sub_data = subcats[selected]
            if not isinstance(sub_data, dict):
                sub_data = {}

            st.subheader(f"Editing: {selected}")

            # ── Rename ────────────────────────────────────────────────────────
            with st.expander("✏️ Rename subcategory", expanded=False):
                new_name = st.text_input("New name", value=selected, key="rename_input")
                if st.button("Rename", key="rename_btn"):
                    new_name = new_name.strip()
                    if not new_name:
                        st.error("Name cannot be empty.")
                    elif new_name == selected:
                        st.info("Name unchanged.")
                    elif new_name in subcats:
                        st.error(f'"{new_name}" already exists.')
                    else:
                        subcats[new_name] = subcats.pop(selected)
                        st.session_state.cat_selected_sub = new_name
                        st.session_state.cat_dirty = True
                        st.rerun()

            # ── Parent category ───────────────────────────────────────────────
            st.markdown("**Parent category**")
            all_parents = get_categories(data)
            current_parent = sub_data.get("category", "")

            # Allow typing a new parent or choosing existing
            parent_options = ["— none —"] + all_parents
            current_idx = (
                parent_options.index(current_parent)
                if current_parent in parent_options
                else 0
            )
            chosen_parent = st.selectbox(
                "Assign to",
                options=parent_options,
                index=current_idx,
                key=f"parent_select_{selected}",
            )
            new_parent_typed = st.text_input(
                "Or type a new parent category",
                placeholder="Creates a new parent if it doesn't exist",
                key=f"parent_typed_{selected}",
            )
            if st.button("Apply parent", key=f"apply_parent_{selected}"):
                final_parent = new_parent_typed.strip() or (
                    "" if chosen_parent == "— none —" else chosen_parent
                )
                sub_data["category"] = final_parent
                subcats[selected] = sub_data
                st.session_state.cat_dirty = True
                st.success(f"Parent set to '{final_parent}'." if final_parent else "Parent cleared.")

            st.divider()

            # ── Color ─────────────────────────────────────────────────────────
            st.markdown("**Color**")
            current_color = sub_data.get("color", "#888888")
            # Ensure valid hex
            if not (isinstance(current_color, str) and current_color.startswith("#") and len(current_color) in (4, 7)):
                current_color = "#888888"
            new_color = st.color_picker("Pick a color", value=current_color, key=f"color_{selected}")
            if new_color != current_color:
                sub_data["color"] = new_color
                subcats[selected] = sub_data
                st.session_state.cat_dirty = True

            st.divider()

            # ── Keywords ──────────────────────────────────────────────────────
            st.markdown("**Keywords**")
            st.caption("One keyword per line. Case-insensitive. Transactions matching any keyword are assigned this subcategory.")

            # Separate plain keywords from amount_keywords
            raw_keywords = sub_data.get("keywords", [])
            plain_keywords = [k for k in raw_keywords if isinstance(k, str)]
            amount_keywords = sub_data.get("amount_keywords", [])

            kw_text = st.text_area(
                "Keywords",
                value=keywords_to_text(plain_keywords),
                height=200,
                key=f"kw_{selected}",
                label_visibility="collapsed",
            )
            if st.button("Apply keywords", key=f"apply_kw_{selected}"):
                sub_data["keywords"] = parse_keywords(kw_text)
                subcats[selected] = sub_data
                st.session_state.cat_dirty = True
                st.success("Keywords updated.")

            # ── Amount keywords (advanced) ────────────────────────────────────
            if amount_keywords:
                with st.expander("⚙️ Amount-specific keywords (advanced)", expanded=False):
                    st.caption("These rules match only when both the description AND amount match exactly.")
                    for i, ak in enumerate(amount_keywords):
                        c1, c2, c3 = st.columns([3, 2, 1])
                        new_desc = c1.text_input("Description", value=ak.get("description", ""), key=f"ak_desc_{selected}_{i}")
                        new_amt = c2.number_input("Amount", value=float(ak.get("amount", 0)), key=f"ak_amt_{selected}_{i}")
                        if c3.button("🗑️", key=f"ak_del_{selected}_{i}"):
                            amount_keywords.pop(i)
                            sub_data["amount_keywords"] = amount_keywords
                            subcats[selected] = sub_data
                            st.session_state.cat_dirty = True
                            st.rerun()
                        else:
                            amount_keywords[i] = {"description": new_desc, "amount": new_amt}

                    if st.button("Apply amount keywords", key=f"apply_ak_{selected}"):
                        sub_data["amount_keywords"] = amount_keywords
                        subcats[selected] = sub_data
                        st.session_state.cat_dirty = True
                        st.success("Amount keywords updated.")

            # Add new amount keyword
            with st.expander("➕ Add amount-specific keyword", expanded=False):
                ak_desc = st.text_input("Description (exact)", key=f"new_ak_desc_{selected}")
                ak_amt = st.number_input("Amount (exact)", key=f"new_ak_amt_{selected}")
                if st.button("Add", key=f"add_ak_{selected}"):
                    if not ak_desc.strip():
                        st.error("Enter a description.")
                    else:
                        existing = sub_data.get("amount_keywords", [])
                        existing.append({"description": ak_desc.strip(), "amount": ak_amt})
                        sub_data["amount_keywords"] = existing
                        subcats[selected] = sub_data
                        st.session_state.cat_dirty = True
                        st.success("Added.")

            st.divider()

            # ── Delete subcategory ────────────────────────────────────────────
            with st.expander("🗑️ Delete this subcategory", expanded=False):
                st.warning(
                    f'Deleting **{selected}** removes it from the YAML. '
                    "Transactions already assigned to it keep their assignment until recategorized."
                )
                confirm = st.checkbox(f'Yes, delete "{selected}"', key=f"confirm_delete_{selected}")
                if st.button("Delete", type="primary", key=f"delete_btn_{selected}", disabled=not confirm):
                    del subcats[selected]
                    st.session_state.cat_selected_sub = None
                    st.session_state.cat_dirty = True
                    st.rerun()

    # ════════════════════════════════════════════════════════════════════════
    # SAVE BAR — pinned at bottom
    # ════════════════════════════════════════════════════════════════════════
    st.divider()
    save_col, recategorize_col, reload_col = st.columns([2, 2, 1])

    with save_col:
        if st.button(
            "💾 Save to YAML",
            use_container_width=True,
            disabled=not st.session_state.cat_dirty,
            type="primary",
        ):
            save_changes(recategorize=False)
            st.success("✅ Saved to config/categories.yaml")

    with recategorize_col:
        if st.button(
            "💾 Save & Recategorize",
            use_container_width=True,
            disabled=not st.session_state.cat_dirty,
            help="Saves the YAML then re-runs categorization on all non-manually-categorized transactions.",
        ):
            save_changes(recategorize=True)

    with reload_col:
        if st.button("↩️ Discard", use_container_width=True, help="Discard all unsaved changes and reload from YAML."):
            st.session_state.cat_data = load_yaml()
            st.session_state.cat_dirty = False
            st.session_state.cat_selected_sub = None
            st.rerun()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__" or "streamlit" in sys.modules:
    render_categories_page()
