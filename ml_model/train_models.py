"""
============================================================
  AQI PREDICTION - TRAIN ALL ML MODELS
  Run: python ml_model/train_models.py
============================================================
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, mean_absolute_error
import joblib, os

SAVE_DIR = os.path.dirname(os.path.abspath(__file__))

print("\n" + "="*55)
print("  MODEL 1: AQI Classifier (Random Forest)")
print("="*55)
np.random.seed(42)
N = 3000

def make_sample(cat):
    r = {'Good':[(0,30),(0,50),(0,1.0),(0,40),(0,40),(0,50)],
         'Moderate':[(30,60),(50,100),(1,2),(40,80),(40,80),(50,100)],
         'Poor':[(60,90),(100,250),(2,10),(80,380),(80,180),(100,168)],
         'Very Poor':[(90,120),(250,350),(10,17),(380,800),(180,280),(168,208)],
         'Severe':[(120,250),(350,600),(17,34),(800,1600),(280,400),(208,400)]}[cat]
    return [np.random.uniform(*x) for x in r]

cats = ['Good','Moderate','Poor','Very Poor','Severe']
rows = []
for _ in range(N):
    c = np.random.choice(cats, p=[0.25,0.25,0.20,0.18,0.12])
    rows.append(make_sample(c)+[c])

df1 = pd.DataFrame(rows, columns=['PM25','PM10','CO','SO2','NO2','O3','Cat'])
X1, y1 = df1[['PM25','PM10','CO','SO2','NO2','O3']], df1['Cat']
X1tr,X1te,y1tr,y1te = train_test_split(X1, y1, test_size=0.2, random_state=42)
clf = RandomForestClassifier(n_estimators=150, random_state=42, n_jobs=-1)
clf.fit(X1tr, y1tr)
print(f"  Accuracy: {accuracy_score(y1te, clf.predict(X1te))*100:.2f}%")
joblib.dump(clf, os.path.join(SAVE_DIR,'aqi_model.pkl'))
print("  Saved: aqi_model.pkl")

print("\n" + "="*55)
print("  MODEL 2: Future AQI Forecaster (Gradient Boosting)")
print("="*55)

def gen_ts(days=500):
    ts = pd.date_range('2023-01-01', periods=days*24, freq='h')
    aqi = []
    for t in ts:
        h,m,wd = t.hour, t.month, t.weekday()
        base = 90
        if 7<=h<=9: base += np.random.uniform(35,70)
        elif 17<=h<=20: base += np.random.uniform(30,60)
        elif 1<=h<=4: base -= np.random.uniform(25,45)
        if m in [11,12,1,2]: base += np.random.uniform(50,100)
        elif m in [6,7,8]: base -= np.random.uniform(25,50)
        if wd>=5: base -= np.random.uniform(15,30)
        base += np.random.normal(0,12)
        aqi.append(float(np.clip(base,10,480)))
    df = pd.DataFrame({'aqi':aqi,'hour':[t.hour for t in ts],'month':[t.month for t in ts],'wd':[t.weekday() for t in ts],'we':[(t.weekday()>=5)*1 for t in ts]})
    return df

print("  Generating 500-day synthetic dataset...")
df2 = gen_ts(500)
WINDOW = 24
aqi_arr = df2['aqi'].values
X2,Y24,Y7d,Y30d=[],[],[],[]
for i in range(WINDOW, len(df2)-720-1):
    past = aqi_arr[i-WINDOW:i]
    tf = [df2['hour'].iloc[i],df2['month'].iloc[i],df2['wd'].iloc[i],df2['we'].iloc[i],
          past.mean(),past.std(),past.max(),past.min(),past[-1],past[-6],past[-12]]
    X2.append(np.concatenate([past,tf]))
    Y24.append(aqi_arr[i:i+24].mean())
    Y7d.append(aqi_arr[i:i+168].mean())
    Y30d.append(aqi_arr[i:i+720].mean())

X2=np.array(X2); Y2=np.column_stack([Y24,Y7d,Y30d])
X2tr,X2te,Y2tr,Y2te = train_test_split(X2,Y2,test_size=0.2,random_state=42,shuffle=False)
scaler = StandardScaler()
X2tr_s = scaler.fit_transform(X2tr); X2te_s = scaler.transform(X2te)
base_gb = GradientBoostingRegressor(n_estimators=120,learning_rate=0.1,max_depth=5,random_state=42)
forecaster = MultiOutputRegressor(base_gb, n_jobs=-1)
print("  Training... (~30 seconds)")
forecaster.fit(X2tr_s, Y2tr)
Y2pr = forecaster.predict(X2te_s)
print(f"  MAE 24h:±{mean_absolute_error(Y2te[:,0],Y2pr[:,0]):.1f}  7d:±{mean_absolute_error(Y2te[:,1],Y2pr[:,1]):.1f}  30d:±{mean_absolute_error(Y2te[:,2],Y2pr[:,2]):.1f}")
joblib.dump(forecaster, os.path.join(SAVE_DIR,'future_model.pkl'))
joblib.dump(scaler, os.path.join(SAVE_DIR,'future_scaler.pkl'))
joblib.dump(aqi_arr[-WINDOW:], os.path.join(SAVE_DIR,'seed_24h.pkl'))
print("  Saved: future_model.pkl, future_scaler.pkl, seed_24h.pkl")
print("\n" + "="*55)
print("  ALL DONE! Now run: python manage.py runserver")
print("="*55+"\n")
