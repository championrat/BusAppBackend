# Generated by Django 5.1.4 on 2025-01-09 09:21

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='BusDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Bus_No', models.IntegerField(unique=True)),
                ('Departure_Location', models.CharField(max_length=100)),
                ('Departure_Time', models.TimeField()),
                ('Destinations', models.CharField(max_length=500)),
                ('Seats_Available', models.IntegerField()),
                ('TicketCosts', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='TicketDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('Ticket_No', models.IntegerField(unique=True)),
                ('Bus_No', models.IntegerField()),
                ('Passenger_Name', models.CharField(max_length=100)),
                ('Passenger_Age', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=100, unique=True)),
                ('password', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=100, unique=True)),
                ('passenger_name', models.CharField(max_length=100)),
                ('passenger_age', models.IntegerField(validators=[django.core.validators.MinValueValidator(0)])),
            ],
        ),
    ]