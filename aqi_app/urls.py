from django.urls import path
from . import views

urlpatterns = [
    path('',            views.home,            name='home'),
    path('realtime/',   views.realtime_aqi,    name='realtime'),
    path('future/',     views.future_forecast, name='future'),
    path('login/',      views.user_login,      name='login'),
    path('logout/',     views.user_logout,     name='logout'),
    path('dashboard/',  views.dashboard,       name='dashboard'),
    path('search/',     views.search_history,  name='search'),
    path('charts/',     views.visualisations,  name='visualisations'),
    path('stations/',   views.manage_stations, name='manage_stations'),
    path('stations/delete/<int:pk>/', views.delete_station, name='delete_station'),
    path('readings/',   views.readings_list,   name='readings_list'),
    path('readings/delete/<int:pk>/', views.delete_reading, name='delete_reading'),
    path('api/iot/',    views.iot_api,         name='iot_api'),
]
