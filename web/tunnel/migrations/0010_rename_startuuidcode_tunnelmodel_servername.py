# Generated by Django 3.2.12 on 2022-03-31 07:47
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tunnel", "0009_tunnelmodel_svc_port"),
    ]

    operations = [
        migrations.RenameField(
            model_name="tunnelmodel",
            old_name="startuuidcode",
            new_name="servername",
        ),
    ]
