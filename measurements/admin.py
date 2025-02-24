# measurements/admin.py
from django.contrib import admin
from .models import Datalogger, Location, Measurement


@admin.register(Datalogger)
class DataloggerAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at")
    search_fields = ("id",)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("id", "lat", "lng", "datalogger")
    list_filter = ("datalogger",)
    search_fields = ("datalogger__id",)


@admin.register(Measurement)
class MeasurementAdmin(admin.ModelAdmin):
    list_display = ("id", "label", "value", "measured_at", "datalogger")
    list_filter = ("label", "datalogger", "measured_at")
    search_fields = ("datalogger__id",)
    date_hierarchy = "measured_at"
