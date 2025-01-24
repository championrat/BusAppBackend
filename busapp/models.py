from django.db import models
from django.core.validators import MinValueValidator
from datetime import datetime

# Create your models here.
class BusDetails(models.Model):
    Bus_No = models.IntegerField(unique=True)
    Departure_Location = models.CharField(max_length=100)
    Departure_Time = models.DateTimeField()
    Destinations = models.TextField()
    Seats_Available = models.IntegerField()
    TicketCosts = models.TextField()
    AgencyName = models.CharField(max_length=100)
    Driver = models.CharField(max_length=100, default='None')
    BusStatus = models.CharField(max_length=50, default='Scheduled')
    
    def __str__(self):
        return f'Bus {self.Bus_No}'

class TicketDetails(models.Model):
    Ticket_No = models.IntegerField(unique=True)
    Bus_No = models.IntegerField()
    Acct_Name = models.CharField(max_length=100, default = 'None')
    Passenger_Name = models.CharField(max_length=100)
    Passenger_Age = models.IntegerField(validators=[MinValueValidator(0)])
    TicketStatus = models.CharField(max_length=100, default='Booked')

class DriverDetails(models.Model):
    Driver_username = models.CharField(unique=True, max_length=100)
    Driver_Name = models.CharField(max_length=100)
    Driver_DOB = models.DateField()
    DL_DOE = models.DateField()
    Driver_License_No = models.CharField(max_length=100)
    Driver_Address = models.TextField(default='bro is homeless')
    Driver_Contact = models.CharField(max_length=100)
    
    # def save(self, *args, **kwargs):
    #     # Extract just the date from the datetime object
    #     if isinstance(self.Driver_DOB, datetime):
    #         self.Driver_DOB = self.Driver_DOB.date()  # Get the date part of datetime
    #     if isinstance(self.DL_DOE, datetime):
    #         self.DL_DOE = self.DL_DOE.date()  # Get the date part of datetime
    #     super().save(*args, **kwargs)