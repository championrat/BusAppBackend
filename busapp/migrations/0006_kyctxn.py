# Generated by Django 5.1.4 on 2025-02-05 08:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('busapp', '0005_busdetails_busstatus_busdetails_driver_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='KYCTxn',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_id', models.CharField(max_length=255)),
                ('application_status', models.CharField(max_length=100)),
                ('event_id', models.CharField(max_length=255)),
                ('event_version', models.CharField(max_length=50)),
                ('event_time', models.DateTimeField()),
                ('event_type', models.CharField(max_length=100)),
                ('reviewer_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('duplicate', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
