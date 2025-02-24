from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
import json
import uuid
from datetime import datetime, timedelta
from .models import Datalogger, Measurement


class MeasurementAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.datalogger_id = uuid.uuid4()
        self.datalogger = Datalogger.objects.create(id=self.datalogger_id)

        # Create some test measurements for this datalogger
        for i in range(10):
            Measurement.objects.create(
                label="temp",
                value=20.5 + i,
                measured_at=timezone.now() - timedelta(hours=i),
                datalogger=self.datalogger,
            )

            Measurement.objects.create(
                label="rain",
                value=0.2 * i,
                measured_at=timezone.now() - timedelta(hours=i),
                datalogger=self.datalogger,
            )

            Measurement.objects.create(
                label="hum",
                value=50.0 + i,
                measured_at=timezone.now() - timedelta(hours=i),
                datalogger=self.datalogger,
            )

    def test_ingest_data(self):
        url = reverse("ingest_data")
        data = {
            "at": timezone.now().isoformat(),
            "datalogger": str(uuid.uuid4()),
            "location": {
                "lat": 47.56321,
                "lng": 1.524568,
            },
            "measurements": [
                {
                    "label": "temp",
                    "value": 10.52,
                },
                {
                    "label": "rain",
                    "value": 0,
                },
            ],
        }

        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify data was saved
        self.assertTrue(Datalogger.objects.filter(id=data["datalogger"]).exists())

    def test_fetch_data_raw(self):
        url = reverse("fetch_data_raw")
        response = self.client.get(url, {"datalogger": str(self.datalogger_id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 30)  # 10 records * 3 types

    def test_fetch_data_raw_missing_datalogger(self):
        url = reverse("fetch_data_raw")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fetch_data_with_since_filter(self):
        url = reverse("fetch_data_raw")
        since_time = (timezone.now() - timedelta(hours=5)).isoformat()
        response = self.client.get(
            url, {"datalogger": str(self.datalogger_id), "since": since_time}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return fewer records due to the filter
        self.assertTrue(len(response.data) < 30)

    def test_fetch_data_aggregates_daily(self):
        url = reverse("fetch_data_aggregates")
        response = self.client.get(
            url, {"datalogger": str(self.datalogger_id), "span": "day"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify data structure
        for item in response.data:
            self.assertIn("label", item)
            self.assertIn("time_slot", item)
            self.assertIn("value", item)

    def test_fetch_data_aggregates_hourly(self):
        url = reverse("fetch_data_aggregates")
        response = self.client.get(
            url, {"datalogger": str(self.datalogger_id), "span": "hour"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
