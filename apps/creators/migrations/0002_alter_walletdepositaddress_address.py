# Generated by Django 4.2.5 on 2023-10-13 10:47

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creators', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='walletdepositaddress',
            name='address',
            field=models.CharField(max_length=200, verbose_name='address'),
        ),
    ]