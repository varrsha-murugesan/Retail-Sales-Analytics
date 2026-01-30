from fastapi import FastAPI
from pydantic import BaseModel
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor

print("✅ discount_api.py loaded successfully")

app = FastAPI(title="Discount Optimization API (V2)")

# -----------------------------
# Load dataset
# -----------------------------
df = pd.read_csv("sales_history.csv")

# -----------------------------
# Features + Targets (UPDATED)
# -----------------------------
FEATURES = [
    "product",
    "category",
    "region",
    "base_price",
    "discount_pct",
    "competitor_price"
]

X = df[FEATURES]

y_profit = df["profit"]
y_sales = df["units_sold"]

# -----------------------------
# Preprocessing
# -----------------------------
cat_cols = ["product", "category", "region"]
num_cols = ["base_price", "discount_pct", "competitor_price"]

preprocess = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ("num", "passthrough", num_cols),
    ]
)

# -----------------------------
# Models
# -----------------------------
profit_model = Pipeline([
    ("prep", preprocess),
    ("model", RandomForestRegressor(n_estimators=250, random_state=42))
])

sales_model = Pipeline([
    ("prep", preprocess),
    ("model", RandomForestRegressor(n_estimators=250, random_state=42))
])

# Train once when API starts
profit_model.fit(X, y_profit)
sales_model.fit(X, y_sales)

print("✅ Models trained and API is ready!")

# -----------------------------
# Request schema (UPDATED)
# -----------------------------
class PredictRequest(BaseModel):
    product: str
    category: str
    region: str
    base_price: float
    discount_pct: float
    competitor_price: float


@app.get("/")
def home():
    return {"message": "Discount Optimization API (V2) is running 🚀"}


@app.post("/predict")
def predict(req: PredictRequest):
    input_df = pd.DataFrame([req.dict()])

    pred_profit = float(profit_model.predict(input_df)[0])
    pred_units = float(sales_model.predict(input_df)[0])

    # price competitiveness insight
    our_price = req.base_price * (1 - req.discount_pct / 100)
    if our_price > req.competitor_price:
        price_alert = "Expensive"
    else:
        price_alert = "Competitive"

    return {
        "predicted_profit": round(pred_profit, 2),
        "predicted_units_sold": round(pred_units, 2),
        "our_price": round(our_price, 2),
        "price_alert": price_alert
    }
