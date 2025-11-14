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

if submitted:
    if not location.strip():
        st.error("Please enter a location.")
    else:
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
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for col in ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    st.sidebar.header("Filters")

    unique_dates = sorted(df['date'].dt.date.dropna().unique())
    min_date = unique_dates[0]
    max_date = unique_dates[-1]
    today = datetime.now().date()

    def get_preset_dates(preset):
        # Start is always min_date in data
        start = min_date
        # End is based on quick_select, but always <= today and <= max_date
        if preset == "Today":
            end = today if today <= max_date else max_date
        elif preset == "This Week":
            week_end = today
            end = week_end if week_end <= max_date else max_date
        elif preset == "This Month":
            month_end = today
            end = month_end if month_end <= max_date else max_date
        else:  # All Time
            end = max_date
        if end < start:  # edge case if data is newer than today
            end = start
        return (start, end)

    quick_options = ["Today", "This Week", "This Month", "All Time"]
    st.sidebar.subheader("Date Range Preset")
    quick_select = st.sidebar.selectbox("Quick Select", quick_options, index=3)
    preset_start, preset_end = get_preset_dates(quick_select)

    # Date input in range mode: always robust, falls back to preset, user can manually adjust
    selected_range = st.sidebar.date_input(
        "Date Range (dd/mm/yyyy)",
        value=(preset_start, preset_end),
        min_value=min_date,
        max_value=max_date
    )
    # Accept tuple, one-date, or single date output
    if isinstance(selected_range, tuple):
        if len(selected_range) == 2:
            start_date, end_date = selected_range
        elif len(selected_range) == 1:
            start_date = end_date = selected_range[0]
        else:
            start_date = end_date = min_date
    else:
        start_date = end_date = selected_range

    # If user picks reverse, auto-swap
    if start_date > end_date:
        start_date, end_date = end_date, start_date

    st.sidebar.markdown(
        f"**Selected Range:** {start_date.strftime('%d/%m/%Y')} &ndash; {end_date.strftime('%d/%m/%Y')}"
    )

    # --- Other filters ---
    locations = st.sidebar.multiselect(
        "Locations", options=sorted(df['location'].dropna().unique()), default=None)
    payment_modes = st.sidebar.multiselect(
        "Payment Modes", options=PAYMENT_CHOICES, default=None)

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
        display_df['date'] = display_df['date'].dt.strftime('%a, %d/%m/%Y')
        display_df = display_df.rename(columns=lambda s: ' '.join(word.capitalize() for word in s.split('_')))
        st.subheader("Filtered Sales Records")
        st.dataframe(display_df.reset_index(drop=True), use_container_width=True)

        st.subheader("Summary Statistics")
        sums = {
            'Total Delivery Fees (₵)': int(filtered['delivery_fee'].sum()),
            'Total Item Cost (₵)': int(filtered['cost_of_item'].sum()),
            'Total Tips (₵)': int(filtered['tip'].sum()),
            'Total Owed To Company (₵)': int(filtered['company_gets'].sum()),
            'Total Owed To Rider (₵)': int(filtered['rider_gets'].sum()),
        }

        cols = st.columns(len(sums))
        for col, (name, value) in zip(cols, sums.items()):
            col.metric(label=name, value=f"{value}")

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
    display_row['date'] = display_row['date'].dt.strftime('%a, %d/%m/%Y')
    display_row = display_row.rename(columns=lambda s: ' '.join(word.capitalize() for word in s.split('_')))
    st.dataframe(display_row, use_container_width=True)

    new_loc = st.text_input("New Location", value=str(edit_row['location'].values[0]), key='edit_loc')
    new_cost = st.number_input("New Cost of Item (₵)", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', step=0.01, key='edit_cost')
    new_fee = st.number_input("New Delivery Fee (₵)", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', step=0.01, key='edit_fee')
    new_tip = st.number_input("New Tip (₵)", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', step=0.01, key='edit_tip')
    selected_mode = edit_row['payment_mode'].values[0]
    default_index = PAYMENT_CHOICES.index(selected_mode) if selected_mode in PAYMENT_CHOICES else 0
    new_mode = st.selectbox("New Payment Mode", PAYMENT_CHOICES, index=default_index, key='edit_mode')

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
    st.info("Enter a valid Sale ID from the filtered table above to edit or delete a record.")
