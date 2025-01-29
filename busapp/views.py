from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import authenticate
from django.db import IntegrityError
import django.db.utils
from .models import BusDetails, TicketDetails, DriverDetails
import json, requests
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.contrib.auth.models import User, Group
from .permissions import IsNormalUser, IsAdminUser, IsDriverUser
from datetime import datetime
import re
from django.core.exceptions import ValidationError
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
import sqlite3
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.conf import settings
import os

@csrf_exempt
@api_view(['POST'])  # Ensures the view only accepts GET requests
@authentication_classes([])  # Disable authentication for this view
@permission_classes([AllowAny])  # Allow anyone to access this view
def testAPI(request):
    response_data = json.loads(request.body)
    print(response_data)
    return JsonResponse({'message': 'API test successful'}, status=200)

@csrf_exempt
@api_view(['GET'])  # Ensures the view only accepts GET requests
@authentication_classes([])  # Disable authentication for this view
@permission_classes([AllowAny])  # Allow anyone to access this view
def printbuses(request):
    try:
        buses = BusDetails.objects.all()
        buses_list = [{
            'Bus_No': bus.Bus_No,
            'Departure_Location': bus.Departure_Location,
            'Departure_Date': bus.Departure_Time.date(),
            'Departure_Time': bus.Departure_Time.strftime('%H:%M:%S'),
            'Destinations': bus.Destinations,
            'Ticket_Costs': bus.TicketCosts,
            'Seats_Available': bus.Seats_Available,
            'Agency_Name' : bus.AgencyName,
            'Driver' : bus.Driver,
            'bus_status' : bus.BusStatus
        } for bus in buses]
        
        if not buses_list:
            return JsonResponse({'message': 'No buses found'}, status=404)

        return JsonResponse({'buses': buses_list}, status=200)

    except Exception as e:
        return JsonResponse({'message': f'An error occurred: {str(e)}'}, status=500)


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
                return JsonResponse({'message': 'Bus number, destination, and number of passengers are required.'}, status=400)

            try:
                np = int(np)
                if np <= 0:
                    return JsonResponse({'message': 'Number of passengers must be a positive integer.'}, status=400)
            except ValueError:
                return JsonResponse({'message': 'Number of passengers must be an integer.'}, status=400)

            # Fetch bus details
            try:
                bus = BusDetails.objects.get(Bus_No=busno)
            except BusDetails.DoesNotExist:
                return JsonResponse({'message': 'Bus number not available'}, status=404)

            destinations_list = eval(bus.Destinations)
            ticket_costs_list = eval(bus.TicketCosts)

            # Validate if destination exists in the bus's destinations list
            if dest not in destinations_list:
                return JsonResponse({'message': 'Destination not available'}, status=400)

            # Check if there are enough seats available
            if bus.Seats_Available < np:
                return JsonResponse({'message': 'Not enough seats available for the requested number of passengers.'}, status=400)

            # Calculate the ticket cost
            index = destinations_list.index(dest)
            tcost = ticket_costs_list[index]
            tamount = tcost * np
            
            #retrieve username
            username = request.user.username

            ticket_list = []
            for i in range(np):
                # Validate passenger information (name and age)
                passenger_name = data.get(f'passenger_name_{i}')
                passenger_age = data.get(f'passenger_age_{i}')

                if not passenger_name or not passenger_age:
                    return JsonResponse({'message': f'Missing passenger details for passenger {i + 1}.'}, status=400)

                # Generate ticket number
                ticket_no = TicketDetails.objects.all().count() + 1000
                ticket = TicketDetails.objects.create(
                    Ticket_No=ticket_no,
                    Bus_No=busno,
                    Acct_Name=username,
                    Passenger_Name=passenger_name,
                    Passenger_Age=passenger_age
                )
                ticket_list.append({
                    'Ticket_No': ticket_no,
                    'Acct_Name': ticket.Acct_Name,
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
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=400)
    else:
        return JsonResponse({'message': 'Only POST method is allowed.'}, status=405)

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
                return JsonResponse({'message': 'Ticket number is required.'}, status=400)

            # Attempt to get the ticket details
            try:
                ticket = TicketDetails.objects.get(Ticket_No=ticket_no)
            except TicketDetails.DoesNotExist:
                return JsonResponse({'message': 'Ticket number not found'}, status=404)

            # Check if the ticket belongs to the logged-in user (optional validation)
            if ticket.Acct_Name != request.user.username:
                return JsonResponse({'message': 'You are not authorized to cancel this ticket.'}, status=403)

            # Attempt to get the associated bus details
            try:
                bus = BusDetails.objects.get(Bus_No=ticket.Bus_No)
            except BusDetails.DoesNotExist:
                return JsonResponse({'message': 'Bus details not found for the ticket.'}, status=404)

            # Update available seats and cancel the ticket
            bus.Seats_Available += 1
            bus.save()

            ticket.TicketStatus = 'Cancelled'
            ticket.save()

            return JsonResponse({
                'message': f'Ticket {ticket_no} has been successfully canceled. Seat is now available.'
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=400)

    else:
        return JsonResponse({'message': 'Only POST method is allowed.'}, status=405)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # Allow anyone to access this view
def get_ticket_details(request):
    try:
        # Parse the JSON body of the request
        data = json.loads(request.body)
        ticket_no = data.get('ticket_no')
        passenger_name = data.get('passenger_name')

        # Check if both ticket_no and passenger_name were provided
        if not ticket_no or not passenger_name:
            return JsonResponse({'message': 'Both ticket_no and passenger_name are required'}, status=400)

        # Query the database for the ticket matching the ticket_no and passenger_name
        ticket = TicketDetails.objects.filter(Ticket_No=ticket_no, Passenger_Name=passenger_name).first()

        if not ticket:
            return JsonResponse({'message': 'Ticket not found'}, status=404)

        # Return the ticket details as JSON
        ticket_data = {
            'Ticket_No': ticket.Ticket_No,
            'Bus_No': ticket.Bus_No,
            'Acct_Name': ticket.Acct_Name,
            'Passenger_Name': ticket.Passenger_Name,
            'Passenger_Age': ticket.Passenger_Age
        }

        return JsonResponse({'ticket': ticket_data})

    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON'}, status=400)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Only authenticated users can access this view
def get_user_tickets(request):
    if request.method == 'GET':
        try:
            # Get the logged-in user's username
            username = request.user.username

            # Fetch all tickets associated with the logged-in user (based on Acct_Name)
            tickets = TicketDetails.objects.filter(Acct_Name=username)

            # If no tickets found, return an empty list
            if not tickets.exists():
                return JsonResponse({'message': 'No tickets found for this user.'}, status=404)

            # Prepare the ticket data in JSON format
            tickets_list = [{
                'Ticket_No': ticket.Ticket_No,
                'Bus_No': ticket.Bus_No,
                'Passenger_Name': ticket.Passenger_Name,
                'Passenger_Age': ticket.Passenger_Age,
                'Acct_Name': ticket.Acct_Name,
                'TicketStatus': ticket.TicketStatus
            } for ticket in tickets]

            # Return the ticket details in the response
            return JsonResponse({'tickets': tickets_list}, status=200)

        # except ValueError as e:
        #     return JsonResponse({'message': 'No tickets booked'}, status = 404)
        
        except Exception as e:
            return JsonResponse({'message': f'An error occurred: {str(e)}'}, status=500)
    else:
        return JsonResponse({'message': 'Only GET method is allowed.'}, status=405)


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this view
@permission_classes([AllowAny])  # Allow anyone to access this view
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
            user_type = data.get('user_type')  # New field for user type (e.g., 'normal', 'admin', 'driver')

            # Check if all required fields are present
            if not all([username, password, email, passenger_name, passenger_age, user_type]):
                print('All fields are required (username, password, email, passenger_name, passenger_age, user_type).')
                print(data)
                return JsonResponse({'message': 'All fields are required (username, password, email, passenger_name, passenger_age, user_type).'}, status=400)
                
            # Validate username and password length
            if len(username) > 32:
                print('Username must be 32 characters or less')
                return JsonResponse({'message': 'Username must be 32 characters or less.'}, status=400)

            # Validate user_type
            if user_type not in ['admin', 'normal', 'driver']:
                print("Invalid 'user_type'. It must be either 'admin', 'normal' or 'driver'.")
                return JsonResponse({'message': "Invalid 'user_type'. It must be either 'admin', 'normal' or 'driver'."}, status=400)

            # Password Strength Validation
            if not validate_password_strength(password):
                print('Password must be at least 8 characters long, include one uppercase letter, one lowercase letter, one number, and one special character.')
                return JsonResponse({'message': 'Password must be at least 8 characters long, include one uppercase letter, one lowercase letter, one number, and one special character.'}, status=400)

            # Hash the password before saving
            hashed_password = make_password(password)

            # Check if the username or email already exists
            if User.objects.filter(username=username).exists():
                print('Username already exists')
                return JsonResponse({'message': 'Username already exists'}, status=400)
            if User.objects.filter(email=email).exists():
                print('Email already registered')
                return JsonResponse({'message': 'Email already registered'}, status=400)

            # Create the user
            user = User(username=username, password=hashed_password, email=email,
                        first_name=passenger_name, last_name=passenger_age)
            user.save()

            # Assign the user type as a group (admin or normal)
            if user_type == 'admin':
                admin_group, created = Group.objects.get_or_create(name='admin')
                user.groups.add(admin_group)
            elif user_type == 'normal':
                normal_group, created = Group.objects.get_or_create(name='normal')
                user.groups.add(normal_group)
            elif user_type == 'driver':
                driver_group, created = Group.objects.get_or_create(name='driver')
                user.groups.add(driver_group)
                # call driver kyc function here

            return JsonResponse({'message': 'User created successfully'}, status=201)

        except json.JSONDecodeError:
            print('Invalid JSON data')
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            print(str(e))
            return JsonResponse({'message': str(e)}, status=400)
    else:
        return JsonResponse({'message': 'Only POST method is allowed.'}, status=405)


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

# def dl_front_kyc(driver_license_front):
#     # KYC API URL and headers
#     dl_url = 'https://ind.idv.hyperverge.co/v1/readId'
#     headers = {
#         'appId': '52vn3f',
#         'appKey': 'nf1yhe5el4g84ieulsh7',
#         'transactionId': '3'
#     }

#     # Prepare files and form data for the API call
#     dlf_files = {'image': driver_license_front}
#     dlf_data = {
#         'countryId': 'ind',
#         'documentId': 'dl',
#         'expectedDocumentSide': 'front',
#         'preferences.returnScore': 'yes',
#         'preferences.returnConfidence': 'yes',
#         'qualityChecks.glare': 'yes',
#         'qualityChecks.blur': 'yes',
#         'qualityChecks.blackAndWhite': 'yes',
#         'qualityChecks.capturedFromScreen': 'yes',
#         'qualityChecks.partialId': 'yes',
#         # 'qualityChecks.faceClear': 'yes',
#         'qualityChecks.faceNotClear': 'yes',
#         'qualityChecks.face': 'yes',
#         'qualityChecks.obscuredId': 'yes',
#         'qualityChecks.cutId': 'yes',
#         'forgeryChecks.text': 'yes',
#         'forgeryChecks.photo': 'yes',
#         'forgeryChecks.emblem': 'yes',
#         'forgeryChecks.dob': 'yes',
#         'forgeryChecks.dobColon': 'yes',
#         'forgeryChecks.idNumberLength': 'yes',
#         'forgeryChecks.expiry': 'yes',
#         'forgeryChecks.provinceMismatch': 'yes',
#         'forgeryChecks.genderAndDOBMismatch': 'yes',
#         'forgeryChecks.qrMismatch': 'yes',
#         'ruleChecks.idNumber': 'yes',
#         'ruleChecks.dateOfBirth': 'yes',
#         'ruleChecks.dateOfIssue': 'yes',
#         'ruleChecks.dateOfExpiry': 'yes',
#         'forgeryChecks.facePhoto': 'yes',
#         'forgeryChecks.digitalText': 'yes',
#         'forgeryChecks.physicalText': 'yes',
#         'forgeryChecks.colorPrintout': 'yes'
#     }

#     # Make API request
#     try:
#         response_f = requests.post(dl_url, headers=headers, files=dlf_files, data=dlf_data)
#         response_data_f = response_f.json()
#     except Exception as e:
#         return {'status': 'error', 'message': 'Error connecting to DL Verification service', 'error': str(e)}

#     # Handle API response
#     if response_data_f.get('status') == 'success':
#         details_f = response_data_f.get('result', {}).get('details', [])[0]
#         extracted_fields_f = details_f.get('fieldsExtracted', {})
#         quality_checks_f = details_f.get('qualityChecks', {})

#         # Validate quality checks
#         failed_quality_checks_f = {
#             key: value for key, value in quality_checks_f.items() 
#             if value.get('value') in ['yes'] and value.get('confidence') == 'high'
#         }

#         # Check for low confidence in critical fields
#         critical_fields = ['fullName', 'dateOfBirth', 'idNumber']
#         low_confidence_fields_f = {
#             field: extracted_fields_f[field]
#             for field in critical_fields
#             if extracted_fields_f.get(field, {}).get('confidence', '') == 'low'
#         }

#         # Determine retry status based on quality checks and low confidence
#         if failed_quality_checks_f or low_confidence_fields_f:
#             return {
#                 'status': 'retry',
#                 'failed_quality_checks': failed_quality_checks_f,
#                 'low_confidence_fields': low_confidence_fields_f
#             }

#         driver_info = {
#             'full_name': extracted_fields_f.get('fullName', {}).get('value', ''),
#             'dob': extracted_fields_f.get('dateOfBirth', {}).get('value', ''),
#             'id_number': extracted_fields_f.get('idNumber', {}).get('value', ''),
#             'license_expiry': extracted_fields_f.get('dateOfExpiry', {}).get('value', ''),
#         }

#         return {'status': 'success', 'driver_info': driver_info}

#     elif response_data_f.get('status') == 'failure':
#         error_message = response_data_f.get('result', {}).get('error', 'Unexpected error')
#         return {'status': 'error', 'error': error_message}
    
#     return {'status': 'error', 'message': 'Unexpected error occurred'}

# def livenessCheck(driver_selfie_file):
#     # Liveness check API URL and headers
#     liveness_url = 'https://ind.idv.hyperverge.co/v1/checkLiveness'
#     headers = {
#         'appId': '52vn3f',
#         'appKey': 'nf1yhe5el4g84ieulsh7',
#         'transactionId': '3'
#     }
#     selfie_files = {'image': driver_selfie_file}
#     selfie_data = {
#         'qualityChecks.eyesClosed': 'yes',
#         'qualityChecks.blur': 'yes',
#         'qualityChecks.maskPresent': 'yes',
#         'qualityChecks.multipleFaces': 'yes',
#         'qualityChecks.hat': 'yes',
#         'qualityChecks.sunglasses': 'yes',
#         'qualityChecks.readingGlasses': 'yes',
#         'qualityChecks.dull': 'yes',
#         'qualityChecks.lowQuality': 'yes',
#         'qualityChecks.bright': 'yes',
#         'qualityChecks.headTurned': 'yes',
#         'qualityChecks.eyewear': 'yes',
#         'qualityChecks.occlusion': 'yes',
#         'qualityChecks.nudity': 'yes',
#         # 'qualityChecks.nonWhiteBackground': 'yes',
#         'ageRange': 'yes',
#         'fraudChecks.checkDeepfake': 'yes',
#         'fraudChecks.checkAnomaly': 'yes'
#     }
    
#     try:
#         response_s = requests.post(liveness_url, headers=headers, files=selfie_files, data=selfie_data)
#         response_data_s = response_s.json()
#     except Exception as e:
#         return {'status': 'error', 'message': 'Error connecting to LivenessCheck service', 'error': str(e)}
    
#     if response_data_s.get('status') == 'success':
#         # details_s = response_data_s.get('result', {}).get('details', {})
#         liveFace = response_data_s.get('result', {}).get('details', {}).get('liveFace', {})
#         quality_checks_s = response_data_s.get('result', {}).get('details', {}).get('qualityChecks', {})
#         # print(liveFace.get('value'))
        
#         # Validate quality checks
#         failed_quality_checks_s = {
#             (key, value) : value for key, value in quality_checks_s.items() 
#             if key != 'faceClear' and value.get('value') in ['yes'] and value.get('confidence') == 'high'
#         }
        
#         if liveFace.get('value') == 'no' and liveFace.get('confidence') == 'high':
#             return {'status': 'retry', 'message': 'Liveness check failed'}
#         elif failed_quality_checks_s:
#             return {'status': 'retry', 'failed_quality_checks': failed_quality_checks_s}
#         else:
#             return {'status': 'success'}
        
# def facematch_check(driver_selfie_file, driver_license_front):
#     # FaceMatch API URL and headers
#     facematch_url = 'https://ind.idv.hyperverge.co/v1/matchFace'
#     headers = {
#         'appId': '52vn3f',
#         'appKey': 'nf1yhe5el4g84ieulsh7',
#         'transactionId': '3',
#         # 'Content-Type' : 'multipart/form-data'
#     }
#     fm_files = {
#         'selfie': driver_selfie_file,
#         'id': driver_license_front
#     }
    
#     # fm_files = {
#     #     'selfie': (driver_selfie_file.name, driver_selfie_file, driver_selfie_file.content_type),
#     #     'id': (driver_license_front.name, driver_license_front, driver_license_front.content_type)
#     # }
    
#     # Open test files (make sure the files exist and are small)
#     # with open('/home/user/Documents/DBusApp/busapp/TN-DL_FRONT.jpg', 'rb') as driver_selfie_file, open('/home/user/Documents/DBusApp/busapp/TN-DL_FRONT.jpg', 'rb') as driver_license_front:
#     #     fm_files = {
#     #         'selfie': ('selfie.jpg', driver_selfie_file, 'image/jpeg'),
#     #         'id': ('id_card.jpg', driver_license_front, 'image/jpeg')
#     #     }
    
#     # selfie_size = driver_selfie_file.size
#     # license_size = driver_license_front.size
#     # print(f"Selfie size: {selfie_size} bytes")
#     # print(f"License front size: {license_size} bytes")
    
#     try:
#         response_fm = requests.post(facematch_url, headers=headers, files=fm_files, stream=True)
#         response_data_fm = response_fm.json()
#     except Exception as e:
#         print(str(e))
#         return {'status': 'error', 'message': 'Error connecting to FaceMatch service', 'error': str(e)}
    
#     if response_data_fm.get('status') == 'success':
#         results = response_data_fm.get('result', {}).get('details', {}).get('match', {}).get('value', '')
#         confidence = response_data_fm.get('result', {}).get('details', {}).get('match', {}).get('confidence', '')
        
#         if results == 'yes' and confidence == 'high':
#             return {'status': 'success'}
#         elif results == 'no' and confidence == 'high':
#             return {'status': 'retry', 'message': 'FaceMatch requires retry'}
#         elif results == 'yes' and confidence == 'low':
#             return {'status': 'retry', 'message': 'FaceMatch requires retry'}
#     else:
#         print(response_data_fm.get('status'))
#         print(response_data_fm)
#         return {'status': 'error', 'message': 'FaceMatch failed'}            


# @csrf_exempt
# @api_view(['POST'])
# @permission_classes([IsDriverUser])  # Replace with your custom permission class
# def driver_kyc(request):

    
#     if not request.content_type.startswith('multipart/form-data'):
#         return JsonResponse({'message': 'Content-Type must be multipart/form-data'}, status=400)
    
#     # Ensure the request contains both data and files
#     if not request.FILES or 'driver-license-front' not in request.FILES or 'driver-selfie' not in request.FILES:
#         return JsonResponse({'message': 'Driver license files and selfie are required'}, status=400)

#     # Extract data from the request
#     driver_address = request.POST.get('driver-address')
#     driver_phone = request.POST.get('driver-phone')
#     driver_license_front = request.FILES['driver-license-front']  # Uploaded file
#     print(driver_license_front.size/1024)
#     driver_license_back = request.FILES.get('driver-license-back')  # Mandatory file
#     driver_selfie_file = request.FILES.get('driver-selfie')  # Mandatory selfie file

#     fp_dlf = default_storage.save(f'dlf_{request.user.username}.jpg',ContentFile(driver_license_front))
#     fp_dlb = default_storage.save(f'dlb_{request.user.username}.jpg',ContentFile(driver_license_back))
    
#     # Validate input
#     if not all([driver_address, driver_phone]):
#         return JsonResponse({'message': 'All fields are required'}, status=400)
    
#     DL_ver = False
#     S_ver = False
#     FM_ver = False
    
#     # Perform DL verification using helper fn
#     result_DL = dl_front_kyc(driver_license_front)
    
#     # Handle the result and return appropriate response
#     if result_DL['status'] == 'error':
#         return JsonResponse({'message': result_DL['message'], 'error': result_DL['error']}, status=500)

#     elif result_DL['status'] == 'retry':
#         return JsonResponse({
#             'message': 'DL verification requires retry',
#             'failed_quality_checks': result_DL['failed_quality_checks'],
#             'low_confidence_fields': result_DL['low_confidence_fields']
#         }, status=422)
    
#     elif result_DL['status'] == 'success':
#         DL_ver = True
#     else:
#         return JsonResponse({'message': 'Unexpected error occurred'}, status=500)
    
#     # Perform selfie liveness check if DL verification is successful
#     result_LV = livenessCheck(driver_selfie_file)
    
#     # Handle the result and return appropriate response
#     if result_LV['status'] == 'error':
#         return JsonResponse({'message': result_LV['message'], 'error': result_LV['error']}, status=422)
#     elif result_LV['status'] == 'retry':
#         return JsonResponse({'message': 'Liveness check requires retry', 'failed_quality_checks': result_LV['failed_quality_checks']}, status=400)
#     elif result_LV['status'] == 'success':
#         S_ver = True
    
#     # Perform facematch between selfie and DL photo if selfie liveness check is successful
#     result_FM = facematch_check(driver_selfie_file, driver_license_front)
    
#     # Handle the result and return appropriate response
#     if result_FM['status'] == 'retry':
#         return JsonResponse({'message': result_FM['message']}, status=400)
#     elif result_FM['status'] == 'error':
#         return JsonResponse({'message': result_FM['message']}, status=500)
#     elif result_FM['status'] == 'success':
#         FM_ver = True
    
#     if DL_ver and S_ver and FM_ver:
#         # Save the driver details to the database
#         driver = DriverDetails(
#             Driver_username = request.user.username,
#             Driver_Name = result_DL['driver_info']['full_name'],
#             Driver_DOB = datetime.strptime(result_DL['driver_info']['dob'], "%d-%m-%Y").strftime("%Y-%m-%d"),
#             DL_DOE = datetime.strptime(result_DL['driver_info']['license_expiry'], "%d-%m-%Y").strftime("%Y-%m-%d"),
#             Driver_License_No = result_DL['driver_info']['id_number'],
#             Driver_Address = driver_address,
#             Driver_Contact = driver_phone
#         )
#         driver.save()
    
#     # If successful
#     return JsonResponse({'message': 'KYC successful, Driver registered', 'driver_info': result_DL['driver_info']}, status=200)



@csrf_exempt
@api_view(['GET'])
@permission_classes([AllowAny])
def get_appToken(request):
    appID = '52vn3f'
    appKey = 'nf1yhe5el4g84ieulsh7'
    
    token_url = 'https://auth.hyperverge.co/login'
    token_data = {
        'appId': appID,
        'appKey': appKey,
        # 'expiry': 43200
    }
    
    try:
        response_AK = requests.post(token_url, data = token_data)
        response_data_AK = response_AK.json()
    except Exception as e:
        return {'status': 'error', 'message': 'Error connecting to AppToken service', 'error': str(e)}
    
    if response_data_AK.get('status') == 'success':
        appToken = response_data_AK.get('result', {}).get('token', '')
        return JsonResponse({'appToken': appToken}, status=200)


def dl_front_kyc(driver_license_front_path, driver_license_back_path):
    dl_url = 'https://ind.idv.hyperverge.co/v1/readId'
    headers = {
        'appId': '52vn3f',
        'appKey': 'nf1yhe5el4g84ieulsh7',
        'transactionId': '3'
    }

    with open(driver_license_front_path, 'rb') as f:
        dlf_files = {'image': f}
        dlf_data = {
            'countryId': 'ind',
            'documentId': 'dl',
            'expectedDocumentSide': 'front',
            # Add other parameters here as needed
        }

        try:
            response_f = requests.post(dl_url, headers=headers, files=dlf_files, data=dlf_data)
            response_data_f = response_f.json()
        except Exception as e:
            return {'status': 'error', 'message': 'Error connecting to DL Verification service', 'error': str(e)}

    # Handle the response here as before...
    # Handle API response
    if response_data_f.get('status') == 'success':
        details_f = response_data_f.get('result', {}).get('details', [])[0]
        extracted_fields_f = details_f.get('fieldsExtracted', {})
        quality_checks_f = details_f.get('qualityChecks', {})

        # Validate quality checks
        failed_quality_checks_f = {
            key: value for key, value in quality_checks_f.items() 
            if value.get('value') in ['yes'] and value.get('confidence') == 'high'
        }

        # Check for low confidence in critical fields
        critical_fields = ['fullName', 'dateOfBirth', 'idNumber']
        low_confidence_fields_f = {
            field: extracted_fields_f[field]
            for field in critical_fields
            if extracted_fields_f.get(field, {}).get('confidence', '') == 'low'
        }

        # Determine retry status based on quality checks and low confidence
        if failed_quality_checks_f or low_confidence_fields_f:
            return {
                'status': 'retry',
                'failed_quality_checks': failed_quality_checks_f,
                'low_confidence_fields': low_confidence_fields_f
            }
        
    with open(driver_license_back_path, 'rb') as f:
        dlb_files = {'image': f}
        dlb_data = {
            'countryId': 'ind',
            'documentId': 'dl',
            'expectedDocumentSide': 'front',
            # Add other parameters here as needed
        }

        try:
            response_b = requests.post(dl_url, headers=headers, files=dlb_files, data=dlb_data)
            response_data_b = response_f.json()
        except Exception as e:
            return {'status': 'error', 'message': 'Error connecting to DL Verification service', 'error': str(e)}

        # Handle the response here as before...
        # Handle API response
    if response_data_b.get('status') == 'success':
        details_b = response_data_b.get('result', {}).get('details', [])[0]
        extracted_fields_b = details_b.get('fieldsExtracted', {})
        quality_checks_b = details_b.get('qualityChecks', {})

        # Validate quality checks
        failed_quality_checks_b = {
            key: value for key, value in quality_checks_b.items() 
            if value.get('value') in ['yes'] and value.get('confidence') == 'high'
        }

        # Check for low confidence in critical fields
        critical_fields = ['fullName', 'dateOfBirth', 'idNumber']
        low_confidence_fields_b = {
            field: extracted_fields_b[field]
            for field in critical_fields
            if extracted_fields_b.get(field, {}).get('confidence', '') == 'low'
        }

        # Determine retry status based on quality checks and low confidence
        if failed_quality_checks_b or low_confidence_fields_b:
            return {
                'status': 'retry',
                'failed_quality_checks': failed_quality_checks_b,
                'low_confidence_fields': low_confidence_fields_b
            }

        driver_info = {
            'full_name': extracted_fields_b.get('fullName', {}).get('value', ''),
            'dob': extracted_fields_b.get('dateOfBirth', {}).get('value', ''),
            'id_number': extracted_fields_b.get('idNumber', {}).get('value', ''),
            'license_expiry': extracted_fields_b.get('dateOfExpiry', {}).get('value', ''),
            'address': extracted_fields_b.get('address', {}).get('value', '')
        }

        return {'status': 'success', 'driver_info': driver_info}

    elif response_data_b.get('status') == 'failure':
        error_message = response_data_b.get('result', {}).get('error', 'Unexpected error')
        return {'status': 'error', 'error': error_message}
    
    return {'status': 'error', 'message': 'Unexpected error occurred'}

def livenessCheck(driver_selfie_file_path):
    liveness_url = 'https://ind.idv.hyperverge.co/v1/checkLiveness'
    headers = {
        'appId': '52vn3f',
        'appKey': 'nf1yhe5el4g84ieulsh7',
        'transactionId': '3'
    }

    with open(driver_selfie_file_path, 'rb') as f:
        selfie_files = {'image': f}
        selfie_data = {
            'qualityChecks.eyesClosed': 'yes',
            'qualityChecks.blur': 'yes',
            # Add other parameters here as needed
        }

        try:
            response_s = requests.post(liveness_url, headers=headers, files=selfie_files, data=selfie_data)
            response_data_s = response_s.json()
        except Exception as e:
            return {'status': 'error', 'message': 'Error connecting to LivenessCheck service', 'error': str(e)}

        # Handle the response here as before...
    if response_data_s.get('status') == 'success':
        # details_s = response_data_s.get('result', {}).get('details', {})
        liveFace = response_data_s.get('result', {}).get('details', {}).get('liveFace', {})
        quality_checks_s = response_data_s.get('result', {}).get('details', {}).get('qualityChecks', {})
        # print(liveFace.get('value'))
        
        # Validate quality checks
        failed_quality_checks_s = {
            (key, value) : value for key, value in quality_checks_s.items() 
            if key != 'faceClear' and value.get('value') in ['yes'] and value.get('confidence') == 'high'
        }
        
        if liveFace.get('value') == 'no' and liveFace.get('confidence') == 'high':
            return {'status': 'retry', 'message': 'Liveness check failed'}
        elif failed_quality_checks_s:
            return {'status': 'retry', 'failed_quality_checks': failed_quality_checks_s}
        else:
            return {'status': 'success'}
        

def facematch_check(driver_selfie_file_path, driver_license_front_path):
    facematch_url = 'https://ind.idv.hyperverge.co/v1/matchFace'
    headers = {
        'appId': '52vn3f',
        'appKey': 'nf1yhe5el4g84ieulsh7',
        'transactionId': '3',
    }

    with open(driver_selfie_file_path, 'rb') as selfie_file, open(driver_license_front_path, 'rb') as license_file:
        fm_files = {
            'selfie': selfie_file,
            'id': license_file
        }

        try:
            response_fm = requests.post(facematch_url, headers=headers, files=fm_files)
            response_data_fm = response_fm.json()
        except Exception as e:
            return {'status': 'error', 'message': 'Error connecting to FaceMatch service', 'error': str(e)}

        # Handle the response here as before...
    if response_data_fm.get('status') == 'success':
        results = response_data_fm.get('result', {}).get('details', {}).get('match', {}).get('value', '')
        confidence = response_data_fm.get('result', {}).get('details', {}).get('match', {}).get('confidence', '')
        
        if results == 'yes' and confidence == 'high':
            return {'status': 'success'}
        elif results == 'no' and confidence == 'high':
            return {'status': 'retry', 'message': 'FaceMatch requires retry'}
        elif results == 'yes' and confidence == 'low':
            return {'status': 'retry', 'message': 'FaceMatch requires retry'}
    else:
        print(response_data_fm.get('status'))
        print(response_data_fm)
        return {'status': 'error', 'message': 'FaceMatch failed'}  

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsDriverUser])  # Replace with your custom permission class
def driver_kyc(request):
    if not request.content_type.startswith('multipart/form-data'):
        return JsonResponse({'message': 'Content-Type must be multipart/form-data'}, status=400)

    # Ensure the request contains both data and files
    if not request.FILES or 'driver-license-front' not in request.FILES or 'driver-license-back' not in request.FILES or 'driver-selfie' not in request.FILES:
        return JsonResponse({'message': 'Driver license files and selfie are required'}, status=400)

    # Extract data from the request
    # driver_address = request.POST.get('driver-address')
    driver_phone = request.POST.get('driver-phone')
    driver_license_front = request.FILES['driver-license-front']  # Uploaded file
    driver_license_back = request.FILES.get('driver-license-back')  # Optional
    driver_selfie_file = request.FILES.get('driver-selfie')  # Mandatory selfie file

    # Save the files to disk temporarily using default_storage
    license_front_path = default_storage.save(f'dlf_{request.user.username}.jpg', ContentFile(driver_license_front.read()))
    license_back_path = default_storage.save(f'dlb_{request.user.username}.jpg', ContentFile(driver_license_back.read()))
    selfie_path = default_storage.save(f'selfie_{request.user.username}.jpg', ContentFile(driver_selfie_file.read()))
    
    print(f"License Front Path: {license_front_path}")
    print(f"License Back Path: {license_back_path}")
    print(f"Selfie Path: {selfie_path}")
    
    full_license_front_path = os.path.join(settings.MEDIA_ROOT, license_front_path)
    full_license_back_path = os.path.join(settings.MEDIA_ROOT, license_back_path) if license_back_path else None
    full_selfie_path = os.path.join(settings.MEDIA_ROOT, selfie_path)
    
    print(f"Full License Front Path: {full_license_front_path}")
    print(f"Full License Back Path: {full_license_back_path}")
    print(f"Full Selfie Path: {full_selfie_path}")



    # Validate input
    if not all([driver_phone]):
        return JsonResponse({'message': 'All fields are required'}, status=400)

    DL_ver = False
    S_ver = False
    FM_ver = False

    # Perform DL verification using helper fn
    result_DL = dl_front_kyc(full_license_front_path, full_license_back_path)
    
    if result_DL['status'] == 'error':
        return JsonResponse({'message': result_DL['message'], 'error': result_DL['error']}, status=500)
    elif result_DL['status'] == 'retry':
        return JsonResponse({'message': 'DL verification requires retry', 'failed_quality_checks': result_DL['failed_quality_checks'], 'low_confidence_fields': result_DL['low_confidence_fields']}, status=422)
    elif result_DL['status'] == 'success':
        DL_ver = True

    # Perform selfie liveness check if DL verification is successful
    result_LV = livenessCheck(full_selfie_path)
    if result_LV['status'] == 'error':
        return JsonResponse({'message': result_LV['message'], 'error': result_LV['error']}, status=422)
    elif result_LV['status'] == 'retry':
        return JsonResponse({'message': 'Liveness check requires retry', 'failed_quality_checks': result_LV['failed_quality_checks']}, status=400)
    elif result_LV['status'] == 'success':
        S_ver = True

    # Perform facematch between selfie and DL photo if selfie liveness check is successful
    result_FM = facematch_check(full_selfie_path, full_license_front_path)
    if result_FM['status'] == 'retry':
        return JsonResponse({'message': result_FM['message']}, status=400)
    elif result_FM['status'] == 'error':
        return JsonResponse({'message': result_FM['message']}, status=500)
    elif result_FM['status'] == 'success':
        FM_ver = True

    # If all verifications are successful, save the driver details to the database
    try:
        if DL_ver and S_ver and FM_ver:
            driver = DriverDetails(
                Driver_username=request.user.username,
                Driver_Name=result_DL['driver_info']['full_name'],
                Driver_DOB=datetime.strptime(result_DL['driver_info']['dob'], "%d-%m-%Y").strftime("%Y-%m-%d"),
                DL_DOE=datetime.strptime(result_DL['driver_info']['license_expiry'], "%d-%m-%Y").strftime("%Y-%m-%d"),
                Driver_License_No=result_DL['driver_info']['id_number'],
                Driver_Address=result_DL['driver_info']['address'],
                Driver_Contact=driver_phone
            )
            driver.save()
    except Exception as e:
        return JsonResponse({'message': str(e) + '<br>This may occur if you have already completed KYC'}, status=500)
    finally:
        default_storage.delete(f'dlf_{request.user.username}.jpg')
        default_storage.delete(f'dlb_{request.user.username}.jpg')
        default_storage.delete(f'selfie_{request.user.username}.jpg')

    # If successful
    return JsonResponse({'message': 'KYC successful, Driver registered', 'driver_info': result_DL['driver_info']}, status=200)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsDriverUser])  # Replace with your custom permission class
