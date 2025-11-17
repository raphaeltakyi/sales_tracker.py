import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from typing import Tuple, Dict, Optional


# ============================================================================
# CONFIGURATION & CONSTANTS
# ============================================================================

PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]

PAYMENT_MODE_LOGIC = {
    'All to Company (MoMo/Bank)': lambda cost, fee, tip: (0.0, fee + tip),
    'All to Rider (Cash)': lambda cost, fee, tip: (cost, 0.0),
    'Split: Item to Company, Delivery+Tip to Rider': lambda cost, fee, tip: (0.0, 0.0),
}

METRIC_CARDS = [
    {"label": "🚚 Delivery Fees", "key": "delivery_fee", "gradient": "667eea, 764ba2"},
    {"label": "💰 Item Cost", "key": "cost_of_item", "gradient": "f093fb, f5576c"},
    {"label": "💵 Tips", "key": "tip", "gradient": "4facfe, 00f2fe"},
    {"label": "🏢 Company", "key": "company_gets", "gradient": "43e97b, 38f9d7"},
    {"label": "🚴 Rider", "key": "rider_gets", "gradient": "fa709a, fee140"},
]

# Centralized CSS styles
STYLES = {
    "main": """
    <style>
        .main { padding-top: 0rem; }
        .block-container { 
            padding-top: 1rem; padding-bottom: 0rem; 
            padding-left: 1rem; padding-right: 1rem; 
            max-width: 100%; 
        }
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
        
        .metric-container { display: flex; gap: 10px; margin-bottom: 10px; }
        .metric-card {
            flex: 1;
            padding: 1.5rem;
            border-radius: 8px;
            color: white;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            font-weight: 700;
        }
        .metric-label { font-size: 0.85rem; opacity: 0.9; margin-bottom: 0.5rem; font-weight: 600; }
        .metric-value { font-size: 1.8rem; font-weight: 700; }
        
        .edit-box { background-color: #f8f9fa; padding: 1rem; border-radius: 8px; }
    </style>
    """,
    "gradient_header": """
    <div style='background: linear-gradient(135deg, {gradient}); 
                padding: 0.3rem; border-radius: 10px; margin: 1rem 0;'>
        <h3 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
            {title}
        </h3>
    </div>
    """
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

@st.cache_resource
def init_supabase() -> Client:
    """Initialize Supabase client once and cache it."""
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_KEY")
    if not url or not key:
        st.error("❌ Missing Supabase credentials in secrets.toml")
        st.stop()
    return create_client(url, key)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_sales_data() -> pd.DataFrame:
    """Fetch and prepare sales data with caching."""
    supabase = init_supabase()
    response = supabase.table("sales").select("*").order("date", desc=True).execute()
    
    if not response.data:
        return pd.DataFrame()
    
    df = pd.DataFrame(response.data)
    
    # Type conversions in one place
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    for col in ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df


def calculate_payment_split(mode: str, cost: float, fee: float, tip: float) -> Tuple[float, float]:
    """Calculate company and rider splits based on payment mode."""
    calculator = PAYMENT_MODE_LOGIC.get(mode, lambda c, f, t: (0.0, 0.0))
    return calculator(cost, fee, tip)


def render_gradient_header(title: str, gradient: str = "667eea, 764ba2") -> None:
    """Render a styled gradient header."""
    st.markdown(
        STYLES["gradient_header"].format(gradient=gradient, title=title),
        unsafe_allow_html=True
    )


def render_metric_cards(filtered_df: pd.DataFrame) -> None:
    """Render all metric cards efficiently."""
    cols = st.columns(len(METRIC_CARDS))
    
    for col, metric_info in zip(cols, METRIC_CARDS):
        with col:
            value = filtered_df[metric_info["key"]].sum()
            st.markdown(
                f"""
                <div class='metric-card' style='background: linear-gradient(135deg, #{metric_info["gradient"]});'>
                    <div class='metric-label'>{metric_info["label"]}</div>
                    <div class='metric-value'>₵{value:,.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )


def format_display_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Format dataframe for display."""
    display_df = df.copy()
    display_df['date'] = display_df['date'].dt.strftime('%a, %d/%m/%Y')
    display_df = display_df.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
    return display_df


def apply_filters(df: pd.DataFrame, start_date, end_date, locations: list, payment_modes: list) -> pd.DataFrame:
    """Apply filters to dataframe using pandas query for efficiency."""
    if not start_date or not end_date:
        return pd.DataFrame()
    
    # Build mask efficiently
    mask = (df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)
    
    if locations:
        mask &= df['location'].isin(locations)
    
    if payment_modes:
        mask &= df['payment_mode'].isin(payment_modes)
    
    return df[mask]


# ============================================================================
# PAGE SETUP
# ============================================================================

st.set_page_config(
    page_title="Daily Sales Tracker - Mannequins Ghana",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(STYLES["main"], unsafe_allow_html=True)

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


# ============================================================================
# ADD SALE FORM
# ============================================================================

render_gradient_header("➕ Add New Sale")

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
    try:
        company_gets, rider_gets = calculate_payment_split(mode, cost, fee, tip)
        
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
        
        supabase = init_supabase()
        response = supabase.table("sales").insert(data).execute()
        
        if response.data:
            st.success("✅ Sale added successfully!")
            st.cache_data.clear()  # Clear cache to fetch fresh data
        else:
            st.error("❌ Failed to add sale.")
    
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


# ============================================================================
# FETCH & DISPLAY DATA
# ============================================================================

df = fetch_sales_data()

if df.empty:
    st.info('📭 No data yet. Add your first sale above.')
else:
    # Sidebar filters
    st.sidebar.header('🔍 Filter')
    
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
    
    # Apply filters
    filtered = apply_filters(df, start_date, end_date, locations, payment_modes)
    
    if not filtered.empty:
        # Display filtered records
        render_gradient_header("📊 Filtered Sales Records", "667eea, 764ba2")
        
        with st.expander("View Table", expanded=True):
            st.dataframe(
                format_display_dataframe(filtered).reset_index(drop=True),
                use_container_width=True,
                height=300
            )
        
        # Display summary statistics
        render_gradient_header("💹 Summary Statistics", "f093fb, f5576c")
        render_metric_cards(filtered)
    
    else:
        st.warning("⚠️ No records for selected filter combination.")
    
    
    # ============================================================================
    # MANAGE RECORDS (EDIT/DELETE)
    # ============================================================================
    
    render_gradient_header("🔧 Manage Records", "f093fb, f5576c")
    
    with st.expander("📝 Edit or Delete a Sale Record", expanded=False):
        selected_id = st.number_input(
            "🔍 Enter Sale ID",
            min_value=1,
            step=1,
            key='select_id',
            help="Enter the ID of the record you want to edit or delete"
        )
        
        edit_row = df[df['id'] == selected_id]
        
        if not edit_row.empty:
            st.markdown("#### 📄 Selected Record")
            st.dataframe(format_display_dataframe(edit_row), use_container_width=True)
            st.markdown("---")
            st.markdown("#### ✏️ Edit Record Details")
            
            edit_col1, edit_col2 = st.columns(2)
            
            with edit_col1:
                st.markdown("<div class='edit-box'>", unsafe_allow_html=True)
                new_loc = st.text_input(
                    "📍 Location",
                    value=str(edit_row['location'].values[0]),
                    key=f'edit_loc_{selected_id}'
                )
                new_cost = st.number_input(
                    "💰 Cost of Item",
                    min_value=0.0,
                    value=float(edit_row['cost_of_item'].values[0]),
                    format='%.2f',
                    key=f'edit_cost_{selected_id}'
                )
                new_fee = st.number_input(
                    "🚚 Delivery Fee",
                    min_value=0.0,
                    value=float(edit_row['delivery_fee'].values[0]),
                    format='%.2f',
                    key=f'edit_fee_{selected_id}'
                )
                st.markdown("</div>", unsafe_allow_html=True)
            
            with edit_col2:
                st.markdown("<div class='edit-box'>", unsafe_allow_html=True)
                new_tip = st.number_input(
                    "💵 Tip",
                    min_value=0.0,
                    value=float(edit_row['tip'].values[0]),
                    format='%.2f',
                    key=f'edit_tip_{selected_id}'
                )
                selected_mode = edit_row['payment_mode'].values[0]
                default_index = PAYMENT_CHOICES.index(selected_mode) if selected_mode in PAYMENT_CHOICES else 0
                new_mode = st.selectbox(
                    "💳 Payment Mode",
                    PAYMENT_CHOICES,
                    index=default_index,
                    key=f'edit_mode_{selected_id}'
                )
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Calculate split
            company_gets, rider_gets = calculate_payment_split(new_mode, new_cost, new_fee, new_tip)
            
            st.markdown("---")
            btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 2])
            
            with btn_col1:
                if st.button("✅ Update Record", type="primary", use_container_width=True):
                    try:
                        update_data = {
                            "location": new_loc,
                            "cost_of_item": new_cost,
                            "delivery_fee": new_fee,
                            "tip": new_tip,
                            "payment_mode": new_mode,
                            "company_gets": company_gets,
                            "rider_gets": rider_gets
                        }
                        
                        supabase = init_supabase()
                        response = supabase.table("sales").update(update_data).eq("id", int(selected_id)).execute()
                        
                        if response.data:
                            st.success("✅ Record updated successfully!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Failed to update record.")
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            
            with btn_col2:
                if st.button("🗑️ Delete Record", type="secondary", use_container_width=True):
                    try:
                        supabase = init_supabase()
                        response = supabase.table("sales").delete().eq("id", int(selected_id)).execute()
                        
                        if response.data or len(response.data) == 0:  # Successful deletion
                            st.success("🗑️ Record deleted successfully!")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Failed to delete record.")
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        
        else:
            st.info("ℹ️ Please enter a valid Sale ID from the filtered records above to edit or delete.")
