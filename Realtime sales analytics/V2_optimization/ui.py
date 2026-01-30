import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Discount Optimization Tool (V2)", layout="wide")

API_URL = "http://127.0.0.1:8001/predict"

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
# Helper: call API (UPDATED)
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
# Objective scoring
# -----------------------------
def objective_score(row, objective, alpha=0.6):
    if objective == "Max Profit":
        return row["Predicted Profit"]
    if objective == "Max Sales":
        return row["Predicted Units Sold"]
    return alpha * row["Profit_norm"] + (1 - alpha) * row["Units_norm"]

# -----------------------------
# UI Header
# -----------------------------
st.title("📊 Discount Optimization Decision Tool (V2)")
st.caption("Objective-based recommendation + constraints + competitor pricing + region insights")

# -----------------------------
# Sidebar Inputs
# -----------------------------
st.sidebar.header("🎛 Controls")

product = st.sidebar.selectbox("Select Product", list(PRODUCTS.keys()))
category = PRODUCTS[product]["category"]
base_price = PRODUCTS[product]["base_price"]

discount_preview = st.sidebar.slider("Discount (%) (Preview)", 0, 50, 10, 1)

# Competitor price input
default_competitor_price = base_price * (1 - (discount_preview / 100)) * 0.98
competitor_price = st.sidebar.number_input(
    "Competitor Price",
    min_value=1.0,
    value=float(round(default_competitor_price, 2)),
    step=50.0
)

objective = st.sidebar.selectbox(
    "Optimization Objective",
    ["Max Profit", "Max Sales", "Balanced"]
)

st.sidebar.subheader("⚙️ Constraints (Business Rules)")
max_discount_allowed = st.sidebar.slider("Max Discount Allowed (%)", 0, 50, 30, 1)
min_profit_required = st.sidebar.number_input("Minimum Profit Required", value=0.0, step=500.0)
min_units_required = st.sidebar.number_input("Minimum Units Sold Required", value=1.0, step=1.0)

alpha = 0.6
if objective == "Balanced":
    alpha = st.sidebar.slider("Balanced Weight (Profit priority)", 0.0, 1.0, 0.6, 0.05)

st.sidebar.info(f"📌 Category: {category}")
st.sidebar.info(f"💰 Base Price: ₹{base_price:,.0f}")

run = st.sidebar.button("🚀 Generate Recommendation")

# -----------------------------
# Main Logic
# -----------------------------
if run:
    st.success("✅ Recommendation Engine Executed!")

    discount_range = list(range(0, 51, 5))

    rows = []
    for d in discount_range:
        profits = []
        units = []

        for reg in REGIONS:
            out = call_api(product, category, reg, base_price, d, competitor_price)
            profits.append(out["predicted_profit"])
            units.append(out["predicted_units_sold"])

        rows.append({
            "Discount %": d,
            "Predicted Profit": sum(profits) / len(profits),
            "Predicted Units Sold": sum(units) / len(units)
        })

    curve_df = pd.DataFrame(rows)

    # Normalize for balanced scoring
    curve_df["Profit_norm"] = (curve_df["Predicted Profit"] - curve_df["Predicted Profit"].min()) / (
        curve_df["Predicted Profit"].max() - curve_df["Predicted Profit"].min() + 1e-9
    )
    curve_df["Units_norm"] = (curve_df["Predicted Units Sold"] - curve_df["Predicted Units Sold"].min()) / (
        curve_df["Predicted Units Sold"].max() - curve_df["Predicted Units Sold"].min() + 1e-9
    )

    curve_df["Score"] = curve_df.apply(lambda r: objective_score(r, objective, alpha), axis=1)

    # Apply constraints
    curve_df["Feasible"] = (
        (curve_df["Discount %"] <= max_discount_allowed) &
        (curve_df["Predicted Profit"] >= min_profit_required) &
        (curve_df["Predicted Units Sold"] >= min_units_required)
    )

    feasible_df = curve_df[curve_df["Feasible"] == True].copy()

    # KPI Cards
    c1, c2, c3 = st.columns(3)
    c1.metric("📌 Objective", objective)
    c2.metric("✅ Feasible Discounts", int(feasible_df.shape[0]))
    c3.metric("🏷 Max Discount Allowed", f"{max_discount_allowed}%")

    st.divider()

    # Recommendation
    st.subheader("🏆 Recommended Discount")

    recommended_discount = None

    if feasible_df.empty:
        st.error("⚠️ No feasible discounts found under your constraints. Try relaxing constraints.")
    else:
        best_row = feasible_df.loc[feasible_df["Score"].idxmax()]
        recommended_discount = int(best_row["Discount %"])

        # Call API once for competitor insight (using avg region - pick South as representative)
        insight = call_api(product, category, "South", base_price, recommended_discount, competitor_price)

        st.success(f"✅ Best Discount: **{recommended_discount}%**")

        k1, k2, k3 = st.columns(3)
        k1.metric("💰 Expected Profit", f"{best_row['Predicted Profit']:,.2f}")
        k2.metric("📦 Expected Units Sold", f"{best_row['Predicted Units Sold']:,.2f}")
        k3.metric("🛒 Our Price", f"₹{insight['our_price']:,.2f}")

        if insight["price_alert"] == "Expensive":
            st.warning("⚠️ Price Alert: You are more expensive than competitor for this strategy.")
        else:
            st.info("✅ Price Alert: Competitive pricing compared to competitor.")

    st.divider()

    # Region-wise graph
    st.subheader("🌍 Region-wise Profit Performance")

    if recommended_discount is not None:
        chosen_discount = st.selectbox(
            "Choose Discount for Region-wise Analysis",
            options=sorted(curve_df["Discount %"].tolist()),
            index=sorted(curve_df["Discount %"].tolist()).index(recommended_discount)
        )
    else:
        chosen_discount = st.selectbox(
            "Choose Discount for Region-wise Analysis",
            options=sorted(curve_df["Discount %"].tolist()),
            index=0
        )

    region_profits = []
    region_units = []

    for reg in REGIONS:
        out = call_api(product, category, reg, base_price, chosen_discount, competitor_price)
        region_profits.append(out["predicted_profit"])
        region_units.append(out["predicted_units_sold"])

    region_df = pd.DataFrame({
        "Region": REGIONS,
        "Predicted Profit": region_profits,
        "Predicted Units Sold": region_units
    })

    colR1, colR2 = st.columns(2)
    with colR1:
        st.write("💰 Profit by Region")
        st.bar_chart(region_df.set_index("Region")["Predicted Profit"])
    with colR2:
        st.write("📦 Units Sold by Region")
        st.bar_chart(region_df.set_index("Region")["Predicted Units Sold"])

    st.dataframe(region_df, use_container_width=True)

    st.divider()

    # Curves
    st.subheader("📈 Discount Impact Curves")

    colA, colB = st.columns(2)
    with colA:
        st.write("💰 Profit Curve")
        st.line_chart(curve_df.set_index("Discount %")["Predicted Profit"])
    with colB:
        st.write("📦 Units Sold Curve")
        st.line_chart(curve_df.set_index("Discount %")["Predicted Units Sold"])

else:
    st.info("⬅️ Select product + competitor price + objective + constraints, then click **Generate Recommendation**.")
