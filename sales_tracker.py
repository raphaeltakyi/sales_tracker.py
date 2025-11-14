import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

# Initialize Supabase client securely via secrets
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# App title with a subtitle for clarity
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

# Payment options as a constant for reuse
PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]

# --- Add Sale Form ---
with st.form("sale_form", clear_on_submit=True):
    st.header("Add a New Sale")
    col1, col2 = st.columns([3, 2], gap="medium")
    with col1:
        date = st.date_input("Date", value=datetime.now(), help="Select the sale date")
        location = st.text_input("Location", placeholder="Enter sale location")
    with col2:
        cost = st.number_input("Cost of Item (₵)", min_value=0.0, format="%.2f", step=0.01)
        fee = st.number_input("Delivery Fee (₵)", min_value=0.0, format="%.2f", step=0.01)
        tip = st.number_input("Tip (₵)", min_value=0.0, format="%.2f", step=0.01)
        mode = st.selectbox("Payment Mode", PAYMENT_CHOICES)
    submitted = st.form_submit_button("Add Sale")

# Handle form submission with validation and data insertion
if submitted:
    if not location.strip():
        st.error("Please enter a location.")
    else:
        # Compute pay distribution based on mode
        if mode == PAYMENT_CHOICES[0]:
            company_gets = cost + fee + tip
            rider_gets = 0.0
        elif mode == PAYMENT_CHOICES[1]:
            company_gets = 0.0
            rider_gets = cost + fee + tip
        else:
            company_gets = cost
            rider_gets = fee + tip

        data = {
            "date": date.strftime('%Y-%m-%d'),
            "location": location.strip(),
            "cost_of_item": cost,
            "delivery_fee": fee,
            "tip": tip,
            "payment_mode": mode,
            "company_gets": company_gets,
            "rider_gets": rider_gets,
        }
        response = supabase.table("sales").insert(data).execute()
        if response.data:
            st.success("Sale added successfully! 🎉")
        else:
            st.error("Failed to add sale. Please try again.")
            st.json(response)

# --- Fetch all sales records for display and filtering ---
response = supabase.table("sales").select("*").order("date", desc=True).execute()
df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

if df.empty:
    st.info('No sales data available. Add your first sale above.')