def sdk_kyc(request):
    try:
        data = json.loads(request.body)
        d_name = data.get('d_name')
        d_dob = data.get('d_dob')
        dl_doe = data.get('dl_doe')
        dl_no = data.get('dl_no')
        d_address = data.get('d_address')
        d_phone = data.get('d_contact')
        
        if not all([d_name, d_dob, dl_doe, dl_no, d_address, d_phone]):
            return JsonResponse({'message': 'All fields are required'}, status=400)
        else:
            driver = DriverDetails(
                Driver_username=request.user.username,
                Driver_Name=d_name,
                Driver_DOB=datetime.strptime(d_dob, "%d-%m-%Y").strftime("%Y-%m-%d"),
                DL_DOE=datetime.strptime(dl_doe, "%d-%m-%Y").strftime("%Y-%m-%d"),
                Driver_License_No=dl_no,
                Driver_Address=d_address,
                Driver_Contact=d_phone
            )
            driver.save()
            return JsonResponse({'message': 'KYC successful, Driver registered'}, status=200)
    except json.JSONDecodeError:
        # Handle case where the request body is not valid JSON
        return JsonResponse({'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        # Catch any unexpected errors and return a generic error message
        return JsonResponse({'message': str(e)}, status=400)
        
@csrf_exempt
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this view
@permission_classes([AllowAny])  # Allow anyone to access this view
def user_login(request):
    if request.method == 'POST':
        try:
            # Try to load the request body
            data = json.loads(request.body)

            # Validate that 'username' and 'password' are in the request data
            username = data.get('username')
            password = data.get('password')

            if not username or not password:
                return JsonResponse({'message': 'Username and password are required.'}, status=400)

            # Fetch the user from the database
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({'message': 'Invalid username or password'}, status=401)

            # Check if the password matches the hashed password
            if check_password(password, user.password):
                # Generate a refresh and access token
                refresh = RefreshToken.for_user(user)
                access_token = str(refresh.access_token)
                refresh_token = str(refresh)
                
                print(f"Access Token: {access_token}")
                print(f"Refresh Token: {refresh_token}")

                return JsonResponse({
                    'message': 'Login successful',
                    'access_token': access_token,  # Send the token back to the user
                    'refresh_token': refresh_token,
                }, status=200)
            else:
                return JsonResponse({'message': 'Invalid username or password'}, status=401)

        except json.JSONDecodeError:
            # Handle case where the request body is not valid JSON
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            # Catch any unexpected errors and return a generic error message
            return JsonResponse({'message': str(e)}, status=400)
    else:
        # Handle invalid HTTP method
        return JsonResponse({'message': 'Only POST method is allowed.'}, status=405)

@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])  # Only authenticated users can access this view
def get_user_info(request):
    user = request.user
    user_groups = [group.name for group in user.groups.all()]  # Get all groups of the user

    # Prepare the user data
    user_data = {
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,  # Passenger Name
        'age': user.last_name,    # Passenger Age
        'user_groups': user_groups      # User groups (user type)
    }

    # Return the user data as a JSON response
    return JsonResponse(user_data)

