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
    /* Remove top padding and margins */
    .main {
        padding-top: 0rem;
    }
    
    /* Maximize content width */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    
    /* Reduce spacing on sections */
    h1, h2, h3 {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Improve dataframe height */
    [data-testid="stDataFrame"] {
        height: auto;
    }
    
    /* Reduce expander margins */
    .streamlit-expanderHeader {
        padding: 0.5rem 0rem;
    }
    
    /* Remove extra spacing from st.markdown */
    .stMarkdown {
        margin-bottom: 0.5rem;
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
    <p style='text-align:center; font-size:1rem; color:#6c757d; font-family: Arial, sans-serif; margin-bottom: 1rem;'>
        Built with Love from Kofi ❤️
    </p>
    <hr style='margin: 0.5rem 0;'>
    """, 
    unsafe_allow_html=True,
)


PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider (Cash)',
    'Split: Item to Company, Delivery+Tip to Rider'
]


# --- Add a sale form ---
with st.form("sale_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    date = col1.date_input("Date", datetime.now())
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
        st.write(response)  # Optional for debugging


# --- Fetch all sales ---
response = supabase.table("sales").select("*").order("date", desc=True).execute()
df = pd.DataFrame(response.data) if response.data else pd.DataFrame()


if df.empty:
    st.info('No data yet. Add your first sale above.')
else:
    st.sidebar.header('Filter')
    # Parse 'date' as datetime
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    # Ensure numeric columns are float
    for col in ['cost_of_item', 'delivery_fee', 'tip', 'company_gets', 'rider_gets']:
        df[col] = pd.to_numeric(df[col], errors='coerce')


    # --- Date range filter using only dates present in data ---
    unique_dates = sorted(df['date'].dt.date.dropna().unique())
    if unique_dates:
        start_date, end_date = st.sidebar.select_slider(
            'Select Date Range',
            options=unique_dates,
            value=(unique_dates[0], unique_dates[-1])
        )
    else:
        start_date, end_date = None, None


    # Other filters
    locations = st.sidebar.multiselect('Locations', sorted(df['location'].dropna().unique()), default=None)
    payment_modes = st.sidebar.multiselect('Payment Mode', PAYMENT_CHOICES, default=None)


    # Filter logic using only dates available in data
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
        
        # Modern styled header for filtered sales
        st.markdown(
            """
            <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        padding: 1rem; border-radius: 10px; margin-bottom: 0.8rem; margin-top: 0.5rem;'>
                <h3 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
                    📊 Filtered Sales Records
                </h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.dataframe(filtered_display.reset_index(drop=True), use_container_width=True, height=300)

        # Modern styled header for summary statistics
        st.markdown(
            """
            <div style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); 
                        padding: 1rem; border-radius: 10px; margin: 0.8rem 0;'>
                <h3 style='color: white; margin: 0; font-family: Arial, sans-serif; text-align: center;'>
                    💹 Summary Statistics
                </h3>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # Summary metrics with improved styling
        st.markdown(
            """
            <style>
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
        
        col_sum1, col_sum2, col_sum3, col_sum4, col_sum5 = st.columns(5)
        
        with col_sum1:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-label'>🚚 Delivery Fees</div>
                    <div class='metric-value'>₵{filtered['delivery_fee'].sum():.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col_sum2:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-label'>💰 Item Cost</div>
                    <div class='metric-value'>₵{filtered['cost_of_item'].sum():.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col_sum3:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-label'>💵 Tips</div>
                    <div class='metric-value'>₵{filtered['tip'].sum():.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col_sum4:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-label'>🏢 Company</div>
                    <div class='metric-value'>₵{filtered['company_gets'].sum():.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col_sum5:
            st.markdown(
                f"""
                <div class='metric-card'>
                    <div class='metric-label'>🚴 Rider</div>
                    <div class='metric-value'>₵{filtered['rider_gets'].sum():.2f}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.warning("⚠️ No records for selected filter combination.")


    # --- Edit/delete section with modern styling ---
    st.markdown(
        """
        <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 1rem; border-radius: 10px; margin: 0.8rem 0;'>
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
            # Display selected record in a styled container
            st.markdown("#### 📄 Selected Record")
            edit_row_display = edit_row.copy()
            edit_row_display['date'] = edit_row_display['date'].dt.strftime('%a, %d/%m/%Y')
            edit_row_display = edit_row_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
            st.dataframe(edit_row_display, use_container_width=True)

            st.markdown("---")
            st.markdown("#### ✏️ Edit Record Details")
            
            # Create two-column layout for inputs
            edit_col1, edit_col2 = st.columns(2)
            
            with edit_col1:
                new_loc = st.text_input("📍 Location", value=str(edit_row['location'].values[0]), key=f'edit_loc_{selected_id}')
                new_cost = st.number_input("💰 Cost of Item", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', key=f'edit_cost_{selected_id}')
                new_fee = st.number_input("🚚 Delivery Fee", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', key=f'edit_fee_{selected_id}')
            
            with edit_col2:
                new_tip = st.number_input("💵 Tip", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', key=f'edit_tip_{selected_id}')
                selected_mode = edit_row['payment_mode'].values[0]
                if selected_mode in PAYMENT_CHOICES:
                    default_index = PAYMENT_CHOICES.index(selected_mode)
                else:
                    default_index = 0
                new_mode = st.selectbox("💳 Payment Mode", PAYMENT_CHOICES, index=default_index, key=f'edit_mode_{selected_id}')

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

            st.markdown("---")
            
            # Action buttons with modern styling
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
                        st.experimental_rerun()
                    else:
                        st.error("❌ Failed to update record.")
                        st.write(response)

            with btn_col2:
                if st.button("🗑️ Delete Record", type="secondary", use_container_width=True):
                    response = supabase.table("sales").delete().eq("id", int(selected_id)).execute()
                    if response.data:
                        st.success("🗑️ Record deleted successfully!")
                        st.experimental_rerun()
                    else:
                        st.error("❌ Failed to delete record.")
                        st.write(response)
        else:
            st.info("ℹ️ Please enter a valid Sale ID from the filtered records above to edit or delete.")
