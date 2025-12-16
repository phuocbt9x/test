import re
from typing import Any, Dict, Set


class DataMasker:
    MASK_VALUE = "***MASKED***"

    def __init__(
        self,
        sensitive_headers: Set[str],
        sensitive_fields: Set[str],
    ):
        self.sensitive_headers = {h.lower() for h in sensitive_headers}
        self.sensitive_fields = {f.lower() for f in sensitive_fields}

    def mask_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        masked = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                masked[key] = self.MASK_VALUE
            else:
                masked[key] = value
        return masked

    def mask_dict(
        self,
        data: Dict[str, Any],
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        if max_depth <= 0 or not isinstance(data, dict):
            return dict(data) if isinstance(data, dict) else {}

        masked: Dict[str, Any] = {}
        for key, value in data.items():
            if key.lower() in self.sensitive_fields:
                masked[key] = self.MASK_VALUE
            elif isinstance(value, dict):
                masked[key] = self.mask_dict(value, max_depth - 1)
            elif isinstance(value, list):
                masked[key] = [
                    self.mask_dict(item, max_depth - 1)
                    if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                masked[key] = value
        return masked

    def mask_string(self, text: str) -> str:
        text = re.sub(
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "***EMAIL***",
            text,
        )
        text = re.sub(r"\b[A-Za-z0-9_-]{32,}\b", "***KEY***", text)
        text = re.sub(
            r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b",
            "***CARD***",
            text,
        )
        text = re.sub(
            r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*",
            "***JWT***",
            text,
        )

        return text