@csrf_exempt
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this view
@permission_classes([AllowAny])  # Allow anyone to access this view
def refresh_token(request):
    if request.method == 'POST':
        try:
            # Try to load the request body
            data = json.loads(request.body)
            
            # Validate the presence of the refresh token in the request
            refresh_token = data.get('refresh_token')
            if not refresh_token:
                return JsonResponse({'message': 'Refresh token required'}, status=400)

            # Try to create a RefreshToken object to validate it
            try:
                refresh = RefreshToken(refresh_token)
            except Exception as e:
                # Catch invalid token exceptions and provide an error
                return JsonResponse({'message': 'Invalid refresh token: ' + str(e)}, status=400)

            # Generate a new access token from the valid refresh token
            access_token = str(refresh.access_token)

            return JsonResponse({'access_token': access_token}, status=200)

        except json.JSONDecodeError:
            # Handle invalid JSON body
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            # Catch other unexpected errors
            return JsonResponse({'message': str(e)}, status=400)
    else:
        return JsonResponse({'message': 'Only POST method is allowed.'}, status=405)


@csrf_exempt
@api_view(['POST'])
@authentication_classes([])  # Disable authentication for this view
@permission_classes([AllowAny])
def user_logout(request):
    return JsonResponse({'message': 'Logout successful. Please clear your token on the client side.'}, status=200)

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])  # Only normal users can access this view
def search_buses(request):
    if request.method == 'POST':
        try:
            # Load and validate the request data
            data = json.loads(request.body)
            dep_location = data.get('dep_location')
            dest = data.get('dest')

            # Validate presence of required fields
            if not dep_location or not dest:
                return JsonResponse({'message': 'Both departure location and destination are required.'}, status=400)
            
            # Validate that the departure location and destination are strings
            if not isinstance(dep_location, str) or not isinstance(dest, str):
                return JsonResponse({'message': 'Both departure location and destination must be strings.'}, status=400)

            # Query buses based on the location and destination
            buses = BusDetails.objects.filter(Departure_Location=dep_location)

            # Filter buses based on destination
            buses = buses.filter(Destinations__contains=dest)

            buses_list = [{
                'Bus_No': bus.Bus_No,
                'Departure_Location': bus.Departure_Location,
                'Departure_Date': bus.Departure_Time.date(),
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
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)

    else:
        return JsonResponse({'message': 'Only POST method is allowed.'}, status=405)

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
                return JsonResponse({'message': f'Missing required fields: {", ".join(missing_fields)}'}, status=400)

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
                return JsonResponse({'message': 'Invalid departure_time format. Use YYYY-MM-DDTHH:MM:SS.'}, status=400)

            try:
                # Validate the bus number
                bus_no = int(bus_no)
            except ValueError:
                return JsonResponse({'message': 'Bus number must be an integer.'}, status=400)
            
            # Validate that the destinations and ticket costs are lists
            if not isinstance(destinations, list) or not all(isinstance(dest, str) for dest in destinations):
                return JsonResponse({'message': 'Destinations must be a list of strings.'}, status=400)
            
            if not isinstance(ticket_costs, list) or not all(isinstance(cost, (int, float)) for cost in ticket_costs):
                return JsonResponse({'message': 'Ticket costs must be a list of numbers (integers or floats).'}, status=400)

            # Validate the number of seats
            if not isinstance(seats_available, int) or seats_available < 0:
                return JsonResponse({'message': 'Seats available must be a non-negative integer.'}, status=400)

            # Check if the bus number already exists
            if BusDetails.objects.filter(Bus_No=bus_no).exists():
                return JsonResponse({'message': 'Bus with this number already exists.'}, status=400)

            admin_username = request.user.username
            
            # Create and save the new bus
            bus = BusDetails.objects.create(
                Bus_No=bus_no,
                Departure_Location=departure_location,
                Departure_Time=departure_time,
                Destinations=json.dumps(destinations),  # Store as a JSON string
                Seats_Available=seats_available,
                TicketCosts=json.dumps(ticket_costs),  # Store as a JSON string
                AgencyName=admin_username
            )

            return JsonResponse({'message': 'Bus added successfully', 'bus_no': bus.Bus_No}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'message': 'Invalid JSON data'}, status=400)
        except KeyError as e:
            return JsonResponse({'message': f'Missing required field: {e}'}, status=400)
    else:
        return JsonResponse({'message': 'Only POST method is allowed.'}, status=405)
    
