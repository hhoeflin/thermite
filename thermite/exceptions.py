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


class NothingProcessedError(Exception):
    pass


class TooFewInputsError(Exception):
    pass


class UnspecifiedParameterError(Exception):
    pass


class UnspecifiedOptionError(UnspecifiedParameterError):
    pass


class UnspecifiedArgumentError(UnspecifiedParameterError):
    pass


class UnspecifiedObjError(Exception):
    pass


class UnprocessedArgumentError(Exception):
    pass


class UnexpectedReturnTypeError(Exception):
    pass


class UnknownArgumentError(Exception):
    pass


class UnknownOptionError(Exception):
    pass
