# Generated by Django 3.2.10 on 2021-12-22 11:03
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tunnel", "0002_remotemodel"),
    ]

    operations = [
        migrations.RenameField(
            model_name="remotemodel",
            old_name="date",
            new_name="last_update",
        ),
    ]