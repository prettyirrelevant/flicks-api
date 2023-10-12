# Generated by Django 4.2.5 on 2023-10-12 08:50

import datetime
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('creators', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Content',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='id'
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='updated at')),
                ('caption', models.TextField(verbose_name='content caption')),
                (
                    'account',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='contents',
                        to='creators.creator',
                        verbose_name='account',
                    ),
                ),
                ('likes', models.ManyToManyField(related_name='likes', to='creators.creator', verbose_name='likes')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Media',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='id'
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='updated at')),
                ('s3_key', models.CharField(max_length=100, verbose_name='file path on s3')),
                ('blur_hash', models.TextField(verbose_name='media blur hash')),
                (
                    'media_type',
                    models.CharField(
                        choices=[('image', 'Image'), ('video', 'Video')], max_length=20, verbose_name='media type'
                    ),
                ),
                (
                    'content',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='media',
                        to='contents.content',
                        verbose_name='content',
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Livestream',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='id'
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='updated at')),
                ('title', models.CharField(max_length=50, verbose_name='title')),
                ('description', models.TextField(verbose_name='description')),
                ('start', models.DateTimeField(verbose_name='start timestamp')),
                (
                    'duration',
                    models.DurationField(
                        validators=[
                            django.core.validators.MinValueValidator(datetime.timedelta(seconds=600)),
                            django.core.validators.MaxValueValidator(datetime.timedelta(seconds=1800)),
                        ],
                        verbose_name='livestream duration',
                    ),
                ),
                (
                    'account',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='livestream',
                        to='creators.creator',
                        verbose_name='account',
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Comment',
            fields=[
                (
                    'id',
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='id'
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='created at')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, verbose_name='updated at')),
                ('message', models.CharField(max_length=200, verbose_name='message')),
                (
                    'author',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='my_comments',
                        to='creators.creator',
                        verbose_name='author',
                    ),
                ),
                (
                    'content',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='comments',
                        to='contents.content',
                        verbose_name='content',
                    ),
                ),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
