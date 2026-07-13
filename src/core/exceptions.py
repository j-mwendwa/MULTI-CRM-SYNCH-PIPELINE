class CrmPipelineError(Exception):
    pass


class ApiError(CrmPipelineError):
    def __init__(self, provider: str, status_code: int, detail: str, attempt: int = 0) -> None:
        self.provider = provider
        self.status_code = status_code
        self.detail = detail
        self.attempt = attempt
        super().__init__(f"[{provider}] HTTP {status_code} (attempt {attempt}): {detail}")


class RateLimitError(ApiError):
    pass


class ConfigError(CrmPipelineError):
    pass
