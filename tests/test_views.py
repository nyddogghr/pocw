from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

import copy
import json
import uuid

from datetime import datetime, timedelta

from measurements.models import Measurement


class MeasurementAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.datalogger = uuid.uuid4()

        for i in range(10):
            Measurement.objects.create(
                label="temp",
                value=20.5 + i,
                recorded_at=timezone.now() - timedelta(hours=i),
                datalogger=self.datalogger,
                location={
                    "lat": 0.5 + i,
                    "lng": 0.5 + i,
                },
            )

            Measurement.objects.create(
                label="rain",
                value=0.2 * i,
                recorded_at=timezone.now() - timedelta(hours=i),
                datalogger=self.datalogger,
                location={
                    "lat": 0.5 + i,
                    "lng": 0.5 + i,
                },
            )

            Measurement.objects.create(
                label="hum",
                value=50.0 + i,
                recorded_at=timezone.now() - timedelta(hours=i),
                datalogger=self.datalogger,
                location={
                    "lat": 0.5 + i,
                    "lng": 0.5 + i,
                },
            )

    def test_measurement_repr(self):
        self.assertIsNotNone(str(Measurement.objects.first()))

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

        self.assertTrue(
            Measurement.objects.filter(datalogger=data["datalogger"]).exists()
        )

        # Errors
        error_data = copy.deepcopy(data)
        error_data["location"] = {
            "key": 5.6,
        }
        response = self.client.post(url, error_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_data = copy.deepcopy(data)
        error_data["location"]["lat"] = -2.5
        response = self.client.post(url, error_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_data = copy.deepcopy(data)
        error_data["location"] = "string"
        response = self.client.post(url, error_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_data = copy.deepcopy(data)
        error_data["measurements"] = [
            {
                "key": 5.6,
            }
        ]
        response = self.client.post(url, error_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        for measurement in [
            ("temp", 500),
            ("hum", 0),
            ("rain", 8),
        ]:
            error_data = copy.deepcopy(data)
            error_data["measurements"] = [
                {
                    "label": measurement[0],
                    "value": measurement[1],
                }
            ]
            response = self.client.post(url, error_data, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        error_data = copy.deepcopy(data)
        error_data["measurements"] = "string"
        response = self.client.post(url, error_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fetch_data_raw(self):
        url = reverse("fetch_data_raw")
        response = self.client.get(url, {"datalogger": str(self.datalogger)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 30)  # 10 records * 3 types

        # Filtering on datalogger with no data
        url = reverse("fetch_data_raw")
        response = self.client.get(url, {"datalogger": str(uuid.uuid4())})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)

        # Errors
        url = reverse("fetch_data_raw")
        response = self.client.get(url, {"datalogger": "logger"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fetch_data_raw_missing_datalogger(self):
        url = reverse("fetch_data_raw")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fetch_data_with_since_filter(self):
        url = reverse("fetch_data_raw")
        since_time = (timezone.now() - timedelta(hours=5)).isoformat()
        response = self.client.get(
            url, {"datalogger": str(self.datalogger), "since": since_time}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) < 30)

    def test_fetch_data_aggregates_raw(self):
        url = reverse("fetch_data_aggregates")
        response = self.client.get(url, {"datalogger": str(self.datalogger)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) == 30)

        # Verify data structure
        for item in response.data:
            self.assertIn("label", item)
            self.assertIn("recorded_at", item)
            self.assertIn("value", item)

        # Using since filter
        since_time = (timezone.now() - timedelta(hours=5)).isoformat()
        url = reverse("fetch_data_aggregates")
        response = self.client.get(
            url,
            {
                "datalogger": str(self.datalogger),
                "since": since_time,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) < 30)

        # Filtering on datalogger with no data
        url = reverse("fetch_data_aggregates")
        response = self.client.get(url, {"datalogger": str(uuid.uuid4())})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(len(response.data) == 0)

    def test_fetch_data_aggregates_raw_errors(self):
        url = reverse("fetch_data_aggregates")
        response = self.client.get(url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        url = reverse("fetch_data_aggregates")
        response = self.client.get(url, {"datalogger": "logger"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_fetch_data_aggregates_daily(self):
        url = reverse("fetch_data_aggregates")
        response = self.client.get(
            url, {"datalogger": str(self.datalogger), "span": "day"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

        # Verify data structure
        for item in response.data:
            self.assertIn("label", item)
            self.assertIn("time_slot", item)
            self.assertIn("value", item)

        # Only one type of measurements
        datalogger = uuid.uuid4()

        temp_sum = 0
        for i in range(10):
            temp_value = 20.5 + i
            temp_sum += temp_value
            Measurement.objects.create(
                label="temp",
                value=temp_value,
                recorded_at=timezone.now(),
                datalogger=datalogger,
                location={
                    "lat": 0.5 + i,
                    "lng": 0.5 + i,
                },
            )
        url = reverse("fetch_data_aggregates")
        response = self.client.get(url, {"datalogger": str(datalogger), "span": "day"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["label"], "temp")
        self.assertEqual(response.data[0]["value"], temp_sum / 10)

    def test_fetch_data_aggregates_hourly(self):
        url = reverse("fetch_data_aggregates")
        response = self.client.get(
            url, {"datalogger": str(self.datalogger), "span": "hour"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_fetch_data_aggregates_error(self):
        url = reverse("fetch_data_aggregates")
        response = self.client.get(
            url, {"datalogger": str(self.datalogger), "span": "other"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
