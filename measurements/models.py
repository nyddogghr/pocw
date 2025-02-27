from django.db import models
import uuid


class Measurement(models.Model):
    LABEL_CHOICES = [
        ("temp", "Temperature"),
        ("rain", "Rainfall"),
        ("hum", "Humidity"),
    ]

    label = models.CharField(max_length=4, choices=LABEL_CHOICES)
    value = models.FloatField()
    recorded_at = models.DateTimeField()
    datalogger = models.UUIDField()
    location = models.JSONField()

    class Meta:
        indexes = [
            models.Index(fields=["datalogger", "recorded_at"]),
            models.Index(fields=["label", "recorded_at"]),
            models.Index(fields=["recorded_at"]),
        ]

    def __str__(self):
        return f"{self.label}: {self.value} recorded at {self.recorded_at}"
