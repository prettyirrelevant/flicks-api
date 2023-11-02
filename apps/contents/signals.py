from django.dispatch import receiver
from django.db.models.signals import post_save

from .models import Media
from .choices import MediaType
from .tasks import fetch_blurhash_for_image


@receiver(post_save, sender=Media)
def get_blurhash(sender, instance, created, **kwargs):
    if not created:
        return

    if instance.media_type != MediaType.IMAGE:
        return

    fetch_blurhash_for_image.schedule((instance.id,), delay=1)
