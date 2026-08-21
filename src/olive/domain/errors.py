from __future__ import annotations


class DomainError(Exception):
    code = "DOMAIN_ERROR"


class DomainNotFound(DomainError):
    code = "NOT_FOUND"


class DomainConflict(DomainError):
    code = "CONFLICT"


class DomainValidationError(DomainError):
    code = "VALIDATION_ERROR"
