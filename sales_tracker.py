import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
import io

# Initialize Supabase client
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- Title and subtitle
st.markdown(
    """
    <h1 style='text-align:center; color:#4B6EAF; font-weight:700; font-family: Arial, sans-serif;'>
        Daily Sales Tracker - Mannequins Ghana
    </h1>
    <p style='text-align:center; font-size:1rem; color:#6c757d; font-family: Arial, sans-serif;'>
        Built with Love from Kofi ❤️
    </p>
    <hr>
    """, 
    unsafe_allow_html=True,
)

PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]

def compute_shares(mode, cost, fee, tip):
    """Compute company and rider shares."""
    if mode == 'All to Company (MoMo/Bank)':
        return 0.0, fee + tip
    if mode == 'All to Rider (Cash)':
        return cost, 0.0
    return 0.0, 0.0

# --- Add a sale form ---
with st.form("sale_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    date = col1.date_input("Date", datetime.now())
    location = col1.text_input("Location")
    cost = col2.number_input("Cost of Item", min_value=0.0, format='%.2f')
    fee = col2.number_input("Delivery Fee", min_value=0.0, format='%.2f')
    tip = col2.number_input("Tip", min_value=0.0, format='%.2f')
    mode = col1.selectbox("Payment Mode", PAYMENT_CHOICES)
    submitted = st.form_submit_button("Add Sale")

if submitted:
    company_gets, rider_gets = compute_shares(mode, cost, fee, tip)
    data = {
        "date": date.strftime('%Y-%m-%d'),
        "location": location,
        "cost_of_item": cost,
        "delivery_fee": fee,
        "tip": tip,
        "payment_mode": mode,
        "company_gets": company_gets,
        "rider_gets": rider_gets
    }
    response = supabase.table("sales").insert(data).execute()
    st.success("Sale added!") if response.data else st.error("Failed to add sale.")

# --- Fetch all sales ---
response = supabase.table("sales").select("*").order("date", desc=True).execute()
df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

if df.empty:
    st.info('No data yet. Add your first sale above.')
    st.stop()

# Prepare dataframe
df['date'] = pd.to_datetime(df['date'], errors='coerce')
numeric_cols = ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']
df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors='coerce')

# --- Sidebar Filters ---
st.sidebar.header('Filter')
unique_dates = sorted(df['date'].dt.date.dropna().unique())

start_date, end_date = st.sidebar.select_slider(
    'Select Date Range',
    options=unique_dates,
    value=(unique_dates[0], unique_dates[-1])
)

locations = st.sidebar.multiselect('Locations', sorted(df['location'].dropna().unique()))
payment_modes = st.sidebar.multiselect('Payment Mode', PAYMENT_CHOICES)

# Apply filters
mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
if locations:
    mask &= df['location'].isin(locations)
if payment_modes:
    mask &= df['payment_mode'].isin(payment_modes)
filtered = df[mask]

# --- Filtered Table & Summaries ---
if filtered.empty:
    st.warning("No records for selected filter combination.")
