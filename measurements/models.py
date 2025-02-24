from django.db import models
import uuid


class Datalogger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.id)


class Location(models.Model):
    lat = models.FloatField()
    lng = models.FloatField()
    datalogger = models.ForeignKey(
        Datalogger, on_delete=models.CASCADE, related_name="locations"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"({self.lat}, {self.lng})"


class Measurement(models.Model):
    LABEL_CHOICES = [
        ("temp", "Temperature"),
        ("rain", "Rainfall"),
        ("hum", "Humidity"),
    ]

    label = models.CharField(max_length=4, choices=LABEL_CHOICES)
    value = models.FloatField()
    measured_at = models.DateTimeField()
    ingested_at = models.DateTimeField(auto_now_add=True)
    datalogger = models.ForeignKey(
        Datalogger, on_delete=models.CASCADE, related_name="measurements"
    )
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE, related_name="measurements", null=True
    )

    class Meta:
        indexes = [
            models.Index(fields=["datalogger", "measured_at"]),
            models.Index(fields=["label", "measured_at"]),
            models.Index(fields=["ingested_at"]),
        ]

    def __str__(self):
        return f"{self.label}: {self.value} at {self.measured_at}"
