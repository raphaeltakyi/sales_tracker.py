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

# --- Custom CSS (now inline, no external file needed) ---
st.markdown(
    """
    <style>
    /* ... previous CSS ... (keep as before) ... */

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
    .metric-card:nth-child(2) {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    }
    .metric-card:nth-child(3) {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
    }
    .metric-card:nth-child(4) {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
    }
    .metric-card:nth-child(5) {
        background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
    }
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

# --- Constants & Helper Functions ---
PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]
def compute_shares(mode, cost, fee, tip):
    if mode == PAYMENT_CHOICES[0]:
        return 0.0, fee + tip
    if mode == PAYMENT_CHOICES[1]:
        return cost, 0.0
    if mode == PAYMENT_CHOICES[2]:
        return 0.0, 0.0
    return 0.0, 0.0
def style_card(label, value, emoji=""):
    return f"""
        <div class='metric-card'>
            <div class='metric-label'>{emoji} {label}</div>
            <div class='metric-value'>₵{value:.2f}</div>
        </div>
    """
def get_filtered(df, start_date, end_date, locs, pmodes):
    mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    if locs: mask &= df['location'].isin(locs)
    if pmodes: mask &= df['payment_mode'].isin(pmodes)
    return df[mask]

# --- Initialize Supabase client ---
supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

# --- Title and subtitle
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

# --- Add a sale form ---
with st.form("sale_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("📅 Date", datetime.now())
        location = st.text_input("📍 Location", placeholder="Enter location")
        mode = st.selectbox("💳 Payment Mode", PAYMENT_CHOICES)
    with col2:
        cost = st.number_input("💰 Cost of Item", min_value=0.0, format='%.2f')
        fee = st.number_input("🚚 Delivery Fee", min_value=0.0, format='%.2f')
        tip = st.number_input("💵 Tip", min_value=0.0, format='%.2f')
    submitted = st.form_submit_button("✅ Add Sale", use_container_width=True)

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
    st.success("✅ Sale added successfully!") if response.data else st.error("❌ Failed to add sale.")

# --- Fetch and Parse Sales Data ---
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
    start_date, end_date = st.sidebar.select_slider(
        'Select Date Range',
        options=unique_dates,
        value=(unique_dates[0], unique_dates[-1])
    ) if unique_dates else (None, None)
    locations = st.sidebar.multiselect('Locations', sorted(df['location'].dropna().unique()), default=None)
    payment_modes = st.sidebar.multiselect('Payment Mode', PAYMENT_CHOICES, default=None)
    filtered = get_filtered(df, start_date, end_date, locations, payment_modes) if start_date and end_date else pd.DataFrame()
    filtered_display = filtered.copy()
    if not filtered_display.empty:
        filtered_display['date'] = filtered_display['date'].dt.strftime('%a, %d/%m/%Y')
        filtered_display = filtered_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
        st.markdown("<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);padding: 1rem; border-radius: 10px;' ><h3 style='color: white;text-align: center;'>📊 Filtered Sales Records</h3></div>", unsafe_allow_html=True)
        with st.expander("View Table", expanded=True):
            st.dataframe(filtered_display.reset_index(drop=True), use_container_width=True, height=300)
        # Summary Statistics
        st.markdown("<div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);padding: 1rem; border-radius: 10px;'><h3 style='color: white;text-align: center;'>💹 Summary Statistics</h3></div>", unsafe_allow_html=True)
        col_sum = st.columns(5)
        metrics = [
            ("Delivery Fees", filtered['delivery_fee'].sum(), "🚚"),
            ("Item Cost", filtered['cost_of_item'].sum(), "💰"),
            ("Tips", filtered['tip'].sum(), "💵"),
            ("Company", filtered['company_gets'].sum(), "🏢"),
            ("Rider", filtered['rider_gets'].sum(), "🚴"),
        ]
        for idx, (label, val, emoji) in enumerate(metrics):
            with col_sum[idx]:
                st.markdown(style_card(label, val, emoji), unsafe_allow_html=True)
    else:
        st.warning("⚠️ No records for selected filter combination.")

    # --- Edit/Delete section ---
    st.markdown("<div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);padding: 1rem; border-radius: 10px;'><h3 style='color: white;text-align: center;'>🔧 Manage Records</h3></div>", unsafe_allow_html=True)
    with st.expander("📝 Edit or Delete a Sale Record"):
        selected_id = st.number_input("🔍 Enter Sale ID", min_value=1, step=1, key='select_id')
        edit_row = filtered[filtered['id'] == selected_id]
        if not edit_row.empty:
            st.markdown("#### 📄 Selected Record")
            edit_row_display = edit_row.copy()
            edit_row_display['date'] = edit_row_display['date'].dt.strftime('%a, %d/%m/%Y')
            edit_row_display = edit_row_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
            st.dataframe(edit_row_display, use_container_width=True)
            st.markdown("---\n#### ✏️ Edit Record Details")
            edit_col1, edit_col2 = st.columns(2)
            with edit_col1:
                new_loc = st.text_input("📍 Location", value=str(edit_row['location'].values[0]), key=f'edit_loc_{selected_id}')
                new_cost = st.number_input("💰 Cost of Item", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', key=f'edit_cost_{selected_id}')
                new_fee = st.number_input("🚚 Delivery Fee", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', key=f'edit_fee_{selected_id}')
            with edit_col2:
                new_tip = st.number_input("💵 Tip", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', key=f'edit_tip_{selected_id}')
                selected_mode = edit_row['payment_mode'].values[0]
                new_mode_idx = PAYMENT_CHOICES.index(selected_mode) if selected_mode in PAYMENT_CHOICES else 0
                new_mode = st.selectbox("💳 Payment Mode", PAYMENT_CHOICES, index=new_mode_idx, key=f'edit_mode_{selected_id}')
            company_gets, rider_gets = compute_shares(new_mode, new_cost, new_fee, new_tip)
            st.markdown("---")
            btn_col1, btn_col2, _ = st.columns([1, 1, 2])
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
                    if response.data: st.success("✅ Record updated successfully!"); st.rerun()
                    else: st.error("❌ Failed to update record."); st.write(response)
            with btn_col2:
                if st.button("🗑️ Delete Record", type="secondary", use_container_width=True):
                    response = supabase.table("sales").delete().eq("id", int(selected_id)).execute()
                    if response.data: st.success("🗑️ Record deleted successfully!"); st.rerun()
                    else: st.error("❌ Failed to delete record."); st.write(response)
        else:
            st.info("ℹ️ Please enter a valid Sale ID from the filtered records above to edit or delete.")
