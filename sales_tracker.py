import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

st.title('Daily Sales Tracker - Mannequins Ghana')

DB_FILE = "sales.db"
PAYMENT_CHOICES = [
    'All to Company (MoMo/Bank)',
    'All to Rider',
    'Split: Item to Company, Delivery+Tip to Rider'
]

def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def create_table(conn):
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            location TEXT,
            cost_of_item REAL,
            delivery_fee REAL,
            tip REAL,
            payment_mode TEXT,
            company_gets REAL,
            rider_gets REAL
        )
    ''')
    conn.commit()

conn = get_conn()
create_table(conn)

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
    elif mode == 'All to Rider':
        company_gets = cost
        rider_gets = 0.0
    elif mode == 'Split: Item to Company, Delivery+Tip to Rider':
        company_gets = 0.0
        rider_gets = 0.0
    else:
        company_gets = 0.0
        rider_gets = 0.0
    conn.execute("""
        INSERT INTO sales (date, location, cost_of_item, delivery_fee, tip, payment_mode, company_gets, rider_gets)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        date.strftime('%Y-%m-%d'), location, cost, fee, tip, mode, company_gets, rider_gets
    ))
    conn.commit()
    st.success("Sale added!")

# --- Fetch and filter sales: now by single date only ---
st.header('Sales Summary & Filtering')
df = pd.read_sql_query("SELECT * FROM sales ORDER BY date DESC", conn)

if len(df) == 0:
    st.info('No data yet. Add your first sale above.')
else:
    st.sidebar.header('Filter')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    unique_dates = df['date'].dropna().dt.date.unique()
    default_date = unique_dates[0] if len(unique_dates) else datetime.now().date()
    filter_date = st.sidebar.date_input('Filter by date', default_date)
    locations = st.sidebar.multiselect('Locations', sorted(df['location'].dropna().unique()), default=None)
    payment_modes = st.sidebar.multiselect('Payment Mode', PAYMENT_CHOICES, default=None)
    
    mask = (df['date'].dt.date == filter_date)
    if locations:
        mask = mask & (df['location'].isin(locations))
    if payment_modes:
        mask = mask & (df['payment_mode'].isin(payment_modes))
    filtered = df[mask]

    # --- Capitalize display column headings & Proper Date Format ---
    filtered_display = filtered.copy()
    filtered_display['date'] = filtered_display['date'].dt.strftime('%a, %d/%m/%Y')
    filtered_display = filtered_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
    
    st.subheader('Filtered Sales and Summary')
    st.dataframe(filtered_display.reset_index(drop=True))

    st.subheader('Summary Statistics')
    col_sum1, col_sum2, col_sum3, col_sum4, col_sum5 = st.columns(5)
    col_sum1.metric('Total Delivery Fees', f"{filtered['delivery_fee'].sum():.2f}")
    col_sum2.metric('Total Item Cost', f"{filtered['cost_of_item'].sum():.2f}")
    col_sum3.metric('Total Tips', f"{filtered['tip'].sum():.2f}")
    col_sum4.metric('Total Owed To Company', f"{filtered['company_gets'].sum():.2f}")
    col_sum5.metric('Total Owed To Rider', f"{filtered['rider_gets'].sum():.2f}")

    st.download_button('Download Filtered Data as CSV', filtered_display.to_csv(index=False), 'filtered_sales.csv')

    # --- Edit/delete section ---
    st.subheader("Edit or Delete a Sale Record")
    selected_id = st.number_input("Enter Sale ID to Edit/Delete", min_value=1, step=1)
    edit_row = df[df['id'] == selected_id]
    if not edit_row.empty:
        st.write("Selected Record:")
        edit_row_display = edit_row.copy()
        edit_row_display['date'] = edit_row_display['date'].dt.strftime('%a, %d/%m/%Y')
        edit_row_display = edit_row_display.rename(columns=lambda x: ' '.join(word.capitalize() for word in x.split('_')))
        st.dataframe(edit_row_display)
        new_cost = st.number_input("New Cost of Item", min_value=0.0, value=float(edit_row['cost_of_item'].values[0]), format='%.2f', key='edit_cost')
        new_fee = st.number_input("New Delivery Fee", min_value=0.0, value=float(edit_row['delivery_fee'].values[0]), format='%.2f', key='edit_fee')
        new_tip = st.number_input("New Tip", min_value=0.0, value=float(edit_row['tip'].values[0]), format='%.2f', key='edit_tip')
        new_mode = st.selectbox("New Payment Mode", PAYMENT_CHOICES, index=PAYMENT_CHOICES.index(edit_row['payment_mode'].values[0]), key='edit_mode')
        if new_mode == 'All to Company (MoMo/Bank)':
            company_gets = 0.0
            rider_gets = new_fee + new_tip
        elif new_mode == 'All to Rider':
            company_gets = new_cost
            rider_gets = 0.0
        elif new_mode == 'Split: Item to Company, Delivery+Tip to Rider':
            company_gets = 0.0
            rider_gets = 0.0
        else:
            company_gets = 0.0
            rider_gets = 0.0
        if st.button("Update Record"):
            conn.execute("""
                UPDATE sales SET cost_of_item = ?, delivery_fee = ?, tip = ?, payment_mode = ?, 
                company_gets = ?, rider_gets = ? WHERE id = ?
            """, (new_cost, new_fee, new_tip, new_mode, company_gets, rider_gets, int(selected_id)))
            conn.commit()
            st.rerun()
        if st.button("Delete Record"):
            conn.execute("DELETE FROM sales WHERE id = ?", (int(selected_id),))
            conn.commit()
            st.rerun()
    else:
        st.info("Enter a valid Sale ID to edit or delete.")
