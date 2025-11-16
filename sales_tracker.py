import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client

# --- Helper Functions ---
def calculate_payouts(mode, cost, fee, tip):
    if mode == 'All to Company (MoMo/Bank)':
        return 0.0, fee + tip
    elif mode == 'All to Rider (Cash)':
        return cost, 0.0
    elif mode == 'Split: Item to Company, Delivery+Tip to Rider':
        return 0.0, 0.0
    return 0.0, 0.0

def styled_section_header(title, color1="667eea", color2="764ba2"):
    return f"""
    <div style='background: linear-gradient(135deg, #{color1} 0%, #{color2} 100%);
                padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>
        <h3 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
            {title}
        </h3>
    </div>
    """

# --- Set page config ---
st.set_page_config(
    page_title="Daily Sales Tracker - Mannequins Ghana",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown(
    """
    <style>
    .main { padding-top: 0rem; }
    .block-container { padding: 1rem 1rem 0rem 1rem; max-width: 100%; }
    h1, h2, h3 { margin-top: 0.5rem; margin-bottom: 0.5rem; }
    [data-testid="stDataFrame"] { height: auto; }
    .streamlit-expanderHeader { padding: 0.5rem 0rem; }
    .stMarkdown { margin-bottom: 0.5rem; }
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div > div {
        border-radius: 8px !important;
        border: 2px solid #e0e0e0 !important;
        padding: 0.75rem !important;
        font-size: 1rem !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border: 2px solid #667eea !important;
        box-shadow: 0 0 10px rgba(102, 126, 234, 0.2) !important;
    }
    .stTextInput > label,
    .stNumberInput > label,
    .stSelectbox > label,
    .stDateInput > label {
        font-weight: 600 !important;
        color: #4B6EAF !important;
        font-size: 0.95rem !important;
    }
    .metric-container {
        display: flex;
        gap: 10px;
        margin-bottom: 10px;
    }
    .metric-card {
        flex: 1;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 8px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-card:nth-child(2) { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);}
    .metric-card:nth-child(3) { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);}
    .metric-card:nth-child(4) { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);}
    .metric-card:nth-child(5) { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);}
    .metric-label {
        font-size: 0.85rem;
        opacity: 0.9;
        margin-bottom: 0.5rem;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Supabase client ---
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- Title & subtitle ---
st.markdown(
    """
    <h1 style='text-align:center; color:#4B6EAF; font-weight:700; font-family: Arial, sans-serif; margin-top: 0;'>
        Daily Sales Tracker - Mannequins Ghana
    </h1>
    <p style='text-align:center; font-size:1rem; color:#6c757d; font-family: Arial, sans-serif; margin-bottom: 1.5rem;'>
        Built with Love from Kofi ❤️
    </p>
    """, 
    unsafe_allow_html=True
)

PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]

# --- Sale form ---
st.markdown(styled_section_header("➕ Add New Sale"), unsafe_allow_html=True)
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
    col_btn1, col_btn2, col_btn3 = st.columns([1,2,1])
    with col_btn2:
        submitted = st.form_submit_button("✅ Add Sale", use_container_width=True, type="primary")

if submitted:
    company_gets, rider_gets = calculate_payouts(mode, cost, fee, tip)
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
        st.write(response)

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

    all_locations = sorted(df['location'].dropna().unique())
    locations = st.sidebar.multiselect('Locations', all_locations, default=all_locations)
    payment_modes = st.sidebar.multiselect('Payment Mode', PAYMENT_CHOICES, default=PAYMENT_CHOICES)

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
        st.markdown(styled_section_header("📊 Filtered Sales Records"), unsafe_allow_html=True)
        with st.expander("View Table", expanded=True):
            st.dataframe(filtered_display.reset_index(drop=True), use_container_width=True, height=300)
        st.markdown(styled_section_header("💹 Summary Statistics", color1="f093fb", color2="f5576c"), unsafe_allow_html=True)
        sum_cols = ['delivery_fee', 'cost_of_item', 'tip', 'company_gets', 'rider_gets']
        labels = ['🚚 Delivery Fees', '💰 Item Cost', '💵 Tips', '🏢 Company', '🚴 Rider']
        col_sum = st.columns(5)
        for idx, (col, label) in enumerate(zip(sum_cols, labels)):
            with col_sum[idx]:
                st.markdown(
                    f"""
                    <div class='metric-card'>
                        <div class='metric-label'>{label}</div>
                        <div class='metric-value'>₵{filtered[col].sum():.2f}</div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
    else:
        st.warning("⚠️ No records for selected filter combination.")

    st.markdown(styled_section_header("🔧 Manage Records"), unsafe_allow_html=True)
    with st.expander("📝 Edit or Delete a Sale Record", expanded=False):
        selected_id = st.number_input("🔍 Enter Sale ID", min_value=1, step=1, key='select_id', help="Enter the ID of the record you want to edit or delete")
        edit_row = filtered[filtered['id'] == selected_id]
        if not edit_row.empty:
            st.markdown("#### 📄 Selected Record")
            edit_row_display = edit_row.copy()
            edit_row_display['date'] = edit_row_display['date'].dt.strftime('%a, %d/%m/%Y')
            edit_row_display = edit_row_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
            st.dataframe(edit_row_display, use_container_width=True)
            st.markdown("---")
            st.markdown("#### ✏️ Edit Record Details")
            edit_col1, edit_col2 = st.columns(2)
            with edit_col1:
                new_loc = st.text_input("📍 Location", value=str(edit_row['location'].values[0]), key=f'edit_loc_{selected_id}')
                new_cost = st.number_input("💰 Cost of Item", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', key=f'edit_cost_{selected_id}')
                new_fee = st.number_input("🚚 Delivery Fee", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', key=f'edit_fee_{selected_id}')
            with edit_col2:
                new_tip = st.number_input("💵 Tip", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', key=f'edit_tip_{selected_id}')
                selected_mode = edit_row['payment_mode'].values[0]
                default_index = PAYMENT_CHOICES.index(selected_mode) if selected_mode in PAYMENT_CHOICES else 0
                new_mode = st.selectbox("💳 Payment Mode", PAYMENT_CHOICES, index=default_index, key=f'edit_mode_{selected_id}')
            company_gets, rider_gets = calculate_payouts(new_mode, new_cost, new_fee, new_tip)
            st.markdown("---")
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
            with btn_col1:
                if st.button("✅ Update Record", type="primary", use_container_width=True):
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
                        st.success("✅ Record updated successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to update record.")
                        st.write(response)
            with btn_col2:
                if st.button("🗑️ Delete Record", type="secondary", use_container_width=True):
                    response = supabase.table("sales").delete().eq("id", int(selected_id)).execute()
                    if response.data:
                        st.success("🗑️ Record deleted successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to delete record.")
                        st.write(response)
        else:
            st.info("ℹ️ Please enter a valid Sale ID from the filtered records above to edit or delete.")
