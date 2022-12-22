class ThermiteException(Exception):
    pass


class UnexpectedTriggerError(Exception):
    pass


class UnmatchedOriginError(Exception):
    pass


class IncorrectNumberArgs(Exception):
    pass


class DuplicatedTriggerError(Exception):
    pass


class TooManyInputsError(Exception):
    pass


class TooFewInputsError(Exception):
    pass


class UnspecifiedParameterError(Exception):
    pass
