from enum import Enum
class TransactionType(Enum):
    DEPOSIT = "DEPOSIT"
    TRANSFER = "TRANSFER"
    WITHDRAWAL = "WITHDRAWAL"

class TransactionStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"