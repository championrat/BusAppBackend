from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    # Publicly accessible endpoints
    path('api/buses/', views.printbuses, name='api_buses'),
    path('api/signup/', views.signup, name='api_signup'),
    path('api/login/', views.user_login, name='api_login'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/retrieve-ticket/', views.get_ticket_details, name='api_retrieve_ticket'),
    path('api/test/', views.testAPI, name='api_test'),
    path('api/kyc-webhook/', views.kyc_webhook, name='api_webhook'),

    # Protected endpoints (authentication required)
    path('api/book-ticket/', views.bookticket, name='api_book_ticket'),
    path('api/cancel-ticket/', views.cancel_ticket, name='api_cancel_ticket'),
    path('api/logout/', views.user_logout, name='api_logout'),
    path('api/search-buses/', views.search_buses, name='api_search_buses'),
    path('api/add-bus/', views.add_bus, name='api_add_bus'),
    path('api/user/tickets/', views.get_user_tickets, name='get_user_tickets'),
    path('api/user/info/', views.get_user_info, name='get_user_info'),
    path('api/user/buses/', views.get_user_buses, name='get_user_buses'),
    path('api/bus/passengers/', views.get_bus_passengers, name='get_bus_passengers'),
    path('api/delete-bus/', views.delete_bus, name='delete_bus'),
    path('api/assign-bus/', views.assign_bus_to_driver, name='assign_bus'),
    path('api/driver/get-details/', views.get_driver_details, name='driver_details'),
    path('api/driver-kyc/', views.driver_kyc, name='driver_kyc'),
    path('api/app-token/', views.get_appToken, name='app_token'),
    path('api/sdk-kyc/', views.sdk_kyc, name='sdk_kyc'),
]
