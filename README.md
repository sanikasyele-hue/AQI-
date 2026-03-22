# 🌬️ AQI Prediction System — Complete Edition
## Python, Django & Machine Learning | Final Year Project

---

## ✨ FEATURES
| Feature | Description | Login Required? |
|---|---|---|
| 🏠 Home — Predict AQI | Enter pollutant values → ML prediction | No |
| 📡 Real-Time AQI | Live data from Open-Meteo API | No |
| 🔮 Future Forecast | Predict next 24h / 7 days / 30 days | No |
| 📊 Admin Dashboard | Stats, charts, overview | ✅ Yes |
| 🔍 Search History | Browse all past AQI readings | ✅ Yes |
| 📈 Charts & Visualisations | Pie, line, scatter, radar charts | ✅ Yes |
| 📡 Manage Stations | Add IoT monitoring stations | ✅ Yes |
| 📋 All Readings | View/delete all records | ✅ Yes |
| 🔌 IoT API | ESP32/Arduino POST endpoint | API Key |

---

## 🚀 HOW TO RUN

### WINDOWS
```
Double-click SETUP_AND_RUN.bat
```

### MAC / LINUX
```bash
bash SETUP_AND_RUN.sh
```

### MANUAL STEPS
```bash
# 1. Install packages
pip install Django==4.2.7 scikit-learn==1.3.2 pandas==2.1.3 numpy==1.26.2 joblib==1.3.2

# 2. Train ML models (ONCE — takes ~2 mins)
python ml_model/train_models.py

# 3. Setup database
python manage.py makemigrations aqi_app
python manage.py migrate

# 4. Create admin user
python manage.py createsuperuser
# Enter: username=admin, password=Test@123

# 5. Start server
python manage.py runserver

# 6. Open browser → http://127.0.0.1:8000
```

---

## 🔑 LOGIN
| Username | Password |
|---|---|
| admin | Test@123 |

---

## 🌐 ALL URLs
| URL | Page |
|---|---|
| / | Home — AQI Prediction Form |
| /realtime/ | Live Real-Time AQI |
| /future/ | Future AQI Forecast |
| /login/ | Admin Login |
| /dashboard/ | Admin Dashboard |
| /search/ | Search History |
| /charts/ | Charts & Visualisations |
| /stations/ | Manage IoT Stations |
| /readings/ | All Readings |
| /api/iot/ | IoT API Endpoint |

---

## 🧠 ML MODELS

### Model 1 — Current AQI Classifier
- **Algorithm:** Random Forest (150 trees)
- **Input:** PM2.5, PM10, CO, SO₂, NO₂, O₃
- **Output:** Good / Moderate / Poor / Very Poor / Severe
- **Accuracy:** ~99%

### Model 2 — Future AQI Forecaster
- **Algorithm:** Gradient Boosting (time-series)
- **Input:** Last 24 hours AQI + time features
- **Output:** AQI for next 24h, 7 days, 30 days
- **Trained on:** 2 years of simulated hourly data

---

## 🔌 IoT INTEGRATION

### ESP32 Code: `iot_sensor_code/esp32_aqi_sensor.ino`

**Hardware needed:**
- ESP32 board (~₹500)
- SDS011 dust sensor — PM2.5 & PM10 (~₹800)
- MQ-7 gas sensor — CO (~₹150)
- MQ-135 gas sensor — NO₂, SO₂, O₃ (~₹150)

**How it works:**
```
Sensors → ESP32 reads values → ESP32 sends POST to /api/iot/
→ Django ML model predicts AQI → Saves to database → Shows on website
```

**Test the API manually:**
```bash
curl -X POST http://127.0.0.1:8000/api/iot/ \
  -H "Content-Type: application/json" \
  -d '{"pm25":45,"pm10":80,"co":1.2,"so2":30,"no2":50,"o3":70}'
```

**Response:**
```json
{
  "status": "success",
  "category": "Moderate",
  "aqi": 75,
  "advice": "Acceptable. Sensitive groups should take care.",
  "station": "IoT Device"
}
```

---

## ❓ TROUBLESHOOTING
| Problem | Solution |
|---|---|
| "ML Model not loaded" | Run `python ml_model/train_models.py` |
| "No module named django" | Run `pip install django` |
| Port in use | Run `python manage.py runserver 8080` |
| DB errors | Delete `db.sqlite3`, re-run makemigrations + migrate |
| Real-time shows demo data | No internet / API unavailable — demo data is shown |
