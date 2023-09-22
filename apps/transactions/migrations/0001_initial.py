# Generated by Django 4.2.5 on 2023-09-22 11:47

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('accounts', '0003_alter_wallet_provider_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='Transaction',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='id'
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='updated at')),
                ('metadata', models.JSONField(default=dict, verbose_name='metadata')),
                ('narration', models.TextField(blank=True, default='', verbose_name='narration')),
                ('amount', models.DecimalField(decimal_places=6, max_digits=20, verbose_name='amount')),
                ('reference', models.CharField(max_length=200, unique=True, verbose_name='transaction reference')),
                (
                    'status',
                    models.CharField(
                        choices=[('pending', 'Pending'), ('failed', 'Failed'), ('successful', 'Successful')],
                        max_length=10,
                        verbose_name='status',
                    ),
                ),
                (
                    'tx_type',
                    models.CharField(
                        choices=[
                            ('debit', 'Debit'),
                            ('credit', 'Credit'),
                            ('move to master wallet', 'Move To Master Wallet'),
                        ],
                        max_length=30,
                        verbose_name='transaction type',
                    ),
                ),
                (
                    'account',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='transactions',
                        to='accounts.account',
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
