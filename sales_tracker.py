import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import io

# ------------------------
# Config & constants
# ------------------------
st.set_page_config(
    page_title="Daily Sales Tracker - Mannequins Ghana",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAYMENT_CHOICES = [
    "All to Company (MoMo/Bank)",
    "All to Rider (Cash)",
    "Split: Item to Company, Delivery+Tip to Rider",
]

NUMERIC_COLS = ["cost_of_item", "delivery_fee", "tip", "company_gets", "rider_gets"]

# ------------------------
# Helpers: UI / logic / DB
# ------------------------
def inject_css():
    st.markdown(
        """
        <style>
        .main { padding-top: 0rem; }
        .block-container { padding: 1rem; max-width: 100%; }
        h1,h2,h3 { margin-top: 0.5rem; margin-bottom: 0.5rem; }
        [data-testid="stDataFrame"] { height: auto; }
        .streamlit-expanderHeader { padding: 0.5rem 0rem; }
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > div {
            border-radius: 8px !important;
            border: 2px solid #e0e0e0 !important;
            padding: 0.6rem !important;
            font-size: 1rem !important;
        }
        .stTextInput > div > div > input:focus, .stNumberInput > div > div > input:focus {
            border: 2px solid #667eea !important;
            box-shadow: 0 0 8px rgba(102,126,234,0.15) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def section_header(title: str, color1: str = "#667eea", color2: str = "#764ba2", margin: str = "1rem 0"):
    st.markdown(
        f"""
        <div style='background: linear-gradient(135deg, {color1} 0%, {color2} 100%);
                    padding: 0.5rem; border-radius: 10px; margin: {margin};'>
            <h3 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
                {title}
            </h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

def compute_shares(mode: str, cost: float, fee: float, tip: float):
    """Return (company_gets, rider_gets)."""
    cost = cost or 0.0
    fee = fee or 0.0
    tip = tip or 0.0
    if mode == "All to Company (MoMo/Bank)":
        return 0.0, fee + tip
    if mode == "All to Rider (Cash)":
        return cost, 0.0
    # Split or fallback
    return 0.0, 0.0

# ---------- Supabase wrappers ----------
def supabase_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

@st.cache_data(ttl=60)
def fetch_sales_from_db():
    sup = supabase_client()
    resp = sup.table("sales").select("*").order("date", desc=True).execute()
    return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

def insert_sale_db(payload: dict):
    sup = supabase_client()
    return sup.table("sales").insert(payload).execute()

def update_sale_db(sale_id: int, payload: dict):
    sup = supabase_client()
    return sup.table("sales").update(payload).eq("id", sale_id).execute()

def delete_sale_db(sale_id: int):
    sup = supabase_client()
    return sup.table("sales").delete().eq("id", sale_id).execute()

# ---------- Data formatting helpers ----------
def ensure_numeric(df: pd.DataFrame, cols=NUMERIC_COLS):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def format_display_df(df: pd.DataFrame) -> pd.DataFrame:
    disp = df.copy()
    if "date" in disp.columns:
        disp["date"] = pd.to_datetime(disp["date"], errors="coerce")
        disp["date"] = disp["date"].dt.strftime("%a, %d/%m/%Y")
    disp = disp.rename(columns=lambda x: " ".join(word.capitalize() for word in x.split("_")))
    return disp

# ------------------------
# Inject CSS once
# ------------------------
inject_css()

# ------------------------
# Title
# ------------------------
st.markdown(
    """
    <h1 style='text-align:center; color:#4B6EAF; font-weight:700; font-family: Arial, sans-serif; margin-top: 0;'>
        Daily Sales Tracker - Mannequins Ghana
    </h1>
    <p style='text-align:center; font-size:1rem; color:#6c757d; font-family: Arial, sans-serif; margin-bottom: 1.5rem;'>
        Built with Love from Kofi ❤️
    </p>
    """,
    unsafe_allow_html=True,
)

# ------------------------
# Add Sale Form
# ------------------------
section_header("➕ Add New Sale", "#667eea", "#764ba2", "0.5rem 0 1rem 0")

with st.form("sale_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("📅 Date", datetime.now())
        location = st.text_input("📍 Location", placeholder="Enter location")
        mode = st.selectbox("💳 Payment Mode", PAYMENT_CHOICES)
    with col2:
        cost = st.number_input("💰 Cost of Item", min_value=0.0, format="%.2f", step=0.01)
        fee = st.number_input("🚚 Delivery Fee", min_value=0.0, format="%.2f", step=0.01)
        tip = st.number_input("💵 Tip", min_value=0.0, format="%.2f", step=0.01)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        submitted = st.form_submit_button("✅ Add Sale", use_container_width=True, type="primary")

if submitted:
    company_gets, rider_gets = compute_shares(mode, cost, fee, tip)
    payload = {
        "date": date.strftime("%Y-%m-%d"),
        "location": location,
        "cost_of_item": cost,
        "delivery_fee": fee,
        "tip": tip,
        "payment_mode": mode,
        "company_gets": company_gets,
        "rider_gets": rider_gets,
    }
    resp = insert_sale_db(payload)
    if resp.data:
        st.success("✅ Sale added successfully!")
        # clear cached sales so fetch returns fresh data
        fetch_sales_from_db.clear()
    else:
        st.error("❌ Failed to add sale.")
        st.write(resp)

# ------------------------
# Load sales
# ------------------------
df = fetch_sales_from_db()

if df.empty:
    st.info("📭 No data yet. Add your first sale above.")
    st.stop()

# Normalize types
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = ensure_numeric(df)

# ------------------------
# Filters (sidebar)
# ------------------------
st.sidebar.header("🔍 Filter")
unique_dates = sorted(df["date"].dt.date.dropna().unique()) if "date" in df.columns else []

if unique_dates:
    start_date, end_date = st.sidebar.select_slider(
        "Select Date Range",
        options=unique_dates,
        value=(unique_dates[0], unique_dates[-1]),
    )
else:
    start_date, end_date = None, None

locations = st.sidebar.multiselect("Locations", sorted(df["location"].dropna().unique())) if "location" in df.columns else []
payment_modes = st.sidebar.multiselect("Payment Mode", PAYMENT_CHOICES)

# Apply filters concisely
filtered = df.copy()
if start_date and end_date:
    filtered = filtered[filtered["date"].dt.date.between(start_date, end_date)]
if locations:
    filtered = filtered[filtered["location"].isin(locations)]
if payment_modes:
    filtered = filtered[filtered["payment_mode"].isin(payment_modes)]

# ------------------------
# Display filtered results (with pagination & export)
# ------------------------
if filtered.empty:
    st.warning("⚠️ No records for selected filter combination.")
else:
    display_df = format_display_df(filtered)
    section_header("📊 Filtered Sales Records", "#667eea", "#764ba2", "0.5rem 0 0.75rem 0")

    # Pagination controls
    rows_per_page = st.sidebar.number_input("Rows per page", min_value=5, max_value=200, value=10)
    total_rows = len(display_df)
    total_pages = max(1, (total_rows - 1) // rows_per_page + 1)
    page = st.sidebar.slider("Page", 1, total_pages, 1)
    start_idx = (page - 1) * rows_per_page
    end_idx = start_idx + rows_per_page
    page_df = display_df.iloc[start_idx:end_idx].reset_index(drop=True)

    # Beautiful table (read-only)
    st.data_editor(page_df, hide_index=True, use_container_width=True, disabled=True)
    st.caption(f"Showing page {page} of {total_pages} — {total_rows} records total")

    # Export buttons
    export_df = display_df.copy()
    csv_bytes = export_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv_bytes, file_name="sales_filtered.csv", mime="text/csv")

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Filtered Sales")
    st.download_button(
        "Download Excel",
        excel_buffer.getvalue(),
        file_name="sales_filtered.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # Summary stats
    section_header("💹 Summary Statistics", "#f093fb", "#f5576c", "0.75rem 0 0.5rem 0")
    sums = {
        "Delivery Fees": filtered["delivery_fee"].sum(),
        "Item Cost": filtered["cost_of_item"].sum(),
        "Tips": filtered["tip"].sum(),
        "Company": filtered["company_gets"].sum(),
        "Rider": filtered["rider_gets"].sum(),
    }
    cols = st.columns(5)
    for col, (label, val) in zip(cols, sums.items()):
        col.markdown(
            f"<div style='text-align:center'><div style='font-weight:600'>{label}</div>"
            f"<div style='font-size:1.2rem; font-weight:700'>₵{val:,.2f}</div></div>",
            unsafe_allow_html=True,
        )

    # Monthly summary
    section_header("📈 Monthly Summary", "#4facfe", "#00f2fe", "0.75rem 0 0.5rem 0")
    monthly = (
        filtered.assign(month=filtered["date"].dt.to_period("M"))
        .groupby("month")[["cost_of_item", "delivery_fee", "tip", "company_gets", "rider_gets"]]
        .sum()
        .reset_index()
    )
    if not monthly.empty:
        monthly["month"] = monthly["month"].astype(str)
        st.data_editor(monthly.rename(columns=lambda x: x.replace("_", " ").title()), hide_index=True, use_container_width=True, disabled=True)
    else:
        st.info("No monthly summary available for the selected filters.")

# ------------------------
# Edit / Delete section (uses filtered if available)
# ------------------------
section_header("🔧 Manage Records", "#667eea", "#764ba2", "0.75rem 0 0.5rem 0")
with st.expander("📝 Edit or Delete a Sale Record", expanded=False):
    selected_id = st.number_input("🔍 Enter Sale ID", min_value=1, step=1, help="Enter the ID of the record you want to edit or delete")
    target_df = filtered if "filtered" in locals() and not filtered.empty else df
    edit_row = target_df[target_df["id"] == selected_id]

    if edit_row.empty:
        st.info("ℹ️ Enter a valid Sale ID from the visible table to edit or delete.")
    else:
        st.markdown("#### 📄 Selected Record")
        st.dataframe(format_display_df(edit_row), use_container_width=True)
        st.markdown("---")
        st.markdown("#### ✏️ Edit Record Details")

        ecol1, ecol2 = st.columns(2)
        with ecol1:
            new_loc = st.text_input("📍 Location", value=str(edit_row["location"].values[0]), key=f"edit_loc_{selected_id}")
            new_cost = st.number_input("💰 Cost of Item", min_value=0.0, value=float(edit_row["cost_of_item"].values[0]), format="%.2f", key=f"edit_cost_{selected_id}")
            new_fee = st.number_input("🚚 Delivery Fee", min_value=0.0, value=float(edit_row["delivery_fee"].values[0]), format="%.2f", key=f"edit_fee_{selected_id}")
        with ecol2:
            new_tip = st.number_input("💵 Tip", min_value=0.0, value=float(edit_row["tip"].values[0]), format="%.2f", key=f"edit_tip_{selected_id}")
            cur_mode = edit_row["payment_mode"].values[0]
            default_idx = PAYMENT_CHOICES.index(cur_mode) if cur_mode in PAYMENT_CHOICES else 0
            new_mode = st.selectbox("💳 Payment Mode", PAYMENT_CHOICES, index=default_idx, key=f"edit_mode_{selected_id}")

        # Reuse compute_shares
        company_gets, rider_gets = compute_shares(new_mode, new_cost, new_fee, new_tip)

        st.markdown("---")
        b1, b2, b3 = st.columns([1, 1, 2])
        with b1:
            if st.button("✅ Update Record", type="primary", use_container_width=True):
                payload = {
                    "location": new_loc,
                    "cost_of_item": new_cost,
                    "delivery_fee": new_fee,
                    "tip": new_tip,
                    "payment_mode": new_mode,
                    "company_gets": company_gets,
                    "rider_gets": rider_gets,
                }
                resp = update_sale_db(int(selected_id), payload)
                if resp.data:
                    st.success("✅ Record updated successfully!")
                    fetch_sales_from_db.clear()
                    st.experimental_rerun()
                else:
                    st.error("❌ Failed to update record.")
                    st.write(resp)
        with b2:
            if st.button("🗑️ Delete Record", type="secondary", use_container_width=True):
                resp = delete_sale_db(int(selected_id))
                if resp.data:
                    st.success("🗑️ Record deleted successfully!")
                    fetch_sales_from_db.clear()
                    st.experimental_rerun()
                else:
                    st.error("❌ Failed to delete record.")
                    st.write(resp)
