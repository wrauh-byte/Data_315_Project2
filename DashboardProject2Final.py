pip install pandas geopandas plotly pyvis streamlit openpyxl
import pandas as pd
import geopandas as gpd

import plotly.graph_objects as go
import plotly.express as px
import numpy as np

from pyvis.network import Network

import streamlit as st
import tempfile, os
import streamlit.components.v1 as components

import pickle
#---------Dashboard Configuration--------------
st.set_page_config(
    page_title="California Crime & Poverty Dashboard",
    layout="wide",
)
#Dashboard title
st.title("California Crime Statistics")
st.markdown("A break down of arrest data, and crime trends throughout California counties, as well as how poverty guidelines may relate from 2014-2024")

#-----Loaded Data-------
#2014-2024 arrest data from California's Federal Crime database
@st.cache_data(show_spinner="Loading arrest data…")
def load_arrest():
    return pd.read_csv(
        "https://github.com/wrauh-byte/Data_315_Project2/raw/refs/heads/main/cleaned_arrest_data.csv"
    )

#County map of California
@st.cache_data(show_spinner="Loading county boundaries…")
def load_gdf():
    return gpd.read_file(
        "https://raw.githubusercontent.com/wrauh-byte/Data_315_Project2/main/County_Boundaries.geojson"
    )
#2014-2024 Poverty guideline by family size data provided by the Federal Register
@st.cache_data(show_spinner="Loading poverty guidelines…")
def load_econ():
    url = "https://github.com/wrauh-byte/Data_315_Project2/raw/refs/heads/main/Federal_Poverty_Income_Guideline.xlsx"
    raw = pd.read_excel(url)
    raw.columns = raw.iloc[0].values
    raw = raw[1:].copy()

    col_map = {}
    for c in raw.columns:
        if isinstance(c, str) and c.strip() == "Family Size":
            col_map[c] = "Family_Size"
        elif isinstance(c, (float, np.float64)):
            col_map[c] = str(int(c)) if 1984 <= c <= 2026 else c
        else:
            try:
                y = int(str(c).strip())
                col_map[c] = str(y) if 1984 <= y <= 2026 else c
            except (ValueError, TypeError):
                col_map[c] = c
    raw.rename(columns=col_map, inplace=True)


    valid = ["Family_Size"] + [
        c for c in raw.columns
        if c != "Family_Size" and str(c).isdigit() and 1984 <= int(c) <= 2026
    ]
    raw = raw[valid].copy()
    for c in valid:
        if c != "Family_Size":
            raw[c] = pd.to_numeric(raw[c], errors="coerce")
    raw["Family_Size"] = pd.to_numeric(raw["Family_Size"], errors="coerce")
    raw.dropna(subset=["Family_Size"], inplace=True)
    raw.reset_index(drop=True, inplace=True)

    drop_years = [str(y) for y in range(1984, 2014)] + ["2025", "2026"]
    raw.drop(columns=[c for c in drop_years if c in raw.columns], errors="ignore", inplace=True)
    return raw

arrest = load_arrest()
gdf    = load_gdf()
econ   = load_econ()

CRIME_COLS = ["Violent Crimes", "Property Crime", "Drug Offenses", "Sex Offenses", "All Other Offenses"]

#------sidebar----------
st.sidebar.header("️Controls")
tab_choice = st.sidebar.radio(
    "Select View",
    ["🌐Overview","🗺️ Choropleth Map", "📈 Crime & Poverty Trends", "🕸️ Network Graph"],
)

#---------Tab 0 Overview map --------------
if tab_choice == "🌐Overview":
    st.header("🌐Overview of datasets and Where they were found")
    st.subheader("Links to Databases:")
    st.text("https://openjustice.doj.ca.gov/data\n"
            "https://www.federalregister.gov/documents/2026/01/15/2026-00755/annual-update-of-the-hhs-poverty-guidelines")




#---------Tab 1 Chloropleth map --------------
#header
if tab_choice == "🗺️ Choropleth Map":
    st.header("🗺️ Crime Incidents by County")

# Sidebar controls
    arrest_melted = arrest.melt(
        id_vars=["YEAR", "COUNTY"],
        value_vars=CRIME_COLS,
        var_name="Crime_Type",
        value_name="Crime_Count",
    )
    arrest_melted["COUNTY_CLEANED"] = (
        arrest_melted["COUNTY"].str.replace(" County", "", regex=False).str.strip()
    )
    crime_counts = (
        arrest_melted.groupby(["YEAR", "COUNTY_CLEANED", "Crime_Type"])["Crime_Count"]
        .sum()
        .reset_index()
        .rename(columns={"YEAR": "Year", "COUNTY_CLEANED": "CountyName"})
    )

    all_years      = sorted(crime_counts["Year"].unique())
    all_crime_types = sorted(crime_counts["Crime_Type"].unique())

    col1, col2 = st.sidebar.columns(2)
    selected_year_map  = st.sidebar.selectbox("Year", all_years, index=0)
    selected_crime_map = st.sidebar.selectbox("Crime Type", all_crime_types, index=0)


