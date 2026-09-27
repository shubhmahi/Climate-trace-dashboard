import streamlit as st
import pandas as pd
import glob
import os
import plotly.express as px
import plotly.io as pio

# --- Set default template & Font for Plotly (Light Theme) ---
pio.templates.default = "plotly_white"  # Dark se White kar diya
custom_font = dict(family="Tw Cen MT, sans-serif", size=14, color="black")  # Font color black kar diya

# --- Page Configuration ---
st.set_page_config(page_title="ATO Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- Custom CSS ---
st.markdown(
    """
    <style>
    html, body, [class*="css"]  {
        font-family: 'Tw Cen MT', sans-serif;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Title and Logo ---
col1, col2 = st.columns([1, 8])
with col1:
    logo_path = "ATO logo.png"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
    else:
        st.warning("Logo not found")
with col2:
    # Heading ka color bhi black kar diya
    st.markdown(
        "<h1 style='text-align: left; padding-top: 15px; font-family: Tw Cen MT; color: black;'>Asian Transport Observatory</h1>",
        unsafe_allow_html=True)

st.markdown("---")


# --- Data Loading Logic ---
@st.cache_data
def load_data():
    econ_file = os.path.join("data", "Economies 1 - Copy.xlsx")
    if os.path.exists(econ_file):
        df_econ = pd.read_excel(econ_file)
    else:
        return pd.DataFrame()

    csv_files = glob.glob(os.path.join("data", "*.csv"))
    df_list = []

    for file in csv_files:
        temp_df = pd.read_csv(file)
        gas_name = os.path.basename(file).split('_')[1] if '_' in os.path.basename(file) else 'Unknown'
        temp_df['gas_type'] = gas_name

        if 'period_start' in temp_df.columns:
            temp_df['Year'] = pd.to_datetime(temp_df['period_start']).dt.year

        df_list.append(temp_df)

    if df_list:
        df_emissions = pd.concat(df_list, ignore_index=True)
        df_merged = pd.merge(df_emissions, df_econ, left_on="country_id", right_on="economy_iso", how="left")
        return df_merged
    return pd.DataFrame()


df = load_data()

if not df.empty:
    st.sidebar.header("Filters")

    filter_columns = {
        'Year': 'Year',
        'economy_name': 'Economy Name',
        'economy_iso': 'Country Code',
        'economy_region': 'Region',
        'economy_incomegroup': 'Income Group',
        'subsector': 'Subsector',
        'gas_type': 'Gas Type'
    }

    selections = {}

    for col, label in filter_columns.items():
        if col in df.columns:
            temp_df = df.copy()
            for other_col in filter_columns.keys():
                if other_col != col and other_col in st.session_state and st.session_state[other_col]:
                    temp_df = temp_df[temp_df[other_col].isin(st.session_state[other_col])]

            available_options = temp_df[col].dropna().unique().tolist()
            try:
                available_options.sort()
            except TypeError:
                pass

            selections[col] = st.sidebar.multiselect(
                label,
                options=available_options,
                default=st.session_state.get(col, []),
                key=col
            )

    # --- Apply Final Filters ---

    filtered_df_no_year = df.copy()
    for col, selected_vals in selections.items():
        if col != 'Year' and selected_vals:
            filtered_df_no_year = filtered_df_no_year[filtered_df_no_year[col].isin(selected_vals)]

    filtered_df = filtered_df_no_year.copy()
    if selections.get('Year'):
        filtered_df = filtered_df[filtered_df['Year'].isin(selections['Year'])]

    # --- Metrics / KPIs ---
    st.write(f"### Filtered Records: {len(filtered_df):,}")

    if 'emissions_quantity' in filtered_df.columns:
        total_emissions = filtered_df['emissions_quantity'].sum()


        def format_number(num):
            if num >= 1e9:
                return f"{num / 1e9:.2f} Billion"
            elif num >= 1e6:
                return f"{num / 1e6:.2f} Million"
            else:
                return f"{num:,.2f}"


        formatted_total = format_number(total_emissions)
        st.metric(label="Total Emissions (Tonnes)", value=f"{formatted_total}")

    # Helper maps for clean labels
    clean_labels = {
        'emissions_quantity': 'Emissions (Tonnes)',
        'economy_name': 'Economy Name',
        'economy_incomegroup': 'Income Group',
        'economy_region': 'Region',
        'Year': 'Year',
        'subsector': 'Subsector'
    }


    def apply_chart_font(fig):
        fig.update_layout(
            font=custom_font,
            title_font=dict(family="Tw Cen MT", size=18, color="black"),  # Title font color black
            legend_font=dict(family="Tw Cen MT", size=12, color="black")  # Legend font color black
        )
        return fig


    # --- Charts Section ---
    st.markdown("### Visualizations")

    if 'emissions_quantity' in filtered_df.columns:

        # ROW 1: Region & Income Group
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            if 'economy_region' in filtered_df.columns:
                reg_data = filtered_df.groupby('economy_region')['emissions_quantity'].sum().reset_index()
                fig_reg = px.pie(reg_data, names='economy_region', values='emissions_quantity',
                                 title="Emissions by Region", hole=0.4, labels=clean_labels)
                fig_reg.update_traces(hovertemplate="%{label}: %{value:,.2f} Tonnes<extra></extra>")
                apply_chart_font(fig_reg)
                st.plotly_chart(fig_reg, use_container_width=True)

        with col_chart2:
            if 'economy_incomegroup' in filtered_df.columns:
                inc_data = filtered_df.groupby('economy_incomegroup')['emissions_quantity'].sum().reset_index()
                fig_inc = px.bar(inc_data, x='economy_incomegroup', y='emissions_quantity', color='economy_incomegroup',
                                 title="Emissions by Income Group", labels=clean_labels, text_auto='.2s')
                fig_inc.update_traces(textposition='outside',
                                      hovertemplate="Income Group: %{x}<br>Emissions: %{y:,.2f} Tonnes<extra></extra>")
                fig_inc.update_yaxes(range=[0, inc_data['emissions_quantity'].max() * 1.15])
                apply_chart_font(fig_inc)
                st.plotly_chart(fig_inc, use_container_width=True)

        # ROW 2: Top 10 & Bottom 10
        col_chart3, col_chart4 = st.columns(2)

        if 'economy_name' in filtered_df.columns:
            econ_data = filtered_df.groupby('economy_name')['emissions_quantity'].sum().reset_index()
            econ_data = econ_data[econ_data['emissions_quantity'] > 0]

            with col_chart3:
                top10 = econ_data.sort_values(by='emissions_quantity', ascending=False).head(10)
                fig_top = px.bar(top10, x='emissions_quantity', y='economy_name', orientation='h',
                                 title="Top 10 Economies (Tonnes)", labels=clean_labels, text_auto='.2s')
                fig_top.update_layout(yaxis={'categoryorder': 'total ascending'})
                fig_top.update_traces(textposition='outside',
                                      hovertemplate="%{y}<br>Emissions: %{x:,.2f} Tonnes<extra></extra>")
                fig_top.update_xaxes(range=[0, top10['emissions_quantity'].max() * 1.25])
                apply_chart_font(fig_top)
                st.plotly_chart(fig_top, use_container_width=True)

            with col_chart4:
                bottom10 = econ_data.sort_values(by='emissions_quantity', ascending=True).head(10)
                fig_bot = px.bar(bottom10, x='emissions_quantity', y='economy_name', orientation='h',
                                 title="Bottom 10 Economies (Tonnes)", labels=clean_labels, text_auto='.2s')
                fig_bot.update_layout(yaxis={'categoryorder': 'total descending'})
                fig_bot.update_traces(textposition='outside',
                                      hovertemplate="%{y}<br>Emissions: %{x:,.2f} Tonnes<extra></extra>")
                fig_bot.update_xaxes(range=[0, bottom10['emissions_quantity'].max() * 1.25])
                apply_chart_font(fig_bot)
                st.plotly_chart(fig_bot, use_container_width=True)

        # ROW 3: Year by Year & Subsector
        col_chart5, col_chart6 = st.columns(2)

        with col_chart5:
            if 'Year' in filtered_df_no_year.columns:
                yearly_data = filtered_df_no_year.groupby('Year')['emissions_quantity'].sum().reset_index()
                fig_line = px.line(yearly_data, x='Year', y='emissions_quantity', markers=True,
                                   title="Year by Year Emissions (Tonnes)", labels=clean_labels,
                                   text='emissions_quantity')
                fig_line.update_traces(texttemplate='%{text:.2s}', textposition='top center',
                                       hovertemplate="Year: %{x}<br>Emissions: %{y:,.2f} Tonnes<extra></extra>")
                fig_line.update_layout(xaxis=dict(tickmode='linear', dtick=1, tickangle=-90))
                fig_line.update_yaxes(range=[0, yearly_data['emissions_quantity'].max() * 1.15])
                apply_chart_font(fig_line)
                st.plotly_chart(fig_line, use_container_width=True)

        with col_chart6:
            if 'subsector' in filtered_df_no_year.columns and 'Year' in filtered_df_no_year.columns:
                sub_data = filtered_df_no_year.groupby(['Year', 'subsector'])['emissions_quantity'].sum().reset_index()
                fig_stack = px.bar(sub_data, x='Year', y='emissions_quantity', color='subsector',
                                   title="Emissions by Subsector (Stacked)", labels=clean_labels)
                fig_stack.update_traces(
                    hovertemplate="Subsector: %{fullData.name}<br>Emissions: %{y:,.2f} Tonnes<extra></extra>")
                fig_stack.update_layout(xaxis=dict(tickmode='linear', dtick=1, tickangle=-90))
                apply_chart_font(fig_stack)
                st.plotly_chart(fig_stack, use_container_width=True)

    # --- Data Table ---
    st.markdown("### Data Preview")
    st.dataframe(filtered_df, use_container_width=True)

else:
    st.error("No data available. Check data folder and files.")