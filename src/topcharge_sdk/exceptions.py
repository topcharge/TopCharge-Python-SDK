class TopChargeApiError(Exception):
    """Raised when TopCharge returns a non-2xx HTTP response."""

    def __init__(self, message: str, status_code: int, response_body: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body
