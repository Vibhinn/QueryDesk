class NotAuthenticated(Exception):
    pass

class ChatNotFound(Exception):
    pass

class MessageNotFound(Exception):
    pass

class NoSQLResultToSummarize(Exception):
    pass

class SummaryGenerationFailed(Exception):
    pass

class ServiceUnavailable(Exception):
    pass
