from rest_framework import serializers
from .models import BusDetails, TicketDetails, User

class BusDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusDetails
        fields = ['Bus_No', 'Departure_Location', 'Departure_Time', 'Destinations', 'Seats_Available', 'TicketCosts']

class TicketDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = TicketDetails
        fields = ['Ticket_No', 'Bus_No', 'Passenger_Name', 'Passenger_Age']

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'password', 'usertype', 'email', 'passenger_name', 'passenger_age']
