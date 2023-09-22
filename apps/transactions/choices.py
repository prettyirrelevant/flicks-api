from django.db import models


class TransactionType(models.TextChoices):
    DEBIT = 'debit'
    CREDIT = 'credit'
    MOVE_TO_MASTER_WALLET = 'move to master wallet'


class TransactionStatus(models.TextChoices):
    PENDING = 'pending'
    FAILED = 'failed'
    SUCCESSFUL = 'successful'
