import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# --- Configure page layout ---
st.set_page_config(
    page_title="Daily Sales Tracker - Mannequins Ghana",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS to maximize vertical footprint ---
st.markdown(
    """
    <style>
    .main { padding-top: 0rem; }
    .block-container { padding-top: 1rem; padding-bottom: 0rem; padding-left: 1rem; padding-right: 1rem; max-width: 100%; }
    h1, h2, h3, h4, h5 { margin-top: 0.3rem; margin-bottom: 0.3rem; }
    [data-testid="stDataFrame"] { height: auto; }
    .streamlit-expanderHeader { padding: 0.5rem 0rem; }
    .stMarkdown { margin-bottom: 0.5rem; }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div {
        border-radius: 8px !important;
        border: 2px solid #e0e0e0 !important;
        padding: 0.55rem !important;
        font-size: 0.98rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border: 2px solid #667eea !important;
        box-shadow: 0 0 10px rgba(102, 126, 234, 0.17) !important;
    }
    .stTextInput > label,
    .stNumberInput > label,
    .stSelectbox > label,
    .stDateInput > label {
        font-weight: 600 !important;
        color: #4B6EAF !important;
        font-size: 0.92rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Initialize Supabase client
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

# --- Title and subtitle ---
st.markdown(
    """
    <h1 style='text-align:center; color:#4B6EAF; font-weight:700; font-family: Arial, sans-serif; margin-top: 0;'>
        Daily Sales Tracker - Mannequins Ghana
    </h1>
    <p style='text-align:center; font-size:1rem; color:#6c757d; font-family: Arial, sans-serif; margin-bottom: 1.2rem;'>
        Built with Love from Kofi ❤️
    </p>
    """, 
    unsafe_allow_html=True,
)

PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]

# --- Add a sale form with compact styling ---
st.markdown(
    """
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 0.6rem; border-radius: 8px; margin-bottom: 1rem;'>
        <h4 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
            ➕ Add New Sale
        </h4>
    </div>
    """,
    unsafe_allow_html=True
)

with st.form("sale_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("📅 Date", datetime.now())
        location = st.text_input("📍 Location", placeholder="Enter location")
        mode = st.selectbox("💳 Payment Mode", PAYMENT_CHOICES)
    with col2:
        cost = st.number_input("💰 Cost of Item", min_value=0.0, format='%.2f', step=0.01)
        fee = st.number_input("🚚 Delivery Fee", min_value=0.0, format='%.2f', step=0.01)
        tip = st.number_input("💵 Tip", min_value=0.0, format='%.2f', step=0.01)
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        submitted = st.form_submit_button("✅ Add Sale", use_container_width=True, type="primary")

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
        st.success("✅ Sale added successfully!")
    else:
        st.error("❌ Failed to add sale.")
        st.write(response)  # Optional for debugging

# --- Fetch all sales ---
response = supabase.table("sales").select("*").order("date", desc=True).execute()
df = pd.DataFrame(response.data) if response.data else pd.DataFrame()

if df.empty:
    st.info('📭 No data yet. Add your first sale above.')
else:
    st.sidebar.header('🔍 Filter')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for col in ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    unique_dates = sorted(df['date'].dt.date.dropna().unique())
    if unique_dates:
        start_date, end_date = st.sidebar.select_slider(
            'Select Date Range',
            options=unique_dates,
            value=(unique_dates[0], unique_dates[-1])
        )
    else:
        start_date, end_date = None, None

    locations = st.sidebar.multiselect('Locations', sorted(df['location'].dropna().unique()), default=None)
    payment_modes = st.sidebar.multiselect('Payment Mode', PAYMENT_CHOICES, default=None)

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
        
        st.markdown(
            """
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 0.6rem; border-radius: 8px; margin: 0.7rem 0;'>
                <h4 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
                    📊 Filtered Sales Records
                </h4>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.expander("View Table", expanded=True):
            st.dataframe(filtered_display.reset_index(drop=True), use_container_width=True, height=230)

        # ---- Compact Summary Statistics Section ----
        st.markdown(
            """
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        padding: 0.5rem; border-radius: 7px; margin: 0.5rem 0;'>
                <h4 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center; font-size:1.05rem;'>
                    💹 Summary Statistics
                </h4>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            """
            <style>
            .metric-row { display: flex; gap: 6px; margin-bottom: 2px; }
            .metric-card {
                flex: 1;
                background: linear-gradient(135deg, #f5f6fa 0%, #e1e8ed 100%);
                padding: 0.6rem 0.2rem;
                border-radius: 6px;
                color: #5A5A5A;
                text-align: center;
                font-size: 1.02rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.03);
                min-width: 0;
            }
            .metric-label { font-size: 0.80rem; font-weight: 500; margin-bottom: 0.35rem; opacity: 0.8; }
            .metric-value { font-size: 1.07rem; font-weight: 650; }
            </style>
            <div class="metric-row">
            """,
            unsafe_allow_html=True
        )
        st.markdown(
            f"""
            <div class='metric-card'>
                <div class='metric-label'>🚚 Delivery</div>
                <div class='metric-value'>₵{filtered['delivery_fee'].sum():,.2f}</div>
            </div>
            <div class='metric-card'>
                <div class='metric-label'>💰 Item</div>
                <div class='metric-value'>₵{filtered['cost_of_item'].sum():,.2f}</div>
            </div>
            <div class='metric-card'>
                <div class='metric-label'>💵 Tip</div>
                <div class='metric-value'>₵{filtered['tip'].sum():,.2f}</div>
            </div>
            <div class='metric-card'>
                <div class='metric-label'>🏢 Company</div>
                <div class='metric-value'>₵{filtered['company_gets'].sum():,.2f}</div>
            </div>
            <div class='metric-card'>
                <div class='metric-label'>🚴 Rider</div>
                <div class='metric-value'>₵{filtered['rider_gets'].sum():,.2f}</div>
            </div>
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.warning("⚠️ No records for selected filter combination.")

    # ---- Compact Manage Records Section ----
    with st.expander("🔧 Manage Records", expanded=False):
        st.markdown(
            """
            <h5 style='color:#4B6EAF;margin-top:-0.7rem;font-family:Arial,sans-serif'>Edit or Delete Sale</h5>
            <style>
            .stNumberInput > label, .stTextInput > label, .stSelectbox > label {
                font-weight: 500;
                color: #4B6EAF;
                font-size: 0.97rem;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        selected_id = st.number_input("🔍 Sale ID", min_value=1, step=1, key='select_id', help="Enter ID to edit or delete")
        edit_row = filtered[filtered['id'] == selected_id]
        if not edit_row.empty:
            st.markdown("**Selected Record:**")
            edit_row_display = edit_row.copy()
            edit_row_display['date'] = edit_row_display['date'].dt.strftime('%a, %d/%m/%Y')
            edit_row_display = edit_row_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
            st.dataframe(edit_row_display, use_container_width=True)
            edit_col1, edit_col2 = st.columns(2)
            with edit_col1:
                new_loc = st.text_input("📍 Location", value=str(edit_row['location'].values[0]), key=f'edit_loc_{selected_id}')
                new_cost = st.number_input("💰 Item", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', key=f'edit_cost_{selected_id}')
                new_fee = st.number_input("🚚 Delivery", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', key=f'edit_fee_{selected_id}')
            with edit_col2:
                new_tip = st.number_input("💵 Tip", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', key=f'edit_tip_{selected_id}')
                selected_mode = edit_row['payment_mode'].values[0]
                default_index = PAYMENT_CHOICES.index(selected_mode) if selected_mode in PAYMENT_CHOICES else 0
                new_mode = st.selectbox("💳 Payment", PAYMENT_CHOICES, index=default_index, key=f'edit_mode_{selected_id}')
            # Calculate based on payment mode
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
            colA, colB, colC = st.columns([1, 1, 3])
            with colA:
                if st.button("✅ Update", type="primary", use_container_width=True):
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
                        st.success("✅ Updated!")
                        st.rerun()
                    else:
                        st.error("❌ Error.")
                        st.write(response)
            with colB:
                if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                    response = supabase.table("sales").delete().eq("id", int(selected_id)).execute()
                    if response.data:
                        st.success("🗑️ Deleted!")
                        st.rerun()
                    else:
                        st.error("❌ Error.")
                        st.write(response)
        else:
            st.info("ℹ️ Enter a valid Sale ID above.")