# Build merged GDF for the selection
    merged = gdf.merge(
        crime_counts[
            (crime_counts["Year"] == selected_year_map)
            & (crime_counts["Crime_Type"] == selected_crime_map)
        ],
        left_on="NAME10",
        right_on="CountyName",
        how="left",
    )
    merged["Crime_Count"] = merged["Crime_Count"].fillna(0)

    fig_map = px.choropleth(
        merged,
        geojson=gdf.__geo_interface__,
        locations="NAME10",
        color="Crime_Count",
        featureidkey="properties.NAME10",
        hover_name="NAME10",
        color_continuous_scale="YlOrRd",
        projection="mercator",
        title=f"Crime Incidents by County — {selected_year_map} · {selected_crime_map}",
        labels={"Crime_Count": "Number of Crimes"},
    )
    fig_map.update_geos(fitbounds="locations", visible=False)
    fig_map.update_layout(margin={"r": 0, "t": 50, "l": 0, "b": 0}, height=600)

    st.plotly_chart(fig_map, use_container_width=True)

    with st.expander("📋 Show raw county data"):
        st.dataframe(
            merged[["NAME10", "Crime_Count"]].rename(columns={"NAME10": "County"}).sort_values(
                "Crime_Count", ascending=False
            ),
            use_container_width=True,
        )



