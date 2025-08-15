import streamlit as st
import pandas as pd
import altair as alt
import warnings
import base64

warnings.filterwarnings("ignore", message="Data Validation extension is not supported and will be removed")

# Configure Streamlit layout
st.set_page_config(layout="wide", page_title="Product Reorder Dashboard", page_icon="📦")
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)

from PIL import Image

# Load logo image (make sure it's in the same directory or adjust the path)
logo = Image.open("ATEC-Logo-Icon-White-2022-2500x1879.png")

# Create columns for logo and title
col1, col2 = st.columns([1, 6])

with col1:
    st.image(logo, width=200)

with col2:
    st.markdown("""
        <h1 style='margin-bottom: 0;'>ATEC Product Reorder Dashboard</h1>
        <h4 style='color: gray; margin-top: 0;'>Rental Demand • Inventory • Reorder Insights</h4>
    """, unsafe_allow_html=True)


# Load Excel data
df_main = pd.read_excel("Rental_Opportunity_Products_This_Year.xlsx", sheet_name="Sheet2")
df_groups = pd.read_excel("Rental_Opportunity_Products_This_Year.xlsx", sheet_name="Rental Opportunity Products...")

# Clean column names
df_main.columns = df_main.columns.str.strip()
df_groups.columns = df_groups.columns.str.strip()

# Deduplicate group sheet to one row per product
group_lookup = df_groups[
    ['Product name',
     'Product Group List (Existing Product) (Product)',
     'Sub-Category List (Existing Product) (Product)']
].drop_duplicates(subset='Product name')

# Merge product group info into df_main
df_main = df_main.merge(
    group_lookup,
    how='left',
    left_on='Item',
    right_on='Product name'
)

# Assign agents based on product group
agent_map = {
    'Radiated Emissions': 'Kevin',
    'Radiated Immunity': 'Kevin',
    'Signal Analysis': 'Kevin',
    'AC Power Supplies/Loads': 'Jaime',
    'DC Power Supplies/Loads': 'Jaime',
    'Conducted Emissions': 'Jaime',
    'Conducted Immunity': 'Jaime',
    'Environmental Simulation': 'Nicol',
    'Environmental Monitoring': 'Nicol',
    'NDT/Inspection': 'Cesar',
    'Component Testing': 'Cesar',
    'Data Acquisition': 'Cesar',
    'RF Safety': 'Cesar',
    'Calibration': 'Cesar',
    'Network Communications': 'Josh Dodson',
    'Facility Power Monitoring': 'Josh Dodson',
    'Industrial Electrical Testing': 'Josh Villaflor',
    'Cellular Communications': 'Josh Villaflor',
    'Radio Communications': 'Josh Villaflor'
}
df_main['Agent'] = df_main['Product Group List (Existing Product) (Product)'].map(agent_map)

# Let user select their name
selected_agent = st.selectbox("👤 Choose your name", df_main['Agent'].dropna().unique())
agent_data = df_main[df_main['Agent'] == selected_agent].copy()
agent_data['Price Group'] = pd.to_numeric(agent_data['Price Group'], errors='coerce')



if 'Opps this year' in agent_data.columns:
    agent_data['Demand Score'] = agent_data['Opps this year'] / (
        agent_data['Qty in Stock'] + agent_data['Qty On Rent'] + 1
    )
    agent_data['Reorder?'] = (agent_data['Demand Score'] > 1.3)

    agent_data = agent_data.sort_values(by='Demand Score', ascending=False)
    

# Create tabs for home, table, and chart
homepage, tab1, tab2, tab3 = st.tabs(["🏠 Homepage", "📦 Product Table", "📊 Demand Score Chart", "📘 Training Guide"])

with homepage:
    st.header("📊 Product Group Distribution & Inventory vs. Demand")

    # Pie chart: Product Group Distribution (for selected agent)
    group_counts = agent_data['Product Group List (Existing Product) (Product)'].value_counts().reset_index()
    group_counts.columns = ['Product Group', 'Count']

    st.subheader("Product Group Distribution")
    pie_chart = alt.Chart(group_counts).mark_arc(innerRadius=50).encode(
        theta=alt.Theta(field="Count", type="quantitative"),
        color=alt.Color(field="Product Group", type="nominal"),
        tooltip=['Product Group', 'Count']
    )
    st.altair_chart(pie_chart, use_container_width=True)

    # Bar chart: Product Group Distribution
    bar_chart = alt.Chart(group_counts).mark_bar().encode(
        x=alt.X('Product Group:N', sort='-y'),
        y=alt.Y('Count:Q'),
        color='Product Group:N',
        tooltip=['Product Group', 'Count']
    ).properties(height=350)
    st.altair_chart(bar_chart, use_container_width=True)

    # Grouped Bar Chart: Inventory vs. Demand by Product
    st.subheader("Inventory vs. Demand (Top 20 by Demand Score)")
    if 'Demand Score' in agent_data.columns:
        top_products = agent_data.sort_values(by='Demand Score', ascending=False).head(20)
        inventory_vs_demand = pd.melt(
            top_products,
            id_vars=['Item'],
            value_vars=['Qty in Stock', 'Opps this year'],
            var_name='Metric',

            value_name='Value'
        )
        grouped_bar = alt.Chart(inventory_vs_demand).mark_bar().encode(
            x=alt.X('Item:N', sort=top_products['Item'].tolist(), title='Product'),
            y=alt.Y('Value:Q'),
            color=alt.Color('Metric:N'),
            tooltip=['Item', 'Metric', 'Value']
        ).properties(height=350)
        st.altair_chart(grouped_bar, use_container_width=True)
    else:
        st.info("Demand Score not available yet. Please select an agent with data.")

