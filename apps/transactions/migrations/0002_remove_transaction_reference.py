# Generated by Django 4.2.5 on 2023-10-15 15:43

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('transactions', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='reference',
        ),
    ]