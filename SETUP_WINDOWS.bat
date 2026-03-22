@echo off
echo =============================================
echo   AQI PREDICTION SYSTEM - SETUP
echo =============================================
echo.
echo [1/5] Installing packages...
pip install Django==4.2.7 scikit-learn==1.3.2 pandas==2.1.3 numpy==1.26.2 joblib==1.3.2
echo.
echo [2/5] Training ML models (takes ~1 min)...
python ml_model/train_models.py
echo.
echo [3/5] Setting up database...
python manage.py makemigrations
python manage.py migrate
echo.
echo [4/5] Creating admin user...
python manage.py shell -c "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin','admin@aqi.com','Test@123'); print('Admin ready!')"
echo.
echo [5/5] Starting server...
echo    Open browser: http://127.0.0.1:8000
echo    Admin login:  admin / Test@123
echo =============================================
python manage.py runserver
pause
