import sys
import traceback
from typing import Optional, cast


class DocumentPortalException(Exception):
    def __init__(self, error_message, error_details=None):
        norm_msg = str(error_message)

        exc_type = exc_value = exc_tb = None
        if error_details is None:
            exc_type, exc_value, exc_tb = sys.exc_info()
        elif hasattr(error_details, "exc_info"):
            exc_type, exc_value, exc_tb = error_details.exc_info()
        elif isinstance(error_details, BaseException):
            exc_type, exc_value, exc_tb = (
                type(error_details),
                error_details,
                error_details.__traceback__,
            )
        else:
            exc_type, exc_value, exc_tb = sys.exc_info()

        last_tb = exc_tb
        while last_tb and last_tb.tb_next:
            last_tb = last_tb.tb_next

        self.file_name = last_tb.tb_frame.f_code.co_filename if last_tb else "<unknown>"
        self.lineno = last_tb.tb_lineno if last_tb else -1
        self.error_message = norm_msg

        self.traceback_str = (
            ''.join(traceback.format_exception(exc_type, exc_value, exc_tb))
            if exc_type and exc_tb
            else ""
        )

        super().__init__(norm_msg)

    def __str__(self):
        base = f"Error in [{self.file_name}] at line [{self.lineno}] | Message: {self.error_message}"
        return f"{base}\nTraceback:\n{self.traceback_str}" if self.traceback_str else base


#if __name__ == "__main__":
    # Demo-1: generic exception -> wrap
    # try:
    #     a = 1 / 0
    # except Exception as e:
    #     raise DocumentPortalException("Division failed", e) from e

    # Demo-2: still supports sys (old pattern)
    # try:
    #     a = int("abc")
    # except Exception as e:
    #     raise DocumentPortalException(e, sys)