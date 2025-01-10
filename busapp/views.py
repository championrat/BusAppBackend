from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password
from django.contrib.auth import authenticate
from .models import BusDetails, TicketDetails, User
import json
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth.models import User, Group
from django.contrib.auth.hashers import check_password
from .permissions import IsNormalUser, IsAdminUser
from datetime import datetime
import re
from django.core.exceptions import ValidationError


@csrf_exempt
@api_view(['GET'])  # Ensures the view only accepts GET requests
def printbuses(request):
    try:
        buses = BusDetails.objects.all()
        buses_list = [{
            'Bus_No': bus.Bus_No,
            'Departure_Location': bus.Departure_Location,
            'Departure_Time': bus.Departure_Time.strftime('%H:%M:%S'),
            'Destinations': bus.Destinations,
            'Seats_Available': bus.Seats_Available
        } for bus in buses]
        
        if not buses_list:
            return JsonResponse({'error': 'No buses found'}, status=404)

        return JsonResponse({'buses': buses_list}, status=200)

    except Exception as e:
        return JsonResponse({'error': f'An error occurred: {str(e)}'}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsNormalUser])  # Only normal users can access this
def bookticket(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            busno = data.get('busno')
            dest = data.get('dest')
            np = data.get('np')

            # Validate if busno, dest, and np are provided
            if not busno or not dest or not np:
                return JsonResponse({'error': 'Bus number, destination, and number of passengers are required.'}, status=400)

            try:
                np = int(np)
                if np <= 0:
                    return JsonResponse({'error': 'Number of passengers must be a positive integer.'}, status=400)
            except ValueError:
                return JsonResponse({'error': 'Number of passengers must be an integer.'}, status=400)

            # Fetch bus details
            try:
                bus = BusDetails.objects.get(Bus_No=busno)
            except BusDetails.DoesNotExist:
                return JsonResponse({'error': 'Bus number not available'}, status=404)

            destinations_list = eval(bus.Destinations)
            ticket_costs_list = eval(bus.TicketCosts)

            # Validate if destination exists in the bus's destinations list
            if dest not in destinations_list:
                return JsonResponse({'error': 'Destination not available'}, status=400)

            # Check if there are enough seats available
            if bus.Seats_Available < np:
                return JsonResponse({'error': 'Not enough seats available for the requested number of passengers.'}, status=400)

            # Calculate the ticket cost
            index = destinations_list.index(dest)
            tcost = ticket_costs_list[index]
            tamount = tcost * np

            ticket_list = []
            for i in range(np):
                # Validate passenger information (name and age)
                passenger_name = data.get(f'passenger_name_{i}')
                passenger_age = data.get(f'passenger_age_{i}')

                if not passenger_name or not passenger_age:
                    return JsonResponse({'error': f'Missing passenger details for passenger {i + 1}.'}, status=400)

                # Generate ticket number
                ticket_no = TicketDetails.objects.all().count() + 1
                ticket = TicketDetails.objects.create(
                    Ticket_No=ticket_no,
                    Bus_No=busno,
                    Passenger_Name=passenger_name,
                    Passenger_Age=passenger_age
                )
                ticket_list.append({
                    'Ticket_No': ticket_no,
                    'Passenger_Name': ticket.Passenger_Name,
                    'Passenger_Age': ticket.Passenger_Age
                })

            # Update available seats
            bus.Seats_Available -= np
            bus.save()

            # Return success response with ticket details
            return JsonResponse({
                'busno': busno,
                'dest': dest,
                'np': np,
                'dtime': bus.Departure_Time.strftime('%H:%M:%S'),
                'tcost': tcost,
                'tamount': tamount,
                'tickets': ticket_list
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsNormalUser])  # Only normal users can access this
def cancel_ticket(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            ticket_no = data.get('ticket_no')

            # Validate if ticket_no is provided
            if not ticket_no:
                return JsonResponse({'error': 'Ticket number is required.'}, status=400)

            # Attempt to get the ticket details
            try:
                ticket = TicketDetails.objects.get(Ticket_No=ticket_no)
            except TicketDetails.DoesNotExist:
                return JsonResponse({'error': 'Ticket number not found'}, status=404)

            # Check if the ticket belongs to the logged-in user (optional validation)
            if ticket.User.username != request.user.username:
                return JsonResponse({'error': 'You are not authorized to cancel this ticket.'}, status=403)

            # Attempt to get the associated bus details
            try:
                bus = BusDetails.objects.get(Bus_No=ticket.Bus_No)
            except BusDetails.DoesNotExist:
                return JsonResponse({'error': 'Bus details not found for the ticket.'}, status=404)

            # Update available seats and delete the ticket
            bus.Seats_Available += 1
            bus.save()

            ticket.delete()

            return JsonResponse({
                'message': f'Ticket {ticket_no} has been successfully canceled. Seat is now available.'
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    else:
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsNormalUser])  # Only normal users can access this
def RetrieveTicket(request):
    if request.method == 'POST':
        try:
            # Validate if required data is present in the request
            data = json.loads(request.body)
            busno = data.get('busno')
            dest = data.get('dest')
            np = data.get('np')

            if not busno or not dest or np is None:
                return JsonResponse({'error': 'Bus number, destination, and number of passengers are required.'}, status=400)

            # Validate if np is a positive integer
            if not isinstance(np, int) or np <= 0:
                return JsonResponse({'error': 'Number of passengers must be a positive integer.'}, status=400)

            try:
                bus = BusDetails.objects.get(Bus_No=busno)
            except BusDetails.DoesNotExist:
                return JsonResponse({'error': 'Bus Number not available'}, status=404)

            try:
                destinations = json.loads(bus.Destinations)  # Assuming Destinations is stored as a JSON string
                ticket_costs = json.loads(bus.TicketCosts)  # Assuming TicketCosts is stored as a JSON string
            except ValueError:
                return JsonResponse({'error': 'Invalid data format for destinations or ticket costs.'}, status=400)

            # Validate if the destination exists in the bus' destinations
            if dest not in destinations:
                return JsonResponse({'error': 'Destination not available for this bus.'}, status=400)

            index = destinations.index(dest)
            tcost = ticket_costs[index]
            tamount = tcost * np

            return JsonResponse({
                'busno': busno,
                'dest': dest,
                'np': np,
                'dtime': bus.Departure_Time.strftime('%H:%M:%S'),
                'tcost': tcost,
                'tamount': tamount
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)

@csrf_exempt
@api_view(['POST'])
def signup(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Required fields validation
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            passenger_name = data.get('passenger_name')
            passenger_age = data.get('passenger_age')
            user_type = data.get('user_type')  # New field for user type (e.g., 'normal', 'admin')

            # Check if all required fields are present
            if not all([username, password, email, passenger_name, passenger_age, user_type]):
                return JsonResponse({'error': 'All fields are required (username, password, email, passenger_name, passenger_age, user_type).'}, status=400)

            # Validate username and password length
            if len(username) > 32:
                return JsonResponse({'error': 'Username must be 32 characters or less.'}, status=400)
            if len(password) > 32:
                return JsonResponse({'error': 'Password must be 32 characters or less.'}, status=400)

            # Validate user_type
            if user_type not in ['admin', 'normal']:
                return JsonResponse({'error': "Invalid 'user_type'. It must be either 'admin' or 'normal'."}, status=400)

            # Password Strength Validation
            if not validate_password_strength(password):
                return JsonResponse({'error': 'Password must be at least 8 characters long, include one uppercase letter, one lowercase letter, one number, and one special character.'}, status=400)

            # Hash the password before saving
            hashed_password = make_password(password)

            # Check if the username or email already exists
            if User.objects.filter(username=username).exists():
                return JsonResponse({'error': 'Username already exists'}, status=400)
            if User.objects.filter(email=email).exists():
                return JsonResponse({'error': 'Email already registered'}, status=400)

            # Create the user
            user = User(username=username, password=hashed_password, email=email,
                        first_name=passenger_name, last_name=passenger_age)
            user.save()

            # Assign the user type as a group (admin or normal)
            if user_type == 'admin':
                admin_group, created = Group.objects.get_or_create(name='admin')
                user.groups.add(admin_group)
            else:
                normal_group, created = Group.objects.get_or_create(name='normal')
                user.groups.add(normal_group)

            return JsonResponse({'message': 'User created successfully'}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)


def validate_password_strength(password):
    """
    Validates the password strength:
    - Minimum 8 characters long
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 8:
        return False

    if not re.search(r'[a-z]', password):  # at least one lowercase letter
        return False
    if not re.search(r'[A-Z]', password):  # at least one uppercase letter
        return False
    if not re.search(r'[0-9]', password):  # at least one digit
        return False
    if not re.search(r'[\W_]', password):  # at least one special character
        return False

    return True

@csrf_exempt
@api_view(['POST'])
def user_login(request):
    if request.method == 'POST':
        try:
            # Try to load the request body
            data = json.loads(request.body)

            # Validate that 'username' and 'password' are in the request data
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return JsonResponse({'error': 'Username and password are required.'}, status=400)

            # Fetch the user from the database
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'error': 'Invalid username or password'}, status=401)

            # Check if the password matches the hashed password
            if check_password(password, user.password):
                # Generate a refresh and access token
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)

                return JsonResponse({
                    'message': 'Login successful',
                    'access_token': access_token,  # Send the token back to the user
                }, status=200)
            else:
                return JsonResponse({'error': 'Invalid username or password'}, status=401)

        except json.JSONDecodeError:
            # Handle case where the request body is not valid JSON
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            # Catch any unexpected errors and return a generic error message
            return JsonResponse({'error': str(e)}, status=400)
    else:
        # Handle invalid HTTP method
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)



@csrf_exempt
@api_view(['POST'])
def refresh_token(request):
    if request.method == 'POST':
        try:
            # Try to load the request body
            data = json.loads(request.body)
            
            # Validate the presence of the refresh token in the request
            refresh_token = data.get('refresh_token')
            if not refresh_token:
                return JsonResponse({'error': 'Refresh token required'}, status=400)

            # Try to create a RefreshToken object to validate it
            try:
                refresh = RefreshToken(refresh_token)
            except Exception as e:
                # Catch invalid token exceptions and provide an error
                return JsonResponse({'error': 'Invalid refresh token: ' + str(e)}, status=400)

            # Generate a new access token from the valid refresh token
            access_token = str(refresh.access_token)

            return JsonResponse({'access_token': access_token}, status=200)

        except json.JSONDecodeError:
            # Handle invalid JSON body
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            # Catch other unexpected errors
            return JsonResponse({'error': str(e)}, status=400)
    else:
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])  # Ensures only authenticated users can access this view
def user_logout(request):
    return JsonResponse({'message': 'Logout successful. Please clear your token on the client side.'}, status=200)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsNormalUser])  # Only normal users can access this
def search_buses(request):
    if request.method == 'POST':
        try:
            # Load and validate the request data
            data = json.loads(request.body)
            dep_location = data.get('dep_location')
            dest = data.get('dest')

            # Validate presence of required fields
            if not dep_location or not dest:
                return JsonResponse({'error': 'Both departure location and destination are required.'}, status=400)
            
            # Validate that the departure location and destination are strings
            if not isinstance(dep_location, str) or not isinstance(dest, str):
                return JsonResponse({'error': 'Both departure location and destination must be strings.'}, status=400)

            # Call the display_buses function to filter buses based on the provided location and destination
            return display_buses(dep_location, dest)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    else:
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsNormalUser])  # Only normal users can access this view
def display_buses(request):
    if request.method == 'POST':
        try:
            # Load data from the request
            data = json.loads(request.body)
            dep_location = data.get('dep_location')
            dest = data.get('dest')

            # Validate required fields
            if not dep_location or not dest:
                return JsonResponse({'error': 'Both departure location and destination are required.'}, status=400)

            # Validate that dep_location and dest are strings
            if not isinstance(dep_location, str) or not isinstance(dest, str):
                return JsonResponse({'error': 'Both departure location and destination must be strings.'}, status=400)

            # Query buses based on the location and destination
            buses = BusDetails.objects.filter(
                Departure_Location=dep_location
            )

            # Filter buses based on destination
            buses = buses.filter(Destinations__contains=dest)

            buses_list = [{
                'Bus_No': bus.Bus_No,
                'Departure_Location': bus.Departure_Location,
                'Departure_Time': bus.Departure_Time.strftime('%H:%M:%S'),
                'Destinations': bus.Destinations,
                'Seats_Available': bus.Seats_Available
            } for bus in buses]

            # If no buses match the search criteria
            if not buses_list:
                return JsonResponse({'message': 'No buses found for this route.'}, status=404)

            # Return the list of buses
            return JsonResponse({'buses': buses_list}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)

    else:
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAdminUser])  # Only admin users can access this view
def add_bus(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            # Validate required fields
            required_fields = ['bus_no', 'departure_location', 'departure_time', 'destinations', 'seats_available', 'ticket_costs']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return JsonResponse({'error': f'Missing required fields: {", ".join(missing_fields)}'}, status=400)

            bus_no = data['bus_no']
            departure_location = data['departure_location']
            departure_time = data['departure_time']
            destinations = data['destinations']  # List of destinations
            seats_available = data['seats_available']
            ticket_costs = data['ticket_costs']  # List of ticket costs

            # Validate departure time format
            try:
                departure_time = datetime.strptime(departure_time, '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                return JsonResponse({'error': 'Invalid departure_time format. Use YYYY-MM-DDTHH:MM:SS.'}, status=400)

            # Validate that the destinations and ticket costs are lists
            if not isinstance(destinations, list) or not all(isinstance(dest, str) for dest in destinations):
                return JsonResponse({'error': 'Destinations must be a list of strings.'}, status=400)
            
            if not isinstance(ticket_costs, list) or not all(isinstance(cost, (int, float)) for cost in ticket_costs):
                return JsonResponse({'error': 'Ticket costs must be a list of numbers (integers or floats).'}, status=400)

            # Validate the number of seats
            if not isinstance(seats_available, int) or seats_available < 0:
                return JsonResponse({'error': 'Seats available must be a non-negative integer.'}, status=400)

            # Check if the bus number already exists
            if BusDetails.objects.filter(Bus_No=bus_no).exists():
                return JsonResponse({'error': 'Bus with this number already exists.'}, status=400)

            # Create and save the new bus
            bus = BusDetails.objects.create(
                Bus_No=bus_no,
                Departure_Location=departure_location,
                Departure_Time=departure_time,
                Destinations=json.dumps(destinations),  # Store as a JSON string
                Seats_Available=seats_available,
                TicketCosts=json.dumps(ticket_costs)  # Store as a JSON string
            )

            return JsonResponse({'message': 'Bus added successfully', 'bus_no': bus.Bus_No}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except KeyError as e:
            return JsonResponse({'error': f'Missing required field: {e}'}, status=400)
    else:
        return JsonResponse({'error': 'Only POST method is allowed.'}, status=405)