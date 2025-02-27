from django.db.models import Avg, Sum, F, Q
from django.db.models.functions import TruncDay, TruncHour
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
import datetime
import uuid

from .models import Measurement
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

    for measurement_data in data["measurements"]:
        Measurement.objects.create(
            label=measurement_data["label"],
            value=measurement_data["value"],
            recorded_at=data["at"],
            datalogger=data["datalogger"],
            location=data["location"],
        )

    return Response({}, status=status.HTTP_200_OK)


@api_view(["GET"])
def fetch_data_raw(request):
    # Required parameter
    datalogger = request.query_params.get("datalogger")
    if not datalogger:
        return Response(
            {"error": "Missing required datalogger parameter"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Optional filters
    since = request.query_params.get("since")
    before = request.query_params.get("before", timezone.now().isoformat())

    try:
        datalogger_uuid = uuid.UUID(datalogger)

        queryset = Measurement.objects.filter(datalogger=datalogger_uuid)

        if since:
            queryset = queryset.filter(recorded_at__gt=since)

        if before:
            queryset = queryset.filter(recorded_at__lt=before)

        data = []
        for measurement in queryset:
            data.append(
                {
                    "label": measurement.label,
                    "recorded_at": measurement.recorded_at.isoformat(),
                    "value": measurement.value,
                }
            )

        serializer = DataRecordResponseSerializer(data=data, many=True)
        serializer.is_valid()
        return Response(serializer.data)

    except ValueError:
        return Response(
            {"error": "Invalid datalogger ID format"},
            status=status.HTTP_400_BAD_REQUEST,
        )


@api_view(["GET"])
def fetch_data_aggregates(request):
    # Required parameter
    datalogger = request.query_params.get("datalogger")
    if not datalogger:
        return Response(
            {"error": "Missing required datalogger parameter"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Optional filters
    since = request.query_params.get("since")
    before = request.query_params.get("before", timezone.now().isoformat())
    span = request.query_params.get("span")

    try:
        datalogger_uuid = uuid.UUID(datalogger)

        queryset = Measurement.objects.filter(datalogger=datalogger_uuid)

        if since:
            queryset = queryset.filter(recorded_at__gt=since)

        if before:
            queryset = queryset.filter(recorded_at__lt=before)

        if span is None:
            data = []
            for measurement in queryset:
                data.append(
                    {
                        "label": measurement.label,
                        "recorded_at": measurement.recorded_at.isoformat(),
                        "value": measurement.value,
                    }
                )

            serializer = DataRecordResponseSerializer(data=data, many=True)
            serializer.is_valid()
            return Response(serializer.data)

        result = []

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

        if span == "day":
            queryset = queryset.annotate(time_slot=TruncDay("recorded_at"))
        else:  # hour
            queryset = queryset.annotate(time_slot=TruncHour("recorded_at"))

        # Group by time_slot and apply the appropriate aggregation
        # Mean for temp and hum, Sum for rain
        group_queryset = queryset.values("time_slot", "label")
        temp = Avg("value", filter=Q(label="temp"))
        hum = Avg("value", filter=Q(label="hum"))
        rain = Sum("value", filter=Q(label="rain"))
        group_queryset = (
            group_queryset.annotate(temp=temp).annotate(hum=hum).annotate(rain=rain)
        )

        for item in group_queryset:
            result.append(
                {
                    "label": item["label"],
                    "time_slot": item["time_slot"].isoformat(),
                    "value": item[item["label"]],
                }
            )

        serializer = DataRecordAggregateResponseSerializer(data=result, many=True)
        serializer.is_valid()
        return Response(serializer.data)

    except ValueError:
        return Response(
            {"error": "Invalid datalogger ID format"},
            status=status.HTTP_400_BAD_REQUEST,
        )
