from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Station(models.Model):
    name       = models.CharField(max_length=200)
    location   = models.CharField(max_length=200)
    city       = models.CharField(max_length=100, blank=True)
    latitude   = models.FloatField(default=0.0)
    longitude  = models.FloatField(default=0.0)
    is_active  = models.BooleanField(default=True)
    api_key    = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} — {self.location}"

    class Meta:
        ordering = ['-created_at']


class AQIReading(models.Model):
    AQI_CHOICES = [
        ('Good', 'Good'),
        ('Moderate', 'Moderate'),
        ('Poor', 'Poor'),
        ('Very Poor', 'Very Poor'),
        ('Severe', 'Severe'),
    ]
    SOURCE_CHOICES = [
        ('manual', 'Manual Entry'),
        ('iot',    'IoT Sensor'),
        ('api',    'API'),
    ]

    station    = models.ForeignKey(Station, on_delete=models.SET_NULL, null=True, blank=True)
    user       = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    pm25  = models.FloatField()
    pm10  = models.FloatField()
    co    = models.FloatField()
    so2   = models.FloatField()
    no2   = models.FloatField()
    o3    = models.FloatField()

    predicted_category = models.CharField(max_length=20, choices=AQI_CHOICES, blank=True)
    aqi_value          = models.IntegerField(default=0)

    location_name = models.CharField(max_length=200, blank=True)
    source        = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='manual')
    recorded_at   = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.location_name} | {self.predicted_category} | AQI {self.aqi_value}"

    class Meta:
        ordering = ['-recorded_at']

    def badge_class(self):
        return {
            'Good': 'good', 'Moderate': 'moderate',
            'Poor': 'poor', 'Very Poor': 'verypoor', 'Severe': 'severe'
        }.get(self.predicted_category, 'moderate')

    def health_advice(self):
        return {
            'Good':      '✅ Air is clean. Safe for all activities.',
            'Moderate':  '🟡 Acceptable. Sensitive people take care.',
            'Poor':      '🟠 Unhealthy for sensitive groups. Wear a mask.',
            'Very Poor': '🔴 Unhealthy for everyone. Limit outdoor time.',
            'Severe':    '🟣 Hazardous! Stay indoors. Use air purifier.',
        }.get(self.predicted_category, '')

    def aqi_color(self):
        return {
            'Good': '#22c55e', 'Moderate': '#f59e0b',
            'Poor': '#f97316', 'Very Poor': '#ef4444', 'Severe': '#7c3aed'
        }.get(self.predicted_category, '#64748b')


class ForecastResult(models.Model):
    user          = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    location_name = models.CharField(max_length=200)
    current_aqi   = models.FloatField()
    forecast_24h  = models.FloatField()
    forecast_7d   = models.FloatField()
    forecast_30d  = models.FloatField()
    category_24h  = models.CharField(max_length=20)
    category_7d   = models.CharField(max_length=20)
    category_30d  = models.CharField(max_length=20)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Forecast: {self.location_name} — {self.created_at.strftime('%d %b %Y')}"

    class Meta:
        ordering = ['-created_at']