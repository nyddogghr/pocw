from django.urls import path
from . import views

urlpatterns = [
    path("ingest", views.ingest_data, name="ingest_data"),
    path("data", views.fetch_data_raw, name="fetch_data_raw"),
    path("summary", views.fetch_data_aggregates, name="fetch_data_aggregates"),
]