else:
    # Data preprocessing
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for col in ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    st.sidebar.header("Filters")

    # -- Date Preset Logic --
    date_list = sorted(df['date'].dt.date.dropna().unique())
    min_date = min(date_list)
    max_date = max(date_list)
    def valid_preset(name):
        today = datetime.now().date()
        if name == "Today":
            # Always clamp to available data
            d0 = d1 = today
            if d0 < min_date or d0 > max_date:
                d0 = d1 = max_date
        elif name == "Last 7 Days":
            d0 = max(today - timedelta(days=6), min_date)
            d1 = min(today, max_date)
        elif name == "This Month":
            month_start = today.replace(day=1)
            d0 = max(month_start, min_date)
            d1 = min(today, max_date)
        else:
            d0, d1 = min_date, max_date
        return (d0, d1)

    preset_options = ["Today", "Last 7 Days", "This Month", "All Time"]
    st.sidebar.subheader("Date Range Preset")
    preset = st.sidebar.selectbox("Quick Select", preset_options, index=3)
    start_preset, end_preset = valid_preset(preset)

    # --- Robust Date Range Selector ---
    selected_range = st.sidebar.date_input(
        "Or Select Date Range (dd/mm/yyyy)",
        value=(start_preset, end_preset),
        min_value=min_date,
        max_value=max_date,
        format="DD/MM/YYYY"
    )
    # Accept tuple, one-element tuple, or single date; never crash as user picks.
    if isinstance(selected_range, tuple):
        if len(selected_range) == 2:
            start_date, end_date = selected_range
        elif len(selected_range) == 1:
            start_date = end_date = selected_range[0]
        else:
            start_date = end_date = min_date
    else:
        start_date = end_date = selected_range

    # If user picks in reverse, auto-swap
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    # Clamp dates to min/max
    start_date, end_date = max(start_date, min_date), min(end_date, max_date)
    st.sidebar.markdown(f"**Selected Range:** {start_date.strftime('%d/%m/%Y')} &ndash; {end_date.strftime('%d/%m/%Y')}")

    # Other filters
    locations = st.sidebar.multiselect(
        "Locations", options=sorted(df['location'].dropna().unique()), default=None)
    payment_modes = st.sidebar.multiselect(
        "Payment Modes", options=PAYMENT_CHOICES, default=None)

    # Apply filters
    mask = pd.Series(True, index=df.index)
    mask &= (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    if locations:
        mask &= df['location'].isin(locations)
    if payment_modes:
        mask &= df['payment_mode'].isin(payment_modes)

    filtered = df[mask]

    if filtered.empty:
        st.warning("No records match the selected filter criteria.")
    else:
        display_df = filtered.copy()
        display_df['date'] = display_df['date'].dt.strftime('%d/%m/%Y')
        display_df = display_df.rename(columns=lambda s: ' '.join(word.capitalize() for word in s.split('_')))
        st.subheader("Filtered Sales Records")
        st.dataframe(display_df.reset_index(drop=True), use_container_width=True)

        st.subheader("Summary Statistics")
        sums = {
            'Total Delivery Fees (₵)': filtered['delivery_fee'].sum(),
            'Total Item Cost (₵)': filtered['cost_of_item'].sum(),
            'Total Tips (₵)': filtered['tip'].sum(),
            'Total Owed To Company (₵)': filtered['company_gets'].sum(),
            'Total Owed To Rider (₵)': filtered['rider_gets'].sum(),
        }
        cols = st.columns(len(sums))
        for col, (name, value) in zip(cols, sums.items()):
            col.metric(label=name, value=f"{value:.2f}")

# --- Edit/Delete Section ---
st.divider()
st.header("Edit or Delete a Sale Record")

selected_id = st.number_input(
    "Enter Sale ID to Edit/Delete",
    min_value=1,
    step=1,
    help="Find the sale ID from the filtered sales table above"
)

edit_row = df[df['id'] == selected_id]

if not edit_row.empty:
    st.write("Selected Record:")
    display_row = edit_row.copy()
    display_row['date'] = display_row['date'].dt.strftime('%d/%m/%Y')
    display_row = display_row.rename(columns=lambda s: ' '.join(word.capitalize() for word in s.split('_')))
    st.dataframe(display_row, use_container_width=True)

    # Edit form inputs
    new_loc = st.text_input("New Location", value=str(edit_row['location'].values[0]), key='edit_loc')
    new_cost = st.number_input("New Cost of Item (₵)", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', step=0.01, key='edit_cost')
    new_fee = st.number_input("New Delivery Fee (₵)", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', step=0.01, key='edit_fee')
    new_tip = st.number_input("New Tip (₵)", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', step=0.01, key='edit_tip')
    selected_mode = edit_row['payment_mode'].values[0]
    default_index = PAYMENT_CHOICES.index(selected_mode) if selected_mode in PAYMENT_CHOICES else 0
    new_mode = st.selectbox("New Payment Mode", PAYMENT_CHOICES, index=default_index, key='edit_mode')

    # Recompute payment splits
    if new_mode == PAYMENT_CHOICES[0]:
        company_gets = new_cost + new_fee + new_tip
        rider_gets = 0.0
    elif new_mode == PAYMENT_CHOICES[1]:
        company_gets = 0.0
        rider_gets = new_cost + new_fee + new_tip
    else:
        company_gets = new_cost
        rider_gets = new_fee + new_tip

    col_edit, col_delete = st.columns(2)
    with col_edit:
        if st.button("Update Record"):
            update_data = {
                "location": new_loc.strip(),
                "cost_of_item": new_cost,
                "delivery_fee": new_fee,
                "tip": new_tip,
                "payment_mode": new_mode,
                "company_gets": company_gets,
                "rider_gets": rider_gets,
            }
            response = supabase.table("sales").update(update_data).eq("id", int(selected_id)).execute()
            if response.data:
                st.success("Record updated successfully!")
                st.experimental_rerun()
            else:
                st.error("Failed to update record.")
                st.json(response)
    with col_delete:
        if st.button("Delete Record", type="secondary"):
            response = supabase.table("sales").delete().eq("id", int(selected_id)).execute()
            if response.data:
                st.success("Record deleted successfully.")
                st.experimental_rerun()
            else:
                st.error("Failed to delete record.")
                st.json(response)
else:
    st.info("Enter a valid Sale ID from the table above to edit or delete a record.")
