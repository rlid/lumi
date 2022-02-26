class Error(Exception):
    pass


class InvalidActionError(Error):
    pass


class InsufficientFundsError(InvalidActionError):
    pass


class RewardDistributionError(Error):
    pass
