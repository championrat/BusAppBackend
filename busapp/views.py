from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate, login, logout
from .models import BusDetails, TicketDetails, User
from .forms import BusForm, PassengerForm, UserForm, TicketForm, LoginForm

# Create your views here.
def printbuses(request):
    buses = BusDetails.objects.all()
    return render(request, 'printbuses.html', {'buses':buses})

def bookticket(request):
    if request.method == 'POST':
        busform = BusForm(request.POST)
        
        if busform.is_valid():
            # Extract form data
            busno = busform.cleaned_data['busno']
            dest = busform.cleaned_data['dest']
            np = busform.cleaned_data['np']  
            
            try:
                bus = BusDetails.objects.get(Bus_No=busno)
                
                destinations_list = eval(bus.Destinations)
                ticket_costs_list = eval(bus.TicketCosts)
                
                if dest not in destinations_list:
                    return HttpResponse('Sorry!!! Destination not available.')
                
                # Get dest index
                index = destinations_list.index(dest)
                
                # Check available seats
                if bus.Seats_Available >= np:
                    # Compute the total ticket cost
                    tcost = ticket_costs_list[index]
                    tamount = tcost * np
                    
                    #Passenger deets input
                    passenger_forms = [PassengerForm(request.POST, prefix=str(i)) for i in range(np)]
                    
                    # Validate all passenger forms
                    if all([form.is_valid() for form in passenger_forms]):
                        # Create tickets for each passenger
                        for i in range(np):
                            passenger_name = passenger_forms[i].cleaned_data['passenger_name']
                            passenger_age = passenger_forms[i].cleaned_data['passenger_age']
                            
                            # Generate ticket number
                            ticket_no = TicketDetails.objects.all().count() + 1
                            
                            # Create TicketDetails objects for each passenger
                            ticket = TicketDetails.objects.create(
                                Ticket_No=ticket_no,
                                Bus_No=busno,
                                Passenger_Name=passenger_name,
                                Passenger_Age=passenger_age
                            )
                            ticket.save()
                        
                        # Update the available seats
                        bus.Seats_Available -= np
                        bus.save()
                        
                        # Return a confirmation page with ticket details
                        return render(request, 'printticket.html', {
                            'busno': busno,
                            'dest': dest,
                            'np': np,
                            'dtime': bus.Departure_Time,
                            'tcost': tcost,
                            'tamount': tamount,
                            'passenger_forms': passenger_forms  # Include passenger info in confirmation
                        })
                    else:
                        return render(request, 'displayform.html', {
                            'busform': busform,
                            'passenger_forms': passenger_forms
                        })
                else:
                    return HttpResponse('Sorry!!! Seats not available')
            
            except BusDetails.DoesNotExist:
                return HttpResponse('Sorry!!! Bus Number not available')
            except ValueError:
                return HttpResponse('Sorry!!! Destination not available')

        else:
            return render(request, 'displayform.html', {'busform': busform})
    else:
        busform = BusForm()
        return render(request, 'displayform.html', {'busform': busform})


def cancel_ticket(request):
    if request.method == 'POST':
        # Create the form instance with POST data
        ticket_form = TicketForm(request.POST)

        if ticket_form.is_valid():
            # Get the ticket number from the cleaned data
            ticket_no = ticket_form.cleaned_data['tno']

            try:
                # Get the ticket details using the ticket number
                ticket = TicketDetails.objects.get(Ticket_No=ticket_no)

                # Get the corresponding bus details
                bus = BusDetails.objects.get(Bus_No=ticket.Bus_No)

                # Update the available seats in the BusDetails model
                bus.Seats_Available += 1  # Increase seat count as the ticket is being canceled
                bus.save()

                # Delete the ticket record from TicketDetails
                ticket.delete()

                # Return a success message after cancellation
                return HttpResponse(f"Ticket {ticket_no} has been successfully canceled. Seat is now available.")

            except TicketDetails.DoesNotExist:
                return HttpResponse(f"Ticket number {ticket_no} does not exist.")
            except BusDetails.DoesNotExist:
                return HttpResponse("Bus details not found for the ticket.")
        else:
            # If the form is not valid, re-render the form with errors
            return render(request, 'cancel_ticket.html', {'ticket_form': ticket_form})

    else:
        # If it's a GET request, render the cancel ticket form
        ticket_form = TicketForm()
        return render(request, 'cancel_ticket.html', {'ticket_form': ticket_form})

def RetrieveTicket(request):
    if request.method == 'POST':
        busform = BusForm(request.POST)
        
        if busform.is_valid():
            busno = busform.cleaned_data['busno']
            dest = busform.cleaned_data['dest']
            np = busform.cleaned_data['np']
            try:
                bus = BusDetails.objects.get(Bus_No=busno)
                index = eval(bus.Destinations).index(dest)
                tcost = eval(bus.TicketCosts)[index]
                tamount = tcost * np
                return render(request, 'printticket.html', {'busno':busno, 'dest': dest, 'np':np, 'dtime': bus.Departure_Time, 'tcost': tcost, 'tamount':tamount})
            except ValueError:
                return HttpResponse('Sorry!!! Destination not available')
            except:
                return HttpResponse('Sorry!!! Bus Number not available')
        else:
            busform = BusForm(request.POST)
            return render(request, 'displayform.html', {'busform': busform})
    else:
        busform = BusForm()
        return render(request, 'displayform.html', {'busform': busform})

def signup(request):
    if request.method == 'POST':
        userform = UserForm(request.POST)

        if userform.is_valid():
            # Extract form data
            username = userform.cleaned_data['username']
            password = userform.cleaned_data['password']
            email = userform.cleaned_data['email']
            passenger_name = userform.cleaned_data['passenger_name']
            passenger_age = userform.cleaned_data['passenger_age']

            # Hash the password before saving
            hashed_password = make_password(password)

            # Check if the username or email already exists in the database
            if User.objects.filter(username=username).exists():
                return HttpResponse('Username already exists. Please choose another username.')
            if User.objects.filter(email=email).exists():
                return HttpResponse('Email is already registered. Please use a different email.')

            # Create and save the new user with hashed password
            user = User(username=username, password=hashed_password, email=email,
                        passenger_name=passenger_name, passenger_age=passenger_age)
            user.save()

            # Redirect to login page or home page after successful signup
            return redirect('login')  # Replace 'login' with the URL name for the login page

        else:
            # If the form is not valid, render the form again with errors
            return render(request, 'signup.html', {'userform': userform})

    else:
        # If it's a GET request, show the signup form
        userform = UserForm()
        return render(request, 'signup.html', {'userform': userform})

def user_login(request):
    if request.method == 'POST':
        # Create an instance of the form with POST data
        loginform = LoginForm(request.POST)

        # Validate the form
        if loginform.is_valid():
            username = loginform.cleaned_data['username']
            password = loginform.cleaned_data['password']

            # Authenticate the user
            user = authenticate(request, username=username, password=password)

            if user is not None:
                # If authentication is successful, log the user in
                login(request, user)

                # Redirect to a success page (e.g., homepage or dashboard)
                return redirect('home')  # Replace 'home' with the URL name for your desired page

            else:
                # If authentication fails, display an error message
                return HttpResponse('Invalid username or password.')

        else:
            # If form is invalid, re-render the login form with errors
            return render(request, 'login.html', {'loginform': loginform})

    else:
        # If it's a GET request, render the login form
        loginform = LoginForm()
        return render(request, 'login.html', {'loginform': loginform})


def user_logout(request):
    # Log the user out
    logout(request)

    # Redirect to a success page (e.g., login page)
    return redirect('home')  # Replace 'login' with the URL name for the login page