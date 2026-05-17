# custom_exceptions.py

class TaskProcessingError(Exception):
    """Base exception for task processing errors."""
    pass

class DatabaseConnectionError(TaskProcessingError):
    """Raised when there is an issue connecting to the database."""
    pass

class TaskValidationError(TaskProcessingError):
    """Raised when a task fails validation."""
    pass

class DatabaseUpdateError(TaskProcessingError):
    """Raised when there is an issue updating the database."""
    pass

class INIFileReadError(TaskProcessingError):
    """Raised when there is an issue reading the INI file."""
    pass

class TaskProcessingException(TaskProcessingError):
    """Raised when there is a general task processing error."""
    pass

class BaseCustomException(Exception):
    """Base exception for task processing errors."""
    pass

class CustomException_CaseStop(TaskProcessingError):
    """Raised when a case status or phase is invalid."""
    pass

class CustomException_Stop(TaskProcessingError):
    """Raised when to stop processing."""
    pass

class CustomException_Ignore(TaskProcessingError):
    """Raised when some error to be ignored."""
    pass