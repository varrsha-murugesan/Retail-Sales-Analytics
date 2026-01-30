import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="Discount Optimization Tool (V3)", layout="wide")

API_URL = "http://127.0.0.1:8002/predict"

# -----------------------------
# Product Catalog
# -----------------------------
PRODUCTS = {
    "Laptop": {"category": "Electronics", "base_price": 50000},
    "Gaming Laptop": {"category": "Electronics", "base_price": 75000},
    "Mobile": {"category": "Electronics", "base_price": 20000},
    "Premium Mobile": {"category": "Electronics", "base_price": 40000},
    "Tablet": {"category": "Electronics", "base_price": 25000},
    "Smartwatch": {"category": "Electronics", "base_price": 8000},
    "Headphones": {"category": "Electronics", "base_price": 3000},
    "Bluetooth Speaker": {"category": "Electronics", "base_price": 4500},

    "Washing Machine": {"category": "Appliances", "base_price": 30000},
    "Refrigerator": {"category": "Appliances", "base_price": 45000},
    "Microwave Oven": {"category": "Appliances", "base_price": 15000},
    "Air Conditioner": {"category": "Appliances", "base_price": 42000},

    "Power Bank": {"category": "Accessories", "base_price": 2500},
    "Wireless Mouse": {"category": "Accessories", "base_price": 1200},
    "Keyboard": {"category": "Accessories", "base_price": 1800},

    "Fitness Band": {"category": "Wearables", "base_price": 3500},
    "Smart Glasses": {"category": "Wearables", "base_price": 12000},
}

REGIONS = ["North", "South", "East", "West", "Central"]

# -----------------------------
# Helper: call API
# -----------------------------
def call_api(product, category, region, base_price, discount_pct, competitor_price):
    payload = {
        "product": product,
        "category": category,
        "region": region,
        "base_price": float(base_price),
        "discount_pct": float(discount_pct),
        "competitor_price": float(competitor_price)
    }
    r = requests.post(API_URL, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

# -----------------------------
# UI Header
# -----------------------------
st.title("📊 Discount Optimization Tool (V3)")
st.caption("Monte Carlo risk simulation for profit uncertainty + competitor pricing effect")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("🎛 Controls")

product = st.sidebar.selectbox("Select Product", list(PRODUCTS.keys()))
category = PRODUCTS[product]["category"]
base_price = PRODUCTS[product]["base_price"]

discount_pct = st.sidebar.slider("Discount (%)", 0, 50, 15, 1)

# competitor price input
default_comp_price = base_price * (1 - discount_pct / 100) * 0.98
competitor_price = st.sidebar.number_input(
    "Competitor Price",
    min_value=1.0,
    value=float(round(default_comp_price, 2)),
    step=50.0
)

st.sidebar.subheader("🎲 Monte Carlo Settings")
n_sims = st.sidebar.slider("Number of Simulations", 50, 500, 150, 50)
volatility = st.sidebar.slider("Market Volatility (%)", 0.0, 30.0, 10.0, 1.0)

run = st.sidebar.button("🚀 Run Risk Simulation")

# -----------------------------
# Main
# -----------------------------
if run:
    st.success("✅ Simulation completed!")

    profits = []
    units = []
    regions_used = []
    our_prices = []
    alerts = []

    # simulate competitor price fluctuations
    std = competitor_price * (volatility / 100)

    for i in range(n_sims):
        sim_region = np.random.choice(REGIONS)
        sim_comp_price = float(max(1.0, np.random.normal(competitor_price, std)))

        out = call_api(product, category, sim_region, base_price, discount_pct, sim_comp_price)

        profits.append(out["predicted_profit"])
        units.append(out["predicted_units_sold"])
        regions_used.append(sim_region)
        our_prices.append(out.get("our_price", 0))
        alerts.append(out.get("price_alert", "No Alert"))

    sim_df = pd.DataFrame({
        "sim_id": range(1, n_sims + 1),
        "region": regions_used,
        "predicted_profit": profits,
        "predicted_units_sold": units,
        "our_price": our_prices
    })

    # KPIs
    avg_profit = sim_df["predicted_profit"].mean()
    best_profit = sim_df["predicted_profit"].max()
    worst_profit = sim_df["predicted_profit"].min()
    avg_units = sim_df["predicted_units_sold"].mean()
    loss_prob = (sim_df["predicted_profit"] < 0).mean() * 100

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Expected Profit (Avg)", f"{avg_profit:,.2f}")
    c2.metric("📦 Expected Units (Avg)", f"{avg_units:,.2f}")
    c3.metric("⚠️ Loss Probability", f"{loss_prob:.1f}%")
    c4.metric("📉 Worst Case Profit", f"{worst_profit:,.2f}")

    st.divider()

    # -----------------------------
    # Profit Distribution Histogram
    # -----------------------------
    st.subheader("📊 Profit Distribution (Risk Curve)")

    hist, bin_edges = np.histogram(sim_df["predicted_profit"], bins=20)

    hist_df = pd.DataFrame({
        "Profit Range": [f"{bin_edges[i]:.0f} to {bin_edges[i+1]:.0f}" for i in range(len(hist))],
        "Count": hist
    })

    st.bar_chart(hist_df.set_index("Profit Range"))

    st.divider()

    # -----------------------------
    # Profit Trend
    # -----------------------------
    st.subheader("📈 Profit Simulation Trend")
    st.line_chart(sim_df.set_index("sim_id")["predicted_profit"])

    st.divider()

    # -----------------------------
    # Region wise Avg Profit
    # -----------------------------
    st.subheader("🌍 Region-wise Avg Profit")
    region_avg = sim_df.groupby("region")["predicted_profit"].mean().sort_values(ascending=False)
    st.bar_chart(region_avg)

    st.divider()

    # -----------------------------
    # Alert Summary
    # -----------------------------
    st.subheader("🚨 Pricing Alerts Summary")
    alert_counts = pd.Series(alerts).value_counts()
    st.write(alert_counts)

    st.divider()

    # -----------------------------
    # Table
    # -----------------------------
    st.subheader("📋 Simulation Table (Sample)")
    st.dataframe(sim_df.head(30), use_container_width=True)

else:
    st.info("⬅️ Select inputs and click **Run Risk Simulation**.")
