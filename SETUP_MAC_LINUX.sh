#!/bin/bash
echo "============================================="
echo "  AQI PREDICTION SYSTEM - SETUP"
echo "============================================="
echo "[1/5] Installing packages..."
pip install Django==4.2.7 scikit-learn==1.3.2 pandas==2.1.3 numpy==1.26.2 joblib==1.3.2
echo "[2/5] Training ML models (~1 min)..."
python ml_model/train_models.py
echo "[3/5] Setting up database..."
python manage.py makemigrations && python manage.py migrate
echo "[4/5] Creating admin..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin','admin@aqi.com','Test@123')
    print('Admin created!')
else:
    print('Admin exists!')
"
echo "[5/5] Starting server at http://127.0.0.1:8000"
echo "Admin: admin / Test@123"
python manage.py runserver
