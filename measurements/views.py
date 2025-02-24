from django.db.models import Avg, Sum, F
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import datetime
import uuid

from .models import Datalogger, Location, Measurement
from .serializers import (
    DataRecordRequestSerializer,
    DataRecordResponseSerializer,
    DataRecordAggregateResponseSerializer,
)


@api_view(["POST"])
def ingest_data(request):
    serializer = DataRecordRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    # Get or create datalogger
    datalogger_id = data["datalogger"]
    datalogger, created = Datalogger.objects.get_or_create(id=datalogger_id)

    # Create location
    location_data = data["location"]
    location = Location.objects.create(
        lat=location_data["lat"], lng=location_data["lng"], datalogger=datalogger
    )

    # Create measurements
    for measurement_data in data["measurements"]:
        Measurement.objects.create(
            label=measurement_data["label"],
            value=measurement_data["value"],
            measured_at=data["at"],
            datalogger=datalogger,
            location=location,
        )

    return Response({}, status=status.HTTP_200_OK)


@api_view(["GET"])
def fetch_data_raw(request):
    # Required parameter
    datalogger_id = request.query_params.get("datalogger")
    if not datalogger_id:
        return Response(
            {"error": "Missing required datalogger parameter"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Optional filters
    since = request.query_params.get("since")
    before = request.query_params.get("before", timezone.now().isoformat())

    try:
        # Validate and convert UUID
        datalogger_uuid = uuid.UUID(datalogger_id)

        # Build query
        queryset = Measurement.objects.filter(datalogger_id=datalogger_uuid)

        if since:
            queryset = queryset.filter(ingested_at__gt=since)

        if before:
            queryset = queryset.filter(ingested_at__lt=before)

        # Prepare response data
        data = []
        for measurement in queryset:
            data.append(
                {
                    "label": measurement.label,
                    "measured_at": measurement.measured_at.isoformat(),
                    "value": measurement.value,
                }
            )

        serializer = DataRecordResponseSerializer(data=data, many=True)
        serializer.is_valid()
        return Response(serializer.data)

    except (ValueError, uuid.UUID.error):
        return Response(
            {"error": "Invalid datalogger ID format"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
def fetch_data_aggregates(request):
    # Required parameter
    datalogger_id = request.query_params.get("datalogger")
    if not datalogger_id:
        return Response(
            {"error": "Missing required datalogger parameter"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Optional filters
    since = request.query_params.get("since")
    before = request.query_params.get("before", timezone.now().isoformat())
    span = request.query_params.get("span", "raw")

    try:
        # Validate and convert UUID
        datalogger_uuid = uuid.UUID(datalogger_id)

        # Build base query
        queryset = Measurement.objects.filter(datalogger_id=datalogger_uuid)

        if since:
            queryset = queryset.filter(ingested_at__gt=since)

        if before:
            queryset = queryset.filter(ingested_at__lt=before)

        # Handle raw data case
        if span == "raw":
            data = []
            for measurement in queryset:
                data.append(
                    {
                        "label": measurement.label,
                        "measured_at": measurement.measured_at.isoformat(),
                        "value": measurement.value,
                    }
                )

            serializer = DataRecordResponseSerializer(data=data, many=True)
            serializer.is_valid()
            return Response(serializer.data)

        # Handle aggregation
        result = []

        # Process each label type separately
        for label in ["temp", "rain", "hum"]:
            label_queryset = queryset.filter(label=label)

            if not label_queryset.exists():
                continue

            # Group by time slot according to span
            if span == "day":
                date_trunc = "day"
            elif span == "hour":
                date_trunc = "hour"
            else:
                return Response(
                    {"error": "Invalid span parameter"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from django.db.models.functions import TruncDay, TruncHour

            if span == "day":
                label_queryset = label_queryset.annotate(
                    time_slot=TruncDay("measured_at")
                )
            else:  # hour
                label_queryset = label_queryset.annotate(
                    time_slot=TruncHour("measured_at")
                )

            # Group by time_slot and apply the appropriate aggregation
            # Mean for temp and hum, Sum for rain
            group_queryset = label_queryset.values("time_slot", "label")

            if label in ["temp", "hum"]:
                group_queryset = group_queryset.annotate(value=Avg("value"))
            else:  # rain
                group_queryset = group_queryset.annotate(value=Sum("value"))

            # Add to results
            for item in group_queryset:
                result.append(
                    {
                        "label": item["label"],
                        "time_slot": item["time_slot"].isoformat(),
                        "value": item["value"],
                    }
                )

        serializer = DataRecordAggregateResponseSerializer(data=result, many=True)
        serializer.is_valid()
        return Response(serializer.data)

    except (ValueError, uuid.UUID.error):
        return Response(
            {"error": "Invalid datalogger ID format"},
            status=status.HTTP_400_BAD_REQUEST,
        )