#---------Tab 2 Crime vs Poverty rates graph--------------
elif tab_choice == "📈 Crime & Poverty Trends":
    st.header("📈 Crime Trends & Poverty Guidelines Over Time")

    # Prepare crime data
    arrest_melted2 = arrest.melt(
        id_vars=["YEAR"],
        value_vars=CRIME_COLS,
        var_name="Crime_Type",
        value_name="Crime_Count",
    )
    crime_agg = (
        arrest_melted2.groupby(["YEAR", "Crime_Type"])["Crime_Count"]
        .sum()
        .reset_index()
        .rename(columns={"YEAR": "Year"})
    )

    # Prepare poverty data
    econo_melted = econ.melt(id_vars=["Family_Size"], var_name="Year", value_name="Poverty_Guideline")
    econo_melted["Year"] = pd.to_numeric(econo_melted["Year"])

    common_years = sorted(set(crime_agg["Year"].unique()) & set(econo_melted["Year"].unique()))
    crime_agg    = crime_agg[crime_agg["Year"].isin(common_years)].sort_values("Year")
    econo_melted = econo_melted[econo_melted["Year"].isin(common_years)].sort_values("Year")

    unique_crime_types  = sorted(crime_agg["Crime_Type"].unique())
    unique_family_sizes = sorted(econo_melted["Family_Size"].unique())

    # Sidebar controls
    selected_crime_trend   = st.sidebar.selectbox("Crime Type", unique_crime_types, index=0)
    selected_family_size   = st.sidebar.selectbox(
        "Poverty Family Size",
        [int(f) for f in unique_family_sizes],
        index=0,
    )

    crime_colors   = px.colors.qualitative.Dark24
    poverty_colors = px.colors.sequential.Plasma

    df_crime = crime_agg[crime_agg["Crime_Type"] == selected_crime_trend]
    df_econ  = econo_melted[econo_melted["Family_Size"] == selected_family_size]
    c_idx    = unique_crime_types.index(selected_crime_trend)
    p_idx    = list(unique_family_sizes).index(selected_family_size)

    fig_trend = go.Figure()

    fig_trend.add_trace(go.Scatter(
        x=df_crime["Year"],
        y=df_crime["Crime_Count"],
        mode="lines+markers",
        name=f"Crime: {selected_crime_trend}",
        yaxis="y1",
        line=dict(color=crime_colors[c_idx % len(crime_colors)]),
        marker=dict(symbol="circle", size=8),
        hovertemplate="<b>Year</b>: %{x}<br><b>Crime Count</b>: %{y:,}<extra></extra>",
    ))

    fig_trend.add_trace(go.Scatter(
        x=df_econ["Year"],
        y=df_econ["Poverty_Guideline"],
        mode="lines+markers",
        name=f"Poverty: Family Size {selected_family_size}",
        yaxis="y2",
        line=dict(dash="dot", color=poverty_colors[p_idx % len(poverty_colors)]),
        marker=dict(symbol="cross", size=8),
        hovertemplate="<b>Year</b>: %{x}<br><b>Poverty Guideline</b>: $%{y:,}<extra></extra>",
    ))

    fig_trend.update_layout(
        title="Crime Trends and Poverty Guidelines Over Time (2014–2024)",
        xaxis=dict(title="Year", showline=True, linewidth=1, linecolor="black", mirror=True),
        yaxis=dict(
            title=dict(text="Crime Count (Total Incidents)", font=dict(color="blue")),
            tickfont=dict(color="blue"),
            side="left",
            showline=True, linewidth=1, linecolor="blue",
        ),
        yaxis2=dict(
            title=dict(text="Poverty Guideline ($ per Year)", font=dict(color="red")),
            tickfont=dict(color="red"),
            overlaying="y",
            side="right",
            showline=True, linewidth=1, linecolor="red",
        ),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=550,
        margin=dict(l=50, r=60, t=80, b=50),
    )

    st.plotly_chart(fig_trend, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        with st.expander("📋 Crime data"):
            st.dataframe(df_crime.rename(columns={"Year": "Year", "Crime_Count": "Incidents"}), use_container_width=True)
    with col_b:
        with st.expander("📋 Poverty data"):
            st.dataframe(df_econ.rename(columns={"Year": "Year", "Poverty_Guideline": "Guideline ($)"}), use_container_width=True)


#---------Tab 3 Interactive Network Graph--------------

elif tab_choice == "🕸️ Network Graph":
    st.header("🕸️ Crime Network — Race · Gender · Age · County · Crime Type")

    all_net_years = sorted(arrest["YEAR"].unique())
    selected_year_net = st.sidebar.selectbox("Year", all_net_years, index=list(all_net_years).index(2020))

    arrest_melted3 = arrest.melt(
        id_vars=["YEAR", "GENDER", "RACE", "AGE_GROUP", "COUNTY"],
        value_vars=CRIME_COLS,
        var_name="Crime_Type",
        value_name="Crime_Count",
    )
    arrest_filtered = arrest_melted3[arrest_melted3["YEAR"] == selected_year_net].copy()

    network_options = """
    var options = {
      "nodes": {"font": {"size": 12, "color": "white"}, "scaling": {"min": 10, "max": 30}},
      "edges": {"font": {"size": 10, "color": "white"}, "width": 1, "hoverWidth": 0.5,
                 "selectionWidth": 1.5, "smooth": {"type": "dynamic"}},
      "physics": {
        "forceAtlas2Based": {"gravitationalConstant": -50, "centralGravity": 0.005,
                              "springLength": 100, "springConstant": 0.05},
        "minVelocity": 0.75, "solver": "forceAtlas2Based", "timestep": 0.35
      }
    }
    """

    with st.spinner("Building network graph…"):
        net = Network(
            notebook=False, height="750px", width="100%",
            bgcolor="#222222", font_color="white", cdn_resources="in_line", heading=""
        )

        # Race nodes
        race_total = arrest_filtered.groupby("RACE")["Crime_Count"].sum().reset_index()
        max_rc = race_total["Crime_Count"].max() or 1
        for _, row in race_total.iterrows():
            size = (row["Crime_Count"] / max_rc) * 15 + 10
            net.add_node(f'race_{row["RACE"].replace(" ","_")}', label=row["RACE"],
                         title=f'Race: {row["RACE"]}\nTotal: {int(row["Crime_Count"]):,}',
                         color="#98FB98", size=size)

        # Gender nodes
        gender_total = arrest_filtered.groupby("GENDER")["Crime_Count"].sum().reset_index()
        max_gc = gender_total["Crime_Count"].max() or 1
        for _, row in gender_total.iterrows():
            size = (row["Crime_Count"] / max_gc) * 15 + 10
            net.add_node(f'gender_{row["GENDER"].replace(" ","_")}', label=row["GENDER"],
                         title=f'Gender: {row["GENDER"]}\nTotal: {int(row["Crime_Count"]):,}',
                         color="#ADD8E6", size=size)

        # Age group nodes
        age_total = arrest_filtered.groupby("AGE_GROUP")["Crime_Count"].sum().reset_index()
        max_ag = age_total["Crime_Count"].max() or 1
        for _, row in age_total.iterrows():
            size = (row["Crime_Count"] / max_ag) * 15 + 10
            net.add_node(f'age_{row["AGE_GROUP"].replace(" ","_")}', label=row["AGE_GROUP"],
                         title=f'Age: {row["AGE_GROUP"]}\nTotal: {int(row["Crime_Count"]):,}',
                         color="#87CEEB", size=size)

        # County nodes
        county_total = arrest_filtered.groupby("COUNTY")["Crime_Count"].sum().reset_index()
        max_cc = county_total["Crime_Count"].max() or 1
        for _, row in county_total.iterrows():
            size = (row["Crime_Count"] / max_cc) * 15 + 10
            net.add_node(f'county_{row["COUNTY"].replace(" ","_")}', label=row["COUNTY"],
                         title=f'County: {row["COUNTY"]}\nTotal: {int(row["Crime_Count"]):,}',
                         color="#FFD700", size=size)

        # Crime type nodes
        for c in arrest_filtered["Crime_Type"].unique():
            net.add_node(f'crime_{c.replace(" ","_")}', label=c,
                         title=f"Crime Type: {c}", color="#FFA500", size=15)

        # Edges: Race -> Age Group
        ra_agg = arrest_filtered.groupby(["RACE","AGE_GROUP"])["Crime_Count"].sum().reset_index()
        max_ra = ra_agg["Crime_Count"].max() or 1
        for _, r in ra_agg.iterrows():
            if r["Crime_Count"] > 0:
                net.add_edge(f'race_{r["RACE"].replace(" ","_")}',
                             f'age_{r["AGE_GROUP"].replace(" ","_")}',
                             value=(r["Crime_Count"]/max_ra)*3+0.5,
                             title=f'{r["RACE"]} × {r["AGE_GROUP"]}: {int(r["Crime_Count"]):,}',
                             color="#3CB371")

        # Edges: Gender -> Age Group
        ga_agg = arrest_filtered.groupby(["GENDER","AGE_GROUP"])["Crime_Count"].sum().reset_index()
        max_ga = ga_agg["Crime_Count"].max() or 1
        for _, r in ga_agg.iterrows():
            if r["Crime_Count"] > 0:
                net.add_edge(f'gender_{r["GENDER"].replace(" ","_")}',
                             f'age_{r["AGE_GROUP"].replace(" ","_")}',
                             value=(r["Crime_Count"]/max_ga)*3+0.5,
                             title=f'{r["GENDER"]} × {r["AGE_GROUP"]}: {int(r["Crime_Count"]):,}',
                             color="#6A5ACD")

        # Edges: Age Group -> County
        ca_agg = arrest_filtered.groupby(["COUNTY","AGE_GROUP"])["Crime_Count"].sum().reset_index()
        max_ca = ca_agg["Crime_Count"].max() or 1
        for _, r in ca_agg.iterrows():
            if r["Crime_Count"] > 0:
                net.add_edge(f'age_{r["AGE_GROUP"].replace(" ","_")}',
                             f'county_{r["COUNTY"].replace(" ","_")}',
                             value=(r["Crime_Count"]/max_ca)*3+0.5,
                             title=f'{r["AGE_GROUP"]} in {r["COUNTY"]}: {int(r["Crime_Count"]):,}',
                             color="#ADD8E6")

        # Edges: County -> Crime Type
        ct_agg = arrest_filtered.groupby(["COUNTY","Crime_Type"])["Crime_Count"].sum().reset_index()
        max_ct = ct_agg["Crime_Count"].max() or 1
        for _, r in ct_agg.iterrows():
            if r["Crime_Count"] > 0:
                net.add_edge(f'county_{r["COUNTY"].replace(" ","_")}',
                             f'crime_{r["Crime_Type"].replace(" ","_")}',
                             value=(r["Crime_Count"]/max_ct)*5+0.5,
                             title=f'{r["Crime_Type"]} in {r["COUNTY"]}: {int(r["Crime_Count"]):,}',
                             color="#FF4500")

        net.set_options(network_options)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
            tmp_path = tmp.name
        net.write_html(tmp_path)
        #net.show(tmp_path) didn't work
        with open(tmp_path, "r") as f:
            html_content = f.read()
        os.unlink(tmp_path)

    # Legend
    legend_cols = st.columns(5)
    legend_items = [
        ("#98FB98", "Race"),
        ("#ADD8E6", "Gender / Age-County"),
        ("#87CEEB", "Age Group"),
        ("#FFD700", "County"),
        ("#FFA500", "Crime Type"),
    ]
    for col, (color, label) in zip(legend_cols, legend_items):
        col.markdown(
            f'<span style="display:inline-block;width:14px;height:14px;border-radius:50%;'
            f'background:{color};margin-right:6px;vertical-align:middle"></span>{label}',
            unsafe_allow_html=True,
        )

    components.html(html_content, height=780, scrolling=False)
