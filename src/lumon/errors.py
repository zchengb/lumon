"""Errors that cross the Lumon CLI interface."""

from __future__ import annotations

from typing import ClassVar


class LumonError(Exception):
    """Base error with a stable process exit code."""

    exit_code: ClassVar[int] = 4


class InvalidInputError(LumonError):
    """The command input cannot be accepted safely."""

    exit_code: ClassVar[int] = 2


class PreflightError(LumonError):
    """The environment or target failed before any write began."""

    exit_code: ClassVar[int] = 3


class InitializationError(LumonError):
    """Initialization failed after validation began."""

    exit_code: ClassVar[int] = 4


class SkillInstallError(InitializationError):
    """A new Skill could not be installed."""