else:
    filtered_display = filtered.copy()
    filtered_display['date'] = filtered_display['date'].dt.strftime('%a, %d/%m/%Y')
    filtered_display = filtered_display.rename(columns=lambda x: x.replace('_', ' ').title())

    st.subheader('Filtered Sales')

    # --------------------------
    # PAGINATION
    # --------------------------
    rows_per_page = st.sidebar.number_input("Rows per page", 5, 100, 10)
    total_rows = len(filtered_display)
    total_pages = (total_rows - 1) // rows_per_page + 1
    page = st.sidebar.slider("Page", 1, total_pages, 1)

    start = (page - 1) * rows_per_page
    end = start + rows_per_page
    page_data = filtered_display.iloc[start:end]

    # Beautiful table
    st.data_editor(
        page_data.reset_index(drop=True),
        hide_index=True,
        use_container_width=True,
        disabled=True
    )
    st.caption(f"Showing page {page} of {total_pages}")

    # --------------------------
    # EXPORT OPTIONS
    # --------------------------
    export_df = filtered_display.copy()

    csv_data = export_df.to_csv(index=False)
    st.download_button("Download CSV", csv_data, "sales_filtered.csv", "text/csv")

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="Filtered Sales")

    st.download_button(
        "Download Excel",
        excel_buffer.getvalue(),
        "sales_filtered.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # --------------------------
    # SUMMARY STATISTICS
    # --------------------------
    st.subheader('Summary Statistics')
    col_sum1, col_sum2, col_sum3, col_sum4, col_sum5 = st.columns(5)

    col_sum1.metric('Total Delivery Fees', f"₵{filtered['delivery_fee'].sum():.2f}")
    col_sum2.metric('Total Item Cost', f"₵{filtered['cost_of_item'].sum():.2f}")
    col_sum3.metric('Total Tips', f"₵{filtered['tip'].sum():.2f}")
    col_sum4.metric('Total Owed To Company', f"₵{filtered['company_gets'].sum():.2f}")
    col_sum5.metric('Total Owed To Rider', f"₵{filtered['rider_gets'].sum():.2f}")

    # --------------------------
    # MONTHLY SUMMARY
    # --------------------------
    st.subheader("Monthly Summary")

    monthly = (
        filtered.assign(month=filtered["date"].dt.to_period("M"))
                .groupby("month")[["cost_of_item", "delivery_fee", "tip", "company_gets", "rider_gets"]]
                .sum()
                .reset_index()
    )
    monthly["month"] = monthly["month"].astype(str)

    st.data_editor(
        monthly.rename(columns=lambda x: x.replace('_', ' ').title()),
        hide_index=True,
        use_container_width=True,
        disabled=True
    )

# --- Edit/Delete section (same logic preserved) ---
st.subheader("Edit or Delete a Sale Record")
with st.expander("Edit/Delete Record", expanded=True):
    selected_id = st.number_input("Enter Sale ID to Edit/Delete", min_value=1, step=1, key='select_id')
    edit_row = filtered[filtered['id'] == selected_id]

    if edit_row.empty:
        st.info("Enter a valid Sale ID to edit or delete.")
    else:
        st.write("Selected Record:")
        row_display = edit_row.copy()
        row_display['date'] = row_display['date'].dt.strftime('%a, %d/%m/%Y')
        row_display = row_display.rename(columns=lambda x: x.replace('_', ' ').title())
        st.data_editor(row_display, hide_index=True, disabled=True)

        new_loc = st.text_input("New Location", value=str(edit_row['location'].values[0]))
        new_cost = st.number_input("New Cost of Item", min_value=0.0, value=float(edit_row['cost_of_item']), format='%.2f')
        new_fee = st.number_input("New Delivery Fee", min_value=0.0, value=float(edit_row['delivery_fee']), format='%.2f')
        new_tip = st.number_input("New Tip", min_value=0.0, value=float(edit_row['tip']), format='%.2f')

        selected_mode = edit_row['payment_mode'].values[0]
        default_index = PAYMENT_CHOICES.index(selected_mode) if selected_mode in PAYMENT_CHOICES else 0
        new_mode = st.selectbox("New Payment Mode", PAYMENT_CHOICES, index=default_index)

        company_gets, rider_gets = compute_shares(new_mode, new_cost, new_fee, new_tip)

        if st.button("Update Record"):
            update_data = {
                "location": new_loc,
                "cost_of_item": new_cost,
                "delivery_fee": new_fee,
                "tip": new_tip,
                "payment_mode": new_mode,
                "company_gets": company_gets,
                "rider_gets": rider_gets
            }
            response = supabase.table("sales").update(update_data).eq("id", int(selected_id)).execute()
            st.success("Record updated!") if response.data else st.error("Failed to update record.")
            st.experimental_rerun()

        if st.button("Delete Record"):
            response = supabase.table("sales").delete().eq("id", int(selected_id)).execute()
            st.success("Record deleted!") if response.data else st.error("Failed to delete record.")
            st.experimental_rerun()
