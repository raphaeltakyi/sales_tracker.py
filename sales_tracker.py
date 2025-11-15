import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# --- Initialize Supabase client ---
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# ================================
#           UI HEADER
# ================================
st.markdown(
    """
    <h1 style='text-align:center; color:#4B6EAF; font-weight:700;'>
        Daily Sales Tracker - Mannequins Ghana
    </h1>
    <p style='text-align:center; color:#6c757d;'>
        Built with Love from Kofi ❤️
    </p>
    <hr>
    """,
    unsafe_allow_html=True
)

PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]

# ================================
#        ADD NEW SALE
# ================================
with st.form("sale_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    date = col1.date_input("Date", datetime.now())
    location = col1.text_input("Location")
    cost = col2.number_input("Cost of Item (GHS)", min_value=0.0, format="%.2f")
    fee = col2.number_input("Delivery Fee (GHS)", min_value=0.0, format="%.2f")
    tip = col2.number_input("Tip (GHS)", min_value=0.0, format="%.2f")
    mode = col1.selectbox("Payment Mode", PAYMENT_CHOICES)
    submitted = st.form_submit_button("Add Sale")

if submitted:
    # Compute company vs rider earnings
    if mode == 'All to Company (MoMo/Bank)':
        company_gets, rider_gets = 0.0, fee + tip
    elif mode == 'All to Rider (Cash)':
        company_gets, rider_gets = cost, 0.0
    else:  # Split
        company_gets, rider_gets = 0.0, 0.0

    data = {
        "date": date.strftime("%Y-%m-%d"),
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

# ================================
#        RETRIEVE DATA
# ================================
response = supabase.table("sales").select("*").order("date", desc=True).execute()
df = pd.DataFrame(response.data or [])

if df.empty:
    st.info("No data yet. Add your first sale above.")
    st.stop()

# Ensure correct datatypes
df['date'] = pd.to_datetime(df['date'], errors='coerce')
num_cols = ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']
df[num_cols] = df[num_cols].apply(pd.to_numeric, errors='coerce')

# ================================
#        SIDEBAR FILTERS
# ================================
st.sidebar.header("Filters")
unique_dates = sorted(df['date'].dt.date.unique())

start_date, end_date = st.sidebar.select_slider(
    "Select Date Range",
    options=unique_dates,
    value=(unique_dates[0], unique_dates[-1])
)

locations = st.sidebar.multiselect("Locations", sorted(df['location'].unique()))
payment_modes = st.sidebar.multiselect("Payment Mode", PAYMENT_CHOICES)

mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
if locations:
    mask &= df['location'].isin(locations)
if payment_modes:
    mask &= df['payment_mode'].isin(payment_modes)

filtered = df[mask]

# ================================
#     DISPLAY FILTERED DATA
# ================================
st.subheader("Filtered Sales and Summary")

if filtered.empty:
    st.warning("No records for selected filters.")
else:
    display_df = filtered.copy()
    display_df['date'] = display_df['date'].dt.strftime("%a, %d/%m/%Y")
    display_df = display_df.rename(columns=lambda x: x.replace("_", " ").title())

    st.dataframe(display_df.reset_index(drop=True))

    # Summary Metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Delivery Fees", f"₵{filtered['delivery_fee'].sum():.2f}")
    col2.metric("Total Item Cost", f"₵{filtered['cost_of_item'].sum():.2f}")
    col3.metric("Total Tips", f"₵{filtered['tip'].sum():.2f}")
    col4.metric("Total To Company", f"₵{filtered['company_gets'].sum():.2f}")
    col5.metric("Total To Rider", f"₵{filtered['rider_gets'].sum():.2f}")

# ================================
#     EDIT / DELETE RECORDS
# ================================
st.subheader("Edit or Delete a Sale Record")
record_id = st.number_input("Enter Sale ID", min_value=1, step=1)
selected = df[df['id'] == record_id]

if selected.empty:
    st.info("Enter a valid Sale ID to edit or delete.")
else:
    row = selected.iloc[0]
    st.write("Selected Record:")
    st.dataframe(selected)

    # Editable fields
    new_loc = st.text_input("New Location", value=row['location'])
    new_cost = st.number_input("New Cost of Item", min_value=0.0, value=row['cost_of_item'])
    new_fee = st.number_input("New Delivery Fee", min_value=0.0, value=row['delivery_fee'])
    new_tip = st.number_input("New Tip", min_value=0.0, value=row['tip'])
    new_mode = st.selectbox("New Payment Mode", PAYMENT_CHOICES, index=PAYMENT_CHOICES.index(row['payment_mode']))

    # Recompute company/rider shares
    if new_mode == 'All to Company (MoMo/Bank)':
        company_gets, rider_gets = 0.0, new_fee + new_tip
    elif new_mode == 'All to Rider (Cash)':
        company_gets, rider_gets = new_cost, 0.0
    else:
        company_gets, rider_gets = 0.0, 0.0

    # Update action
    if st.button("Update Record"):
        update_data = {
            "location": new_loc,
            "cost_of_item": new_cost,
            "delivery_fee": new_fee,
            "tip": new_tip,
            "payment_mode": new_mode,
            "company_gets": company_gets,
            "rider_gets": rider_gets,
        }
        resp = supabase.table("sales").update(update_data).eq("id", record_id).execute()
        st.success("Updated!") if resp.data else st.error("Update failed.")
        st.rerun()

    # Delete action
    if st.button("Delete Record"):
        resp = supabase.table("sales").delete().eq("id", record_id).execute()
        st.success("Record deleted!") if resp.data else st.error("Delete failed.")
        st.rerun()
