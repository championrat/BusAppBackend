# busapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.printbuses, name='home'),
    path('bookticket/', views.bookticket, name='bookticket'),
    path('cancel_ticket/', views.cancel_ticket, name='cancel_ticket'),
    path('retrieve_ticket/', views.RetrieveTicket, name='retrieve_ticket'),
    path('signup/', views.signup, name='signup'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
]
