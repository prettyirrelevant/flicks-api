# Generated by Django 4.2.5 on 2023-10-16 15:55

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('creators', '0002_alter_walletdepositaddress_address'),
    ]

    operations = [
        migrations.AlterField(
            model_name='walletdepositaddress',
            name='blockchain',
            field=models.CharField(
                choices=[
                    ('TRX', 'Tron'),
                    ('BASE', 'Base'),
                    ('SOL', 'Solana'),
                    ('MATIC', 'Matic'),
                    ('ARB', 'Arbitrum'),
                    ('ETH', 'Ethereum'),
                    ('ALGO', 'Algorand'),
                    ('AVAX', 'Avalanche'),
                ],
                max_length=100,
                verbose_name='blockchain',
            ),
        ),
    ]
