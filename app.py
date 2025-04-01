# app.py

import streamlit as st
import pandas as pd
import numpy as np

# Title
st.title("Modélisation AGA - ManCo : Impact Cash & IFRS")

# 1. Sidebar inputs
st.sidebar.header("Paramètres Globaux")

n_agents = st.sidebar.number_input("Nombre d'agents", value=6, min_value=1)
P = st.sidebar.number_input("Nombre d'années de simulation", value=5, min_value=1)
M = st.sidebar.number_input("Montant brut renoncé (en €)", value=100_000, step=10_000)
rho_threshold = st.sidebar.slider("Seuil de rentabilité (ρ)", 0.0, 1.0, 0.3, 0.05)
price_share = st.sidebar.number_input("Prix d'une action AGA (en €)", value=10)
tau_charges_brut = st.sidebar.slider("Taux charges patronales sur brut (%)", 0.0, 1.0, 0.40, 0.01)
tau_charges_aga = st.sidebar.slider("Taux charges patronales sur AGA (%)", 0.0, 1.0, 0.30, 0.01)
IS = st.sidebar.slider("Taux IS (%)", 0.0, 1.0, 0.25, 0.01)
IRPP = st.sidebar.slider("Taux IRPP marginal (%)", 0.0, 1.0, 0.45, 0.01)
vesting_period = st.sidebar.number_input("Période d'acquisition (vested) AGA (ans)", value=2, min_value=1)

st.write("""
Ce modèle calcule, pour chaque année, le nombre d'actions gratuites attribuées, 
l'économie de cash-flow liée au renoncement du variable, le coût patronal sur AGA, 
et l'impact IFRS (simplifié). 
""")

# 2. Input for each agent's rentabilité per year
st.subheader("Rentabilité (ρᵗ) par agent et par année")

# We create an editable table for ρᵗ
# We'll store them in a DataFrame
agents_range = range(1, n_agents+1)
years_range = range(1, P+1)

default_rho = 0.35  # default example

# We'll create a data structure to hold ρᵗ
rho_input = {}
for ag in agents_range:
    row = []
    for y in years_range:
        row.append(default_rho)
    rho_input[ag] = row

# Convert to DataFrame for display/edit
df_rho = pd.DataFrame(rho_input).transpose()
df_rho.columns = [f"Year {y}" for y in years_range]
df_rho.index = [f"Agent {a}" for a in agents_range]

df_rho_edited = st.data_editor(df_rho, key="rho_editor")

st.write("Table de rentabilité (ρᵗ) saisie :")
st.dataframe(df_rho_edited)

# 3. Calcul
results = []

for ag_idx, ag_name in enumerate(df_rho_edited.index):
    agent_id = ag_idx + 1
    for col_idx, col_name in enumerate(df_rho_edited.columns):
        year = col_idx + 1
        rho_t = df_rho_edited.loc[ag_name, col_name]
        
        if rho_t <= rho_threshold:
            factor = 1.0
        else:
            factor = 1.0 + rho_t
        
        # Valeur AGA "octroyée" (pas investi en cash par l'agent)
        aga_value = M * factor
        
        # Nombre d'actions
        if price_share > 0:
            aga_shares = aga_value / price_share
        else:
            aga_shares = 0
        
        # IFRS cost example: spread over vesting_period
        ifrs_cost_per_year = aga_value / vesting_period
        
        # Economie de cash (avant IS) = M + charges patronales sur M
        # On suppose qu'on évite M*(1+tau_charges_brut)
        # Potentially, on applique l'IS si on veut le net post impôt
        cash_saving_gross = M * (1 + tau_charges_brut)
        cash_saving_netIS = cash_saving_gross * (1 - IS)
        
        # AGA cost at T+2 : charges patronales AGA
        aga_charges_future = aga_value * tau_charges_aga
        aga_charges_future_netIS = aga_charges_future * (1 - IS)
        
        # Impact net sur la société (simplifié) en "année t"
        # Sur l'année t: gain = cash_saving_netIS
        # Sur l'année t+2: - aga_charges_future_netIS
        # (We might keep track in a 2D structure or simply show it as 'future cost'.)
        
        # Impact net sur salarié
        #  - S'il renonce à M brut, il "perd" M*(1 - IRPP) net
        #  + Il reçoit aga_shares => potentiel de plus-value
        #  (Simplif : on calcule la "delta net" = -M*(1-IRPP) + aga_value*(1 -30%?)...
        #   This can be refined.)
        
        # We'll store results in a list
        results.append({
            "Agent": agent_id,
            "Year": year,
            "rho_t": rho_t,
            "factor": round(factor, 3),
            "AGA_value": round(aga_value, 2),
            "AGA_shares": round(aga_shares, 2),
            "IFRS_cost_per_year": round(ifrs_cost_per_year, 2),
            "CashSaving_Gross": round(cash_saving_gross, 2),
            "CashSaving_NetIS": round(cash_saving_netIS, 2),
            "AGA_Charges_Future": round(aga_charges_future, 2),
            "AGA_Charges_Future_NetIS": round(aga_charges_future_netIS, 2)
        })

df_out = pd.DataFrame(results)
df_out = df_out[["Agent","Year","rho_t","factor","AGA_value","AGA_shares","IFRS_cost_per_year",
                 "CashSaving_Gross","CashSaving_NetIS",
                 "AGA_Charges_Future","AGA_Charges_Future_NetIS"]]
df_out.sort_values(["Agent","Year"], inplace=True)

st.subheader("Résultats - par Agent et par Année")
st.dataframe(df_out, use_container_width=True)

# Quick summary
st.subheader("Synthèse par Année (somme sur tous les agents)")
grouped = df_out.groupby("Year").agg({
    "AGA_value": "sum",
    "AGA_shares": "sum",
    "IFRS_cost_per_year": "sum",
    "CashSaving_Gross": "sum",
    "CashSaving_NetIS": "sum",
    "AGA_Charges_Future": "sum",
    "AGA_Charges_Future_NetIS": "sum"
}).reset_index()
st.dataframe(grouped)

import altair as alt

st.subheader("Graphique: Economie de cash (Net IS) vs. Coût charges AGA (Net IS)")

c1 = alt.Chart(grouped).mark_bar(color='green').encode(
    x='Year:O',
    y='CashSaving_NetIS',
    tooltip=['CashSaving_NetIS']
).properties(
    width=400,
    title='CashSaving_NetIS par année'
)

c2 = alt.Chart(grouped).mark_bar(color='red').encode(
    x='Year:O',
    y='AGA_Charges_Future_NetIS',
    tooltip=['AGA_Charges_Future_NetIS']
).properties(
    width=400,
    title='AGA_Charges_Future_NetIS (coût t+2) par année'
)

st.altair_chart((c1 | c2))

st.write("""
> **Note** : 
> - "IFRS_cost_per_year" est une approche simplifiée (lissage sur la période de vesting).
> - "AGA_Charges_Future" représente le coût de charges patronales (ex. 30%) qui frappera la valeur des AGA au moment de l'acquisition (T+2).
> - "CashSaving_NetIS" = (M + M*tau_charges_brut)*(1-IS).
> 
> L'utilisateur peut affiner ces calculs selon la réglementation précise (franchise, abattement, etc.).
""")
