from io import BytesIO

import blurhash
import requests
from huey import crontab
from huey.contrib.djhuey import db_task, lock_task, db_periodic_task

from django.db import transaction

from apps.contents.models import Media
from apps.contents.choices import MediaType


@db_task()
def fetch_blurhash_for_image(media_id):
    with transaction.atomic():
        media = Media.objects.get(id=media_id)
        response = requests.get(media.url, stream=True, timeout=10)
        if not response.ok:
            return

        media.blur_hash = blurhash.encode(image=BytesIO(response.content), x_components=6, y_components=4)
        media.save()


@db_periodic_task(crontab(minute='*/10'))
@lock_task('fetch-blurhash-for-images-lock')
def fetch_blurhash_for_images():
    for media in Media.objects.filter(blur_hash='').exclude(media_type=MediaType.VIDEO):
        fetch_blurhash_for_image.schedule((media.id,), delay=1)
