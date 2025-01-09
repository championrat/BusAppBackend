from django import forms
from .models import BusDetails
from .models import user
from .models import TicketDetails

buses = BusDetails.objects.all()
Busnos = ((str(bus.Bus_No), str(bus.Bus_No)) for bus in buses)
class BusForm(forms.Form):
    busno = forms.ChoiceField(choices=Busnos, label='Bus Number')
    dep = forms.ChoiceField(choices=((bus.Departure_Location, bus.Departure_Location) for bus in buses))
    dest = forms.CharField(max_length=50)
    np = forms.IntegerField()

class PassengerForm(forms.Form):
    passenger_name = forms.CharField(max_length=100, label = 'Passenger Name')
    passenger_age = forms.IntegerField(min_value=0, label = 'Passenger Age')

class UserForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(widget=forms.PasswordInput, max_length=100)
    email = forms.EmailField(max_length=100)
    passenger_name = forms.CharField(max_length=100)
    passenger_age = forms.IntegerField(min_value=0)

    
class TicketForm(forms.Form):
    tno = forms.IntegerField(max_length=100)
    
class LoginForm(forms.Form):
    username = forms.CharField(max_length=100)
    password = forms.CharField(max_length=100, widget = forms.PasswordInput)