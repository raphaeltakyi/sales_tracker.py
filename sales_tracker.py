import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# Streamlit page config for mobile view
st.set_page_config(page_title="Sales Tracker", layout="centered")

# Optional: Add a logo (if available)
# st.image("logo.png", width=120)

# Initialize Supabase client
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title('Daily Sales Tracker - Mannequins Ghana')

# Helpful tip on mobile
st.caption("Tip: You can scroll tables left/right on mobile. For best use, save this app to your home screen!")

PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]

# --- Add a sale form (single-column for mobile clarity) ---
with st.form("sale_form", clear_on_submit=True):
    date = st.date_input("Date", datetime.now())
    location = st.text_input("Location")
    cost = st.number_input("Cost of Item", min_value=0.0, format='%.2f')
    fee = st.number_input("Delivery Fee", min_value=0.0, format='%.2f')
    tip = st.number_input("Tip", min_value=0.0, format='%.2f')
    mode = st.selectbox("Payment Mode", PAYMENT_CHOICES)
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
    if response.data:
        st.success("Sale added!")
    else:
        st.error("Failed to add sale.")
        st.write(response)

# --- Fetch all sales ---
response = supabase.table("sales").select("*").order("date", desc=True).execute()
df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

if df.empty:
    st.info('No data yet. Add your first sale above.')
else:
    st.header('🔎 Filter Sales')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for col in ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    # Place filters at top (not sidebar) for mobile
    unique_dates = sorted(df['date'].dt.date.dropna().unique())
    filter_date = st.selectbox('Filter by date', unique_dates)
    locations = st.multiselect('Locations', sorted(df['location'].dropna().unique()), default=None)
    payment_modes = st.multiselect('Payment Mode', PAYMENT_CHOICES, default=None)
    mask = (df['date'].dt.date == filter_date)
    if locations:
        mask &= df['location'].isin(locations)
    if payment_modes:
        mask &= df['payment_mode'].isin(payment_modes)
    filtered = df[mask]

    filtered_display = filtered.copy()
    if not filtered_display.empty:
        filtered_display['date'] = filtered_display['date'].dt.strftime('%a, %d/%m/%Y')
        filtered_display = filtered_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
        st.subheader('Sales for ' + filter_date.strftime('%d %b %Y'))
        st.dataframe(filtered_display.reset_index(drop=True), use_container_width=True)

        st.subheader('Summary')
        c1, c2, c3 = st.columns(3)
        c1.metric('Total Fees', f"₵{filtered['delivery_fee'].sum():.2f}")
        c2.metric('Total Item', f"₵{filtered['cost_of_item'].sum():.2f}")
        c3.metric('Total Tips', f"₵{filtered['tip'].sum():.2f}")
        cc1, cc2 = st.columns(2)
        cc1.metric('Owed Company', f"₵{filtered['company_gets'].sum():.2f}")
        cc2.metric('Owed Rider', f"₵{filtered['rider_gets'].sum():.2f}")
    else:
        st.warning("No records for selected filter combination.")

    # --- Edit/delete section (optional: place in expander on mobile) ---
    with st.expander("Edit or Delete a Sale Record"):
        selected_id = st.number_input("Enter Sale ID to Edit/Delete", min_value=1, step=1)
        edit_row = filtered[filtered['id'] == selected_id]
        if not edit_row.empty:
            st.write("Selected Record:")
            edit_row_display = edit_row.copy()
            edit_row_display['date'] = edit_row_display['date'].dt.strftime('%a, %d/%m/%Y')
            st.dataframe(edit_row_display)
            new_loc = st.text_input("New Location", value=str(edit_row['location'].values[0]), key='edit_loc')
            new_cost = st.number_input("New Cost of Item", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', key='edit_cost')
            new_fee = st.number_input("New Delivery Fee", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', key='edit_fee')
            new_tip = st.number_input("New Tip", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', key='edit_tip')
            selected_mode = edit_row['payment_mode'].values[0]
            default_index = PAYMENT_CHOICES.index(selected_mode) if selected_mode in PAYMENT_CHOICES else 0
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
