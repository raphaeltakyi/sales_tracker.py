import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# Initialize Supabase client via secrets
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

# --- Fetch all sales for display and filter ---
response = supabase.table("sales").select("*").order("date", desc=True).execute()
df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

if df.empty:
    st.info('No sales data available. Add your first sale above.')
else:
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for col in ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    st.sidebar.header("Filters")

    # --- Quick Select + Date Slider ---
    unique_dates = sorted(df['date'].dt.date.dropna().unique())
    min_date = unique_dates[0]
    max_date = unique_dates[-1]
    today = datetime.now().date()

    def get_flexible_end_date(d):
        return d if d <= max_date else max_date

    def get_preset_dates(preset):
        start = min_date
        if preset == "Today":
            end = get_flexible_end_date(today)
        elif preset == "This Week":
            end = get_flexible_end_date(today)
        elif preset == "This Month":
            end = get_flexible_end_date(today)
        else:  # "All Time"
            end = max_date
        return (start, end)

    quick_options = ["Today", "This Week", "This Month", "All Time"]
    st.sidebar.subheader("Date Range Preset")
    quick_select = st.sidebar.selectbox("Quick Select", quick_options, index=3)
    preset_start, preset_end = get_preset_dates(quick_select)

    # --- Date Slider for filtering
    start_date, end_date = st.sidebar.select_slider(
        "Select Date Range",
        options=unique_dates,
        value=(preset_start, preset_end),
        help="Filter sales within this date range"
    )

    st.sidebar.markdown(f"**Selected Range:** {start_date.strftime('%d/%m/%Y')} &ndash; {end_date.strftime('%d/%m/%Y')}")

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
            'Total Delivery Fees (₵)': filtered['delivery_fee'].sum(),
            'Total Item Cost (₵)': filtered['cost_of_item'].sum(),
            'Total Tips (₵)': filtered['tip'].sum(),
            'Total Owed To Company (₵)': filtered['company_gets'].sum(),
            'Total Owed To Rider (₵)': filtered['rider_gets'].sum(),
        }

        def format_currency_no_trailing(value):
            # Show comma separators, and drop decimals if .00
            if float(value).is_integer():
                return f"{int(value):,} ₵"
            else:
                return f"{value:,.2f} ₵"

        cols = st.columns(len(sums))
        for col, (name, value) in zip(cols, sums.items()):
            col.metric(label=name, value=format_currency_no_trailing(value))

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
