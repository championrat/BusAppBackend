from django.db import models
from django.core.validators import MinValueValidator

# Create your models here.
class BusDetails(models.Model):
    Bus_No = models.IntegerField(unique=True)
    Departure_Location = models.CharField(max_length=100)
    Departure_Time = models.TimeField()
    Destinations = models.CharField(max_length=500)
    Seats_Available = models.IntegerField()
    TicketCosts = models.CharField(max_length=100)

class TicketDetails(models.Model):
    Ticket_No = models.IntegerField(unique=True)
    Bus_No = models.IntegerField()
    Passenger_Name = models.CharField(max_length=100)
    Passenger_Age = models.IntegerField(validators=[MinValueValidator(0)])

class User(models.Model):
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    passenger_name = models.CharField(max_length=100)
    passenger_age = models.IntegerField(validators=[MinValueValidator(0)])