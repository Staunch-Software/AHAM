import logging
import re
import sys

from pythonjsonlogger import jsonlogger

# API keys travel in query strings (Google: `?key=...`). They must never reach a log line, not even inside an
# exception message (httpx puts the full URL in HTTPStatusError).
_SECRET_PARAM = re.compile(r"(?i)([?&](?:key|api_key|apikey|token|access_token)=)[^&\s\"'<>]+")


def redact(text: str) -> str:
    return _SECRET_PARAM.sub(r"\1REDACTED", text)


class RedactSecrets(logging.Filter):
    """Scrubs secret query parameters from the message and from every string field attached to the record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        for name, value in list(record.__dict__.items()):
            if isinstance(value, str) and name not in ("msg", "name", "levelname"):
                record.__dict__[name] = redact(value)
        if record.exc_info:  # tracebacks of httpx errors embed the request URL
            record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
        return True


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    handler.addFilter(RedactSecrets())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)
    # httpx logs every request URL at INFO; for Google that URL contains the API key and adds nothing we need.
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
