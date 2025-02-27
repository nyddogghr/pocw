from django.core.validators import MinValueValidator
from rest_framework import serializers
from .models import Measurement


class LocationRequestSerializer(serializers.Serializer):
    lat = serializers.FloatField(validators=[MinValueValidator(0.0)])
    lng = serializers.FloatField(validators=[MinValueValidator(0.0)])


class MeasurementRequestSerializer(serializers.Serializer):
    label = serializers.ChoiceField(choices=["temp", "rain", "hum"])
    value = serializers.FloatField()


class DataRecordRequestSerializer(serializers.Serializer):
    at = serializers.DateTimeField()
    datalogger = serializers.UUIDField()
    location = LocationRequestSerializer()
    measurements = serializers.ListField(child=MeasurementRequestSerializer())

    def validate_measurements(self, measurements):
        # Validate measurement values based on label
        for measurement in measurements:
            label = measurement["label"]
            m_value = measurement["value"]

            if label == "temp" and (m_value < -20 or m_value > 40):
                raise serializers.ValidationError(
                    f"Temperature must be between -20 and 40, got {m_value}"
                )
            elif label == "hum" and (m_value < 20 or m_value > 100):
                raise serializers.ValidationError(
                    f"Humidity must be between 20 and 100, got {m_value}"
                )
            elif label == "rain" and (m_value < 0 or m_value > 2):
                raise serializers.ValidationError(
                    f"Rainfall must be between 0 and 2, got {m_value}"
                )

        return measurements


class DataRecordResponseSerializer(serializers.Serializer):
    label = serializers.ChoiceField(choices=["temp", "rain", "hum"])
    recorded_at = serializers.DateTimeField()
    value = serializers.FloatField()


class DataRecordAggregateResponseSerializer(serializers.Serializer):
    label = serializers.ChoiceField(choices=["temp", "rain", "hum"])
    time_slot = serializers.DateTimeField()
    value = serializers.FloatField()