# Add multi-select Product Group filter
group_col = 'Product Group List (Existing Product) (Product)'
subcat_col = 'Sub-Category List (Existing Product) (Product)'

subcategories_groups = agent_data[group_col].dropna().unique()
selected_groups = st.multiselect(
    "📂 Filter by Product Group",
    options=sorted(subcategories_groups),
    default=sorted(subcategories_groups)  # show all by default
)

if selected_groups:
    agent_data = agent_data[agent_data[group_col].isin(selected_groups)]

# --- NEW: per-group subcategory dropdowns ---
# Build a mask that keeps rows from each selected group that match chosen subcategories
if selected_groups:
    keep_mask = False
    for g in selected_groups:
        # List subcategories available within this group for current agent_data
        subcats_in_g = sorted(agent_data.loc[agent_data[group_col] == g, subcat_col].dropna().unique().tolist())

        # If a group has no subcats, skip the control and include all rows for that group
        if len(subcats_in_g) == 0:
            keep_mask = keep_mask | (agent_data[group_col] == g)
            continue

        chosen_subcats = st.multiselect(
            f"🔽 Subcategories in “{g}”",
            options=subcats_in_g,
            default=subcats_in_g,     # select all by default
            key=f"subcats_{g}"        # unique key per group
        )

        # If user deselects some, filter; otherwise include all subcats for that group
        keep_mask = keep_mask | (
            (agent_data[group_col] == g) &
            (agent_data[subcat_col].isin(chosen_subcats) if len(chosen_subcats) > 0 else False)
        )

    # Apply combined mask across all selected groups
    agent_data = agent_data[keep_mask]



   

# Add a search box for Item (SKU) or Product name
search_query = st.text_input("🔍 Search for Item or Product Name")
if search_query:
    agent_data = agent_data[
        agent_data['Item'].astype(str).str.contains(search_query, case=False, na=False) |
        agent_data['Product name'].astype(str).str.contains(search_query, case=False, na=False)
    ]

# Let user pick a column to sort by
sort_col = st.selectbox("Sort table by:", agent_data.columns, index=agent_data.columns.get_loc('Demand Score') if 'Demand Score' in agent_data.columns else 0)
sort_ascending = st.checkbox("Sort ascending?", value=False)
agent_data = agent_data.sort_values(by=sort_col, ascending=sort_ascending)

agent_data = agent_data.drop(columns=['Product name'], errors='ignore')

# Row highlighting function
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

# Product Table Tab
with tab1:
    st.write(f"📦 **Product List for {selected_agent}** (highlighted if reorder needed)")
    st.dataframe(agent_data.style.apply(highlight_row, axis=1), use_container_width=True)

# Demand Score Chart Tab
with tab2:
    st.write("📊 **Demand Score by Item**")
    chart_data = agent_data[['Item', 'Demand Score']].sort_values(by='Demand Score', ascending=False).head(50)

    chart = alt.Chart(chart_data).mark_bar().encode(
        x=alt.X('Item:N', sort='-y', title='Product'),
        y=alt.Y('Demand Score:Q', title='Demand Score'),
        tooltip=['Item', 'Demand Score']
    ).properties(height=500)

    st.altair_chart(chart, use_container_width=True)
# st.error("⚠️ Column 'Opps this year' not found in your Excel sheet.")  # Removed stray else

with tab3:
    st.header("📘 Product Reorder Dashboard – Training Guide")
    st.write("This guide provides an overview of how to use the Product Reorder Dashboard effectively.")
    # Optional download button
    with open("ATEC Product Reorder Dashboard Training Guide.pdf", "rb") as f:
        st.download_button(
            label="📥 Download Training Guide",
            data=f,
            file_name="ATEC Product Reorder Dashboard Training Guide.pdf",
            mime="application/pdf"
        )