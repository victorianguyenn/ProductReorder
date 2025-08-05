import streamlit as st
import pandas as pd
import altair as alt
import warnings

warnings.filterwarnings("ignore", message="Data Validation extension is not supported and will be removed")

# Configure Streamlit layout
st.set_page_config(layout="wide", page_title="Product Reorder Dashboard", page_icon="📦")
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)

# Load Excel data
df_main = pd.read_excel("Rental_Opportunity_Products_This_Year.xlsx", sheet_name="Sheet2")
df_groups = pd.read_excel("Rental_Opportunity_Products_This_Year.xlsx", sheet_name="Rental Opportunity Products...")

# Clean column names
df_main.columns = df_main.columns.str.strip()
df_groups.columns = df_groups.columns.str.strip()

# Step 1: Deduplicate group sheet to one row per product
group_lookup = df_groups[['Product name', 'Product Group List (Existing Product) (Product)']].drop_duplicates(subset='Product name')

# Step 2: Merge product group info into df_main
df_main = df_main.merge(
    group_lookup,
    how='left',
    left_on='Item',
    right_on='Product name'
)

# Step 3: Assign agents based on product group
agent_map = {
    'Radiated Emissions': 'Kevin',
    'Radiated Immunity': 'Kevin',
    'Signal Analysis': 'Kevin',
    'AC Power Supplies/Loads': 'Jaime',
    'DC Power Supplies/Loads': 'Jaime',
    'Conducted Emissions': 'Jaime',
    'Conducted Immunity': 'Jaime',
    'Environment Simulation': 'Nicol',
    'Environmental Monitoring': 'Nicol',
    'NDT/Inspection': 'Cesar',
    'Component Testing': 'Cesar',
    'Data Acquisition': 'Cesar',
    'RF Safety': 'Cesar',
    'Calibrators': 'Cesar',
    'Network Communications': 'Josh Dodson',
    'Facility Power Monitoring': 'Josh Dodson',
    'Industrial Electric Testing': 'Josh Villaflor',
    'Cellular Communications': 'Josh Villaflor',
    'Radio Communications': 'Josh Villaflor'
}
df_main['Agent'] = df_main['Product Group List (Existing Product) (Product)'].map(agent_map)

# Step 4: Let user select their name
selected_agent = st.selectbox("👤 Choose your name", df_main['Agent'].dropna().unique())
agent_data = df_main[df_main['Agent'] == selected_agent].copy()
agent_data['Price Group'] = pd.to_numeric(agent_data['Price Group'], errors='coerce')

# Step 5: Create tabs for table and chart
tab1, tab2 = st.tabs(["📦 Product Table", "📊 Demand Score Chart"])

# Step 4.5: Add multi-select subcategory filter (Product Group)
subcategories = agent_data['Product Group List (Existing Product) (Product)'].dropna().unique()
selected_subcategories = st.multiselect(
    "📂 Filter by Product Group (Subcategories)",
    options=sorted(subcategories),
    default=sorted(subcategories)  # show all by default
)

if selected_subcategories:
    agent_data = agent_data[agent_data['Product Group List (Existing Product) (Product)'].isin(selected_subcategories)]


if 'Opps this year' in agent_data.columns:
    # Step 6: Calculate Demand Score and Reorder flag
    agent_data['Demand Score'] = agent_data['Opps this year'] / (
        agent_data['Qty in Stock'] + agent_data['Qty On Rent'] + 1
    )
    agent_data['Reorder?'] = (agent_data['Demand Score'] > 1.3)
    #  | (agent_data['Qty in Stock'] == 0

    # Step 7: Row highlighting function
    def highlight_row(row):
        styles = [''] * len(row)
        if row['Reorder?']:
            styles = ['background-color: #ffe6e6'] * len(row)
        if 'Qty in Stock' in row:
            q = row['Qty in Stock']
            col = row.index.get_loc('Qty in Stock')
            if q == 0:
                styles[col] = 'background-color: #ffb3b3'
            elif q < 3:
                styles[col] = 'background-color: #fff2cc'
            else:
                styles[col] = 'background-color: #d9f2d9'
        return styles

    # Tab 1: Product Table
    with tab1:
        st.write(f"📦 **Product List for {selected_agent}** (highlighted if reorder needed)")
        st.dataframe(agent_data.style.apply(highlight_row, axis=1), use_container_width=True)

    # Tab 2: Demand Score Chart
    with tab2:
        st.write("📊 **Demand Score by Item**")
        chart_data = agent_data[['Item', 'Demand Score']].sort_values(by='Demand Score', ascending=False).head(50)

        chart = alt.Chart(chart_data).mark_bar().encode(
            x=alt.X('Item:N', sort='-y', title='Product'),
            y=alt.Y('Demand Score:Q', title='Demand Score'),
            tooltip=['Item', 'Demand Score']
        ).properties(height=500)

        st.altair_chart(chart, use_container_width=True)
else:
    st.error("⚠️ Column 'Opps this year' not found in your Excel sheet.")
