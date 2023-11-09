from django.db import models


class Blockchain(models.TextChoices):
    TRON = 'TRX'
    BASE = 'BASE'
    SOLANA = 'SOL'
    MATIC = 'MATIC'
    ARBITRUM = 'ARB'
    ETHEREUM = 'ETH'
    ALGORAND = 'ALGO'
    AVALANCHE = 'AVAX'

    def is_evm(self):
        return self not in {Blockchain.TRON, Blockchain.SOLANA, Blockchain.ALGORAND}
