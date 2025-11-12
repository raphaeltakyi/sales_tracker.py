import streamlit as st
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client

# --- Utility: guaranteed Python date conversion
def to_py_date(x):
    if isinstance(x, date):
        return x
    elif pd.isnull(x):
        return None
    elif isinstance(x, pd.Timestamp):
        return x.date()
    elif isinstance(x, str):
        try:
            return pd.to_datetime(x, errors='coerce').date()
        except:
            return None
    return None

# Initialize Supabase client
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title('Daily Sales Tracker - Mannequins Ghana')
st.markdown('<br>', unsafe_allow_html=True)

PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]

# --- Add a sale form ---
with st.form("sale_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    date_val = col1.date_input("Date", datetime.now())
    location = col1.text_input("Location")
    cost = col2.number_input("Cost of Item", min_value=0.0, format='%.2f')
    fee = col2.number_input("Delivery Fee", min_value=0.0, format='%.2f')
    tip = col2.number_input("Tip", min_value=0.0, format='%.2f')
    mode = col1.selectbox("Payment Mode", PAYMENT_CHOICES)
    submitted = st.form_submit_button("Add Sale")

if submitted:
    if mode == 'All to Company (MoMo/Bank)':
        company_gets = 0.0
        rider_gets = fee + tip
    elif mode == 'All to Rider (Cash)':
        company_gets = cost
        rider_gets = 0.0
    elif mode == 'Split: Item to Company, Delivery+Tip to Rider':
        company_gets = 0.0
        rider_gets = 0.0
    else:
        company_gets = 0.0
        rider_gets = 0.0

    data = {
        "date": date_val.strftime('%Y-%m-%d'),
        "location": location,
        "cost_of_item": cost,
        "delivery_fee": fee,
        "tip": tip,
        "payment_mode": mode,
        "company_gets": company_gets,
        "rider_gets": rider_gets
    }
    response = supabase.table("sales").insert(data).execute()

    if response.data:
        st.success("Sale added!")
    else:
        st.error("Failed to add sale.")
        st.write(response)  # For debugging

# --- Fetch all sales ---
response = supabase.table("sales").select("*").order("date", desc=True).execute()
df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

if df.empty:
    st.info('No data yet. Add your first sale above.')
else:
    st.sidebar.header('Filter')
    # Parse 'date' as datetime and force all to date object
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    # Prevent non-numeric values in number columns
    for col in ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # --- Date range filter using only dates present in data, strictly ordered ---
    all_dates = [to_py_date(x) for x in df['date'].dropna()]
    unique_dates = sorted({d for d in all_dates if d is not None}, key=lambda x: (x.year, x.month, x.day))
    # Debug: check both order and types
    st.sidebar.write("Dates for slider:", unique_dates)
    st.sidebar.write([type(d) for d in unique_dates])

    if unique_dates:
        start_date, end_date = st.sidebar.select_slider(
            'Select Date Range',
            options=unique_dates,
            value=(unique_dates[0], unique_dates[-1]),
            format_func=lambda d: d.strftime('%a, %d/%m/%Y')
        )
    else:
        start_date, end_date = None, None

    # Other filters
    locations = st.sidebar.multiselect('Locations', sorted(df['location'].dropna().unique()), default=None)
    payment_modes = st.sidebar.multiselect('Payment Mode', PAYMENT_CHOICES, default=None)

    # Filtering logic
    if start_date and end_date:
        mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
        if locations:
            mask &= df['location'].isin(locations)
        if payment_modes:
            mask &= df['payment_mode'].isin(payment_modes)
        filtered = df[mask]
    else:
        filtered = pd.DataFrame()

    filtered_display = filtered.copy()
    if not filtered_display.empty:
        filtered_display['date'] = filtered_display['date'].dt.strftime('%a, %d/%m/%Y')
        filtered_display = filtered_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
        st.subheader('Filtered Sales and Summary')
        st.dataframe(filtered_display.reset_index(drop=True))

        st.subheader('Summary Statistics')
        col_sum1, col_sum2, col_sum3, col_sum4, col_sum5 = st.columns(5)
        col_sum1.metric('Total Delivery Fees', f"₵{filtered['delivery_fee'].sum():.2f}")
        col_sum2.metric('Total Item Cost', f"₵{filtered['cost_of_item'].sum():.2f}")
        col_sum3.metric('Total Tips', f"₵{filtered['tip'].sum():.2f}")
        col_sum4.metric('Total Owed To Company', f"₵{filtered['company_gets'].sum():.2f}")
        col_sum5.metric('Total Owed To Rider', f"₵{filtered['rider_gets'].sum():.2f}")
    else:
        st.warning("No records for selected filter combination.")

    # --- Edit/delete section ---
    st.subheader("Edit or Delete a Sale Record")
    selected_id = st.number_input("Enter Sale ID to Edit/Delete", min_value=1, step=1)
    edit_row = filtered[filtered['id'] == selected_id]
    if not edit_row.empty:
        st.write("Selected Record:")
        edit_row_display = edit_row.copy()
        edit_row_display['date'] = edit_row_display['date'].dt.strftime('%a, %d/%m/%Y')
        edit_row_display = edit_row_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
        st.dataframe(edit_row_display)

        new_loc = st.text_input("New Location", value=str(edit_row['location'].values[0]), key='edit_loc')
        new_cost = st.number_input("New Cost of Item", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', key='edit_cost')
        new_fee = st.number_input("New Delivery Fee", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', key='edit_fee')
        new_tip = st.number_input("New Tip", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', key='edit_tip')
        selected_mode = edit_row['payment_mode'].values[0]
        if selected_mode in PAYMENT_CHOICES:
            default_index = PAYMENT_CHOICES.index(selected_mode)
        else:
            default_index = 0
        new_mode = st.selectbox("New Payment Mode", PAYMENT_CHOICES, index=default_index, key='edit_mode')

        if new_mode == 'All to Company (MoMo/Bank)':
            company_gets = 0.0
            rider_gets = new_fee + new_tip
        elif new_mode == 'All to Rider (Cash)':
            company_gets = new_cost
            rider_gets = 0.0
        elif new_mode == 'Split: Item to Company, Delivery+Tip to Rider':
            company_gets = 0.0
            rider_gets = 0.0
        else:
            company_gets = 0.0
            rider_gets = 0.0

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
            if response.data:
                st.success("Record updated!")
                st.rerun()
            else:
                st.error("Failed to update record.")
                st.write(response)

        if st.button("Delete Record"):
            response = supabase.table("sales").delete().eq("id", int(selected_id)).execute()
            if response.data:
                st.success("Record deleted!")
                st.rerun()
            else:
                st.error("Failed to delete record.")
                st.write(response)
    else:
        st.info("Enter a valid Sale ID to edit or delete.")
