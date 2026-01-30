import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Discount Optimization Tool", layout="wide")

# 🔥 API URL (make sure this matches your FastAPI port)
API_URL = "http://127.0.0.1:8001/predict"

# -----------------------------
# Product Catalog (dropdown + base price auto)
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
def call_api(product, category, region, base_price, discount_pct):
    payload = {
        "product": product,
        "category": category,
        "region": region,
        "base_price": float(base_price),
        "discount_pct": float(discount_pct)
    }
    r = requests.post(API_URL, json=payload, timeout=10)
    r.raise_for_status()
    return r.json()

# -----------------------------
# UI
# -----------------------------
st.title("📊 Discount Optimization Decision Tool")
st.caption("Select product + discount → get predicted profit & sales + curves + region insights")

st.sidebar.header("🎛 Controls")

product = st.sidebar.selectbox("Select Product", list(PRODUCTS.keys()))
category = PRODUCTS[product]["category"]
base_price = PRODUCTS[product]["base_price"]

discount_pct = st.sidebar.slider("Discount (%)", 0, 50, 10, 1)

st.sidebar.info(f"📌 Category: {category}")
st.sidebar.info(f"💰 Base Price: ₹{base_price:,.0f}")

run = st.sidebar.button("🔮 Predict")

# -----------------------------
# Main Content
# -----------------------------
if run:
    st.success("✅ Predictions Generated!")

    # ----------------------------------------------------
    # 1) Average prediction (across all regions)
    # ----------------------------------------------------
    profits = []
    units = []

    for reg in REGIONS:
        out = call_api(product, category, reg, base_price, discount_pct)
        profits.append(out["predicted_profit"])
        units.append(out["predicted_units_sold"])

    avg_profit = sum(profits) / len(profits)
    avg_units = sum(units) / len(units)

    c1, c2 = st.columns(2)
    c1.metric("💰 Predicted Profit (Avg across regions)", f"{avg_profit:,.2f}")
    c2.metric("📦 Predicted Units Sold (Avg across regions)", f"{avg_units:,.2f}")

    st.divider()

    # ----------------------------------------------------
    # 2) Region-wise Profit Graph (for selected discount)
    # ----------------------------------------------------
    st.subheader("🌍 Region-wise Profit (Selected Product + Discount)")

    region_df = pd.DataFrame({
        "Region": REGIONS,
        "Predicted Profit": profits,
        "Predicted Units Sold": units
    })

    st.bar_chart(region_df.set_index("Region")["Predicted Profit"])

    st.divider()

    # ----------------------------------------------------
    # 3) Discount Curves (Profit & Units across discounts)
    # ----------------------------------------------------
    st.subheader("📈 Discount Impact Curves (Predicted)")

    discount_range = list(range(0, 51, 5))
    curve_profit = []
    curve_units = []

    for d in discount_range:
        p_list = []
        u_list = []
        for reg in REGIONS:
            out = call_api(product, category, reg, base_price, d)
            p_list.append(out["predicted_profit"])
            u_list.append(out["predicted_units_sold"])

        curve_profit.append(sum(p_list) / len(p_list))
        curve_units.append(sum(u_list) / len(u_list))

    curve_df = pd.DataFrame({
        "Discount %": discount_range,
        "Predicted Profit": curve_profit,
        "Predicted Units Sold": curve_units
    })

    colA, colB = st.columns(2)

    with colA:
        st.write("💰 Profit Curve")
        st.line_chart(curve_df.set_index("Discount %")["Predicted Profit"])

    with colB:
        st.write("📦 Units Sold Curve")
        st.line_chart(curve_df.set_index("Discount %")["Predicted Units Sold"])

    # ----------------------------------------------------
    # 4) Best Discount Recommendation (Max Profit)
    # ----------------------------------------------------
    best_row = curve_df.loc[curve_df["Predicted Profit"].idxmax()]
    best_discount = int(best_row["Discount %"])
    best_profit = best_row["Predicted Profit"]

    st.subheader("🏆 Recommended Best Discount (Max Profit)")
    st.info(f"✅ Best Discount: **{best_discount}%**  |  💰 Expected Profit: **{best_profit:,.2f}**")

else:
    st.info("⬅️ Select product + discount and click **Predict** to see results.")
