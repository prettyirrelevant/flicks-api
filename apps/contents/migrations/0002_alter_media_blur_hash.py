# Generated by Django 4.2.5 on 2023-10-14 13:04

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('contents', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='media',
            name='blur_hash',
            field=models.TextField(default='', verbose_name='media blur hash'),
        ),
    ]
