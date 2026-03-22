from django.contrib import admin
from .models import AQIReading, Station, ForecastResult

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ['name', 'location', 'is_active', 'api_key', 'created_at']

@admin.register(AQIReading)
class AQIReadingAdmin(admin.ModelAdmin):
    list_display = ['location_name', 'predicted_category', 'aqi_value', 'source', 'recorded_at']
    list_filter  = ['predicted_category', 'source']

@admin.register(ForecastResult)
class ForecastAdmin(admin.ModelAdmin):
    list_display = ['location_name', 'current_aqi', 'forecast_24h', 'forecast_7d', 'created_at']
