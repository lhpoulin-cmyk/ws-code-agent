"""Disabled candidate adapter for one exact Markdown JSON fence wrapper."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re


ADAPTER_ID = "SINGLE_MARKDOWN_JSON_FENCE_NORMALIZATION_V1"
ADAPTER_VERSION = "v1"
STRICT_RAW = "STRICT_RAW"
NORMALIZATION_CANDIDATE = "NORMALIZATION_CANDIDATE"

_FENCE = re.compile(
    rb"\A(?P<leading>[ \t\r\n]*)"
    rb"(?P<opening>```(?:json)?)(?:\r\n|\n)"
    rb"(?P<payload>.*?)"
    rb"(?:\r\n|\n)```"
    rb"(?P<trailing>[ \t\r\n]*)\Z",
    re.DOTALL,
)


@dataclass(frozen=True)
class NormalizationResult:
    """Raw evidence and parser input remain independently addressable."""

    raw_model_response: bytes
    normalized_parser_input: bytes
    adapter_id: str
    adapter_version: str
    transformation_applied: bool
    transformation_classification: str
    raw_sha256: str
    normalized_sha256: str
    input_byte_count: int
    output_byte_count: int

    def evidence(self) -> dict[str, object]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "transformation_applied": self.transformation_applied,
            "transformation_classification": self.transformation_classification,
            "raw_sha256": self.raw_sha256,
            "normalized_sha256": self.normalized_sha256,
            "input_byte_count": self.input_byte_count,
            "output_byte_count": self.output_byte_count,
        }


def normalize_single_markdown_json_fence(raw_model_response: bytes) -> NormalizationResult:
    """Remove only a whole-response unlabeled or lowercase-json fence."""

    if not isinstance(raw_model_response, bytes):
        raise TypeError("raw model response must be bytes")
    match = _FENCE.fullmatch(raw_model_response)
    if match is not None and b"```" not in match.group("payload"):
        normalized = match.group("payload")
        applied = True
        classification = "SINGLE_MARKDOWN_JSON_FENCE_REMOVED"
    else:
        normalized = raw_model_response
        applied = False
        classification = (
            "NORMALIZATION_REFUSED"
            if b"```" in raw_model_response
            else "IDENTITY_NO_PERMITTED_WRAPPER"
        )
    return NormalizationResult(
        raw_model_response=raw_model_response,
        normalized_parser_input=normalized,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
        transformation_applied=applied,
        transformation_classification=classification,
        raw_sha256=hashlib.sha256(raw_model_response).hexdigest(),
        normalized_sha256=hashlib.sha256(normalized).hexdigest(),
        input_byte_count=len(raw_model_response),
        output_byte_count=len(normalized),
    )
