# app.py
from flask import Flask, render_template, request, jsonify
import joblib, pickle
import pandas as pd
import math

app = Flask(__name__)

# ---- load model and encoders ----
try:
    model = joblib.load("model.joblib")
    with open("encoders.pkl", "rb") as f:
        encoders = pickle.load(f)
    with open("model_columns.pkl", "rb") as f:
        model_columns = pickle.load(f)
    print("Model and encoders loaded successfully.")
except Exception as e:
    print("Error loading model files:", e)

target_le = encoders["target"]

# simple speed map by congestion (km/h)
SPEED_MAP = {"High": 12.0, "Medium": 30.0, "Low": 60.0}

# basic route alternatives (demo)
ROUTE_ALTS = {
    "Lekki-Ajah": [
        {"name": "Lekki-Ajah Main", "distance_km": 15},
        {"name": "Lekki-Ajah Coastal", "distance_km": 18},
        {"name": "Lekki-Ajah Via Link", "distance_km": 22}
    ],
    "Ikeja-Ojota": [
        {"name": "Ikeja-Ojota Express", "distance_km": 12},
        {"name": "Ikeja-Ojota Local", "distance_km": 14}
    ],
    "CMS-Yaba": [
        {"name": "CMS-Yaba Main", "distance_km": 8},
        {"name": "CMS-Yaba Circuit", "distance_km": 12}
    ],
    # add more route keys if your CSV has them
}

# util functions
def label_index_to_text(idx):
    return target_le.inverse_transform([idx])[0]

def make_sample(route, time_of_day, day_type, distance, avg_speed):
    # encode strings to the numeric encodings used in training
    r_enc = encoders["Route"].transform([route])[0]
    t_enc = encoders["TimeOfDay"].transform([time_of_day])[0]
    d_enc = encoders["DayOfWeek"].transform([day_type])[0]
    travel_time = round((distance/avg_speed)*60, 1) if avg_speed>0 else 0.0
    sample = pd.DataFrame([{
        "Route": r_enc,
        "TimeOfDay": t_enc,
        "DayOfWeek": d_enc,
        "Distance(km)": distance,
        "AvgSpeed(km/h)": avg_speed,
        "TravelTime(mins)": travel_time,
        "FuelCost(Naira)": round((distance/12)*650, 2),
        "CO2(kg)": round((distance/12)*2.3, 2)
    }])
    # ensure column order
    sample = sample[model_columns]
    return sample

def predict_congestion(route, time_of_day, day_type, distance, avg_speed):
    sample = make_sample(route, time_of_day, day_type, distance, avg_speed)
    pred_idx = model.predict(sample)[0]
    return label_index_to_text(pred_idx)

def estimate_time(distance_km, congestion_label):
    speed = SPEED_MAP.get(congestion_label, 30.0)
    time_mins = (distance_km / speed) * 60.0
    return round(time_mins, 1)

def recommend_route(route_key, time_of_day, day_type, avg_speed, vehicle_type="Normal"):
    alts = ROUTE_ALTS.get(route_key)
    if not alts:
        # fallback: treat route as single path with distance parameter
        congestion = predict_congestion(route_key, time_of_day, day_type, avg_speed, avg_speed)
        t = estimate_time(avg_speed, congestion)
        return {"route_name": route_key, "distance_km": avg_speed, "congestion": congestion, "est_time_mins": t}, []
    results = []
    for alt in alts:
        cong = predict_congestion(route_key, time_of_day, day_type, alt["distance_km"], avg_speed)
        t = estimate_time(alt["distance_km"], cong)
        results.append({"route_name": alt["name"], "distance_km": alt["distance_km"], "congestion": cong, "est_time_mins": t})
    # emergency: prioritize lower congestion first, then time
    if vehicle_type.lower() == "emergency":
        order = {"Low": 0, "Medium": 1, "High": 2}
        results_sorted = sorted(results, key=lambda r: (order.get(r["congestion"], 9), r["est_time_mins"]))
    else:
        results_sorted = sorted(results, key=lambda r: r["est_time_mins"])
    return results_sorted[0], results_sorted

# ---- routes ----
@app.route("/")
def index():
    # pass route/time/day options to the frontend from the encoders (original classes)
    # inverse_transform to show readable labels
    routes = encoders["Route"].classes_.tolist()
    times = encoders["TimeOfDay"].classes_.tolist()
    days = encoders["DayOfWeek"].classes_.tolist()
    return render_template("index.html", routes=routes, times=times, days=days)
@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    routes = encoders["Route"].classes_.tolist()
    times = encoders["TimeOfDay"].classes_.tolist()
    days = encoders["DayOfWeek"].classes_.tolist()
    return render_template("dashboard.html", routes=routes, times=times, days=days)

@app.route("/help")
def help():
    return render_template("help.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        message = request.form["message"]
        print(f"📩 Message from {name} ({email}): {message}")
        return render_template("contact.html", success=True)
    return render_template("contact.html")

@app.route("/api/predict", methods=["POST"])
def api_predict():
    body = request.json
    route = body.get("route")
    time_of_day = body.get("time_of_day")
    day_type = body.get("day_type")
    avg_speed = float(body.get("avg_speed", 25))
    distance = float(body.get("distance", 15))
    vehicle_type = body.get("vehicle_type", "Normal")

    now = predict_congestion(route, time_of_day, day_type, distance, avg_speed)
    # quick forecast: shift time slot (simple rotate)
    time_map = {"Morning":"Afternoon","Afternoon":"Evening","Evening":"Night","Night":"Morning"}
    future_time = time_map.get(time_of_day, time_of_day)
    future = predict_congestion(route, future_time, day_type, distance, avg_speed)

    best, all_opts = recommend_route(route, time_of_day, day_type, avg_speed, vehicle_type)

    response = {
        "now": now,
        "future": future,
        "recommended": best,
        "alternatives": all_opts
    }
    return jsonify(response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