@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAdminUser])  # Only admin users can access this view
def get_user_buses(request):
    try:
        # Get the username of the logged-in admin user
        admin_username = request.user.username
        
        # Filter buses created by the admin (based on AgencyName)
        buses = BusDetails.objects.filter(AgencyName=admin_username)
        
        # If no buses are found, return a message
        if not buses:
            return JsonResponse({'message': 'No buses found for this admin.'}, status=404)
        
        # Create a list of buses to return in the response
        buses_list = []
        for bus in buses:
            buses_list.append({
                'bus_no': bus.Bus_No,
                'departure_location': bus.Departure_Location,
                'departure_time': bus.Departure_Time,
                'destinations': bus.Destinations,
                'seats_available': bus.Seats_Available,
                'ticket_costs': bus.TicketCosts,
                'agency_name': bus.AgencyName,
                'bus_status': bus.BusStatus,
                'driver':bus.Driver
            })
        
        # Return the list of buses in a JSON response
        return JsonResponse({'buses': buses_list}, status=200)

    except Exception as e:
        return JsonResponse({'message': f'Error occurred: {str(e)}'}, status=500)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAdminUser])  # Only admin users can access this view
def get_bus_passengers(request):
    if request.method == 'POST':
        try:
            data = request.data
            bus_no = data.get('bus_no')

            # Check if bus number is provided
            if not bus_no:
                return JsonResponse({'message': 'Bus number is required.'}, status=400)

            # Retrieve the bus details to check if the current user created it
            try:
                bus = BusDetails.objects.get(Bus_No=bus_no)
            except BusDetails.DoesNotExist:
                return JsonResponse({'message': 'Bus not found.'}, status=404)

            # Check if the current user is the one who created the bus
            if bus.AgencyName != request.user.username:
                return JsonResponse({'message': 'Unauthorized access. You did not create this bus.'}, status=403)

            # Retrieve all ticket details for the bus number
            tickets = TicketDetails.objects.filter(Bus_No=bus_no)

            # If no tickets are found for the bus, return an error
            if not tickets.exists():
                return JsonResponse({'message': 'No passengers found for this bus.'}, status=404)

            # Prepare the list of passengers from the ticket data
            passengers_list = []
            for ticket in tickets:
                passengers_list.append({
                    'ticket_no': ticket.Ticket_No,
                    'passenger_name': ticket.Passenger_Name,
                    'passenger_age': ticket.Passenger_Age,
                    'acct_name': ticket.Acct_Name
                })

            # Return the list of passengers in JSON format
            return JsonResponse({'passengers': passengers_list}, status=200)

        except Exception as e:
            return JsonResponse({'message': f'Error occurred: {str(e)}'}, status=500)
        
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAdminUser])  # Only admin users can access this view
def delete_bus(request):
    if request.method == 'POST':
        try:
            # Parse the JSON request body
            data = request.data
            bus_no = data.get('bus_no')  # Get bus number from the request body
            
            # Validate that bus_no is provided
            if not bus_no:
                return JsonResponse({'message': 'Bus number is required.'}, status=400)
            
            # Check if the bus exists in the database
            bus = BusDetails.objects.filter(Bus_No=bus_no).first()
            
            if not bus:
                return JsonResponse({'message': 'Bus not found.'}, status=404)
            
            # Set status to cancelled
            bus.BusStatus = 'Cancelled'
            bus.save()
            
            tickets = TicketDetails.objects.filter(Bus_No = bus_no)
            for ticket in tickets:
                ticket.TicketStatus = 'Cancelled'
                ticket.save()
            
            return JsonResponse({'message': 'Bus cancelled successfully.'}, status=200)
        
        except Exception as e:
            return JsonResponse({'message': f'Error occurred: {str(e)}'}, status=500)
    else:
        return JsonResponse({'message': 'Only POST method is allowed.'}, status=405)
    
