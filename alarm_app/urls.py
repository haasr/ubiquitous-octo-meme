"""
URL configuration for the alarm_app.
"""

from django.urls import path
from . import views

app_name = "alarm_app"

urlpatterns = [
    # Dashboard
    path("", views.index, name="index"),
    
    # Routine management
    path("routines/", views.RoutineListView.as_view(), name="routine_list"),
    path("routines/create/", views.RoutineCreateView.as_view(), name="routine_create"),
    path("routines/<int:pk>/", views.RoutineDetailView.as_view(), name="routine_detail"),
    path("routines/<int:pk>/edit/", views.RoutineUpdateView.as_view(), name="routine_edit"),
    path("routines/<int:pk>/delete/", views.RoutineDeleteView.as_view(), name="routine_delete"),
    path("routines/<int:pk>/toggle/", views.routine_toggle, name="routine_toggle"),
    
    # Settings
    path("settings/", views.settings_view, name="settings"),
]
