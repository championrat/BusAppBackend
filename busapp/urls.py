# busapp/urls.py
from django.urls import path
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('api/buses/', views.printbuses, name='api_buses'),
    path('api/book-ticket/', views.bookticket, name='api_book_ticket'),
    path('api/cancel-ticket/', views.cancel_ticket, name='api_cancel_ticket'),
    path('api/retrieve-ticket/', views.RetrieveTicket, name='api_retrieve_ticket'),
    path('api/signup/', views.signup, name='api_signup'),
    path('api/login/', views.user_login, name='api_login'),
    path('api/logout/', views.user_logout, name='api_logout'),
    path('api/search-buses/', views.search_buses, name='api_search_buses'),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]