@api_view(['POST'])
@permission_classes([IsDriverUser])  # Only drivers can access this view
def assign_bus_to_driver(request):
    # Check if the user is authenticated
    if not request.user.is_authenticated:
        return JsonResponse({'message': 'Authentication required'}, status=401)

    # Extract bus number from the POST request
    bus_no = request.data.get('bus_no')

    if not bus_no:
        return JsonResponse({'message': 'Bus number is required'}, status=400)

    # Find the bus in the database
    try:
        bus = BusDetails.objects.get(Bus_No=bus_no)
    except BusDetails.DoesNotExist:
        return JsonResponse({'message': 'Bus not found'}, status=404)

    # Check if the bus already has a driver assigned
    if bus.Driver != 'None':
        return JsonResponse({'message': f'This bus is already assigned to {bus.Driver}'}, status=400)

    # Assign the driver to the bus by updating the `Driver` field with the username of the logged-in driver
    bus.Driver = request.user.username
    bus.save()

    # Return success response with driver information
    return JsonResponse({
        'message': f'Bus {bus_no} successfully assigned to driver {request.user.username}',
        'bus_no': bus_no,
        'driver': request.user.username
    }, status=200)
    
@csrf_exempt
@api_view(['GET'])
@permission_classes([IsDriverUser])  # Only authenticated drivers can access this
def get_driver_details(request):
    try:
        # Get the driver details based on the authenticated user
        driver_details = DriverDetails.objects.get(Driver_username=request.user.username)

        # Return the driver details in the response
        return JsonResponse({
            'driver_username': driver_details.Driver_username,
            'driver_name': driver_details.Driver_Name,
            'driver_dob': driver_details.Driver_DOB,
            'driver_dl_doe': driver_details.DL_DOE,
            'driver_license_no': driver_details.Driver_License_No,
            'driver_address': driver_details.Driver_Address,
            'driver_contact': driver_details.Driver_Contact
        }, status=200)

    except DriverDetails.DoesNotExist:
        # If no driver details are found for the user, return an error
        return JsonResponse({'message': 'Driver details not found for this user'}, status=404)