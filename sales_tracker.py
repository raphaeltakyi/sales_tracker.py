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
    
    .summary-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 0.3rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    
    .summary-header h3 {
        color: white;
        margin: 0;
        font-family: Arial, sans-serif;
        text-align: center;
    }
    
    .summary-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .summary-card {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1.2rem;
        border-radius: 6px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .summary-card.prince {
        border-left-color: #667eea;
    }
    
    .summary-card.justice {
        border-left-color: #764ba2;
    }
    
    .summary-card.company {
        border-left-color: #43e97b;
    }
    
    .summary-label {
        font-size: 0.85rem;
        color: #666;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    
    .summary-value {
        font-size: 1.6rem;
        font-weight: 700;
        color: #333;
    }
    
    .summary-meta {
        font-size: 0.75rem;
        color: #999;
        margin-top: 0.5rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# Initialize Supabase client
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)


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
    unsafe_allow_html=True,
)


PAYMENT_CHOICES = [
    '1. All to Company (MoMo/Bank)',
    '2. All to Rider - Prince (Cash)',
    '3. All to Rider - Justice (Cash)',
    '4. Split: Item to Company, Delivery+Tip to Rider - Prince',
    '5. Split: Item to Company, Delivery+Tip to Rider - Justice'
]


def calculate_payment_split(mode, cost, fee, tip):
    """
    Calculate how much company, Prince, and Justice get based on payment mode.
    
    Returns: (company_gets, prince_gets, justice_gets)
    
    1. All to Company: Company gets (cost + fee + tip)
    2. All to Rider - Prince: Prince gets (cost + fee + tip)
    3. All to Rider - Justice: Justice gets (cost + fee + tip)
    4. Split (Prince): Company gets cost, Prince gets (fee + tip)
    5. Split (Justice): Company gets cost, Justice gets (fee + tip)
    """
    if mode == '1. All to Company (MoMo/Bank)':
        return cost + fee + tip, 0.0, 0.0
    elif mode == '2. All to Rider - Prince (Cash)':
        return 0.0, cost + fee + tip, 0.0
    elif mode == '3. All to Rider - Justice (Cash)':
        return 0.0, 0.0, cost + fee + tip
    elif mode == '4. Split: Item to Company, Delivery+Tip to Rider - Prince':
        return cost, fee + tip, 0.0
    elif mode == '5. Split: Item to Company, Delivery+Tip to Rider - Justice':
        return cost, 0.0, fee + tip
    else:
        return 0.0, 0.0, 0.0


# --- Add a sale form with modern styling ---
st.markdown(
    """
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 0.5rem; border-radius: 10px; margin-bottom: 1rem;'>
        <h3 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
            ➕ Add New Sale
        </h3>
    </div>
    """,
    unsafe_allow_html=True
)


with st.form("sale_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            date = st.date_input("📅 Date", datetime.now())
            location = st.text_input("📍 Location", placeholder="Enter location")
            mode = st.selectbox("💳 Payment Mode", PAYMENT_CHOICES)
    with col2:
        with st.container(border=True):
            cost = st.number_input("💰 Cost of Item", min_value=0.0, format='%.2f', step=0.01)
            fee = st.number_input("🚚 Delivery Fee", min_value=0.0, format='%.2f', step=0.01)
            tip = st.number_input("💵 Tip", min_value=0.0, format='%.2f', step=0.01)
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        submitted = st.form_submit_button("✅ Add Sale", use_container_width=True, type="primary")


if submitted:
    company_gets, prince_gets, justice_gets = calculate_payment_split(mode, cost, fee, tip)

    data = {
        "date": date.strftime('%Y-%m-%d'),
        "location": location,
        "cost_of_item": cost,
        "delivery_fee": fee,
        "tip": tip,
        "payment_mode": mode,
        "company_gets": company_gets,
        "prince_gets": prince_gets,
        "justice_gets": justice_gets
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
    for col in ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'prince_gets', 'justice_gets']:
        if col in df.columns:
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
                        padding: 0.3rem; border-radius: 10px; margin: 1rem 0;'>
                <h3 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
                    📊 Filtered Sales Records
                </h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        with st.expander("View Table", expanded=True):
            st.dataframe(filtered_display.reset_index(drop=True), use_container_width=True, height=300)


        # ---- Compact Summary Section ----
        st.markdown('<div class="summary-header"><h3>💰 Settlement Summary</h3></div>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(
                f"""
                <div class="summary-card company">
                    <div class="summary-label">🏢 Company</div>
                    <div class="summary-value">₵{filtered['company_gets'].sum():,.2f}</div>
                    <div class="summary-meta">{len(filtered[filtered['company_gets'] > 0])} transactions</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""
                <div class="summary-card prince">
                    <div class="summary-label">👤 Prince</div>
                    <div class="summary-value">₵{filtered['prince_gets'].sum():,.2f}</div>
                    <div class="summary-meta">{len(filtered[filtered['prince_gets'] > 0])} deliveries</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col3:
            st.markdown(
                f"""
                <div class="summary-card justice">
                    <div class="summary-label">👤 Justice</div>
                    <div class="summary-value">₵{filtered['justice_gets'].sum():,.2f}</div>
                    <div class="summary-meta">{len(filtered[filtered['justice_gets'] > 0])} deliveries</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    else:
        st.warning("⚠️ No records for selected filter combination.")


    # --- Edit/delete section with modern styling ---
    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                    padding: 0.3rem; border-radius: 10px; margin: 1rem 0;'>
            <h3 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
                🔧 Manage Records
            </h3>
        </div>
        """,
        unsafe_allow_html=True
    )
    with st.expander("📝 Edit or Delete a Sale Record", expanded=False):
        st.markdown(
            """
            <style>
            .stNumberInput > label, .stTextInput > label, .stSelectbox > label {
                font-weight: 600;
                color: #4B6EAF;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
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
                st.markdown("<div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px;'>", unsafe_allow_html=True)
                new_loc = st.text_input("📍 Location", value=str(edit_row['location'].values[0]), key=f'edit_loc_{selected_id}')
                new_cost = st.number_input("💰 Cost of Item", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', key=f'edit_cost_{selected_id}')
                new_fee = st.number_input("🚚 Delivery Fee", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', key=f'edit_fee_{selected_id}')
                st.markdown("</div>", unsafe_allow_html=True)
            with edit_col2:
                st.markdown("<div style='background-color: #f8f9fa; padding: 1rem; border-radius: 8px;'>", unsafe_allow_html=True)
                new_tip = st.number_input("💵 Tip", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', key=f'edit_tip_{selected_id}')
                selected_mode = edit_row['payment_mode'].values[0]
                if selected_mode in PAYMENT_CHOICES:
                    default_index = PAYMENT_CHOICES.index(selected_mode)
                else:
                    default_index = 0
                new_mode = st.selectbox("💳 Payment Mode", PAYMENT_CHOICES, index=default_index, key=f'edit_mode_{selected_id}')
                st.markdown("</div>", unsafe_allow_html=True)
            # Calculate based on payment mode
            company_gets, prince_gets, justice_gets = calculate_payment_split(new_mode, new_cost, new_fee, new_tip)
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
                        "prince_gets": prince_gets,
                        "justice_gets": justice_gets
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
