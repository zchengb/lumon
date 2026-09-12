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


class WorkspaceNotFoundError(LumonError):
    """A requested Workspace is not present in the user's registry."""

    exit_code: ClassVar[int] = 4


class InitializationError(LumonError):
    """Initialization failed after validation began."""

    exit_code: ClassVar[int] = 4


class SkillInstallError(InitializationError):
    """A new Skill could not be installed."""


class RepositoryError(InitializationError):
    """A Repository could not be inspected, cloned, or verified."""


class UpdateError(LumonError):
    """A Lumon update could not be checked or applied."""

    exit_code: ClassVar[int] = 4


class AgentError(LumonError):
    """Base error for the Mark Agent lifecycle and message path."""


class AgentConfigError(AgentError):
    """Mark Agent configuration is missing, invalid, or unsafe to use."""

    exit_code: ClassVar[int] = 3


class AgentRuntimeError(AgentError):
    """Mark Agent could not start or complete a runtime operation."""
