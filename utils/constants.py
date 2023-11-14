from decimal import Decimal

ZERO = Decimal('0.00')
ONE_MEGABYTE = 1_024_000
NONCE_DURATION = 600_000
MAX_IMAGE_FILE_SIZE = 5 * ONE_MEGABYTE
MAX_VIDEO_FILE_SIZE = 200 * ONE_MEGABYTE
MINIMUM_ALLOWED_DEPOSIT_AMOUNT = Decimal('1.00')
PERCENTAGE_CUT_FROM_WITHDRAWALS = Decimal('0.9')
MINIMUM_ALLOWED_WITHDRAWAL_AMOUNT = Decimal('5.00')
