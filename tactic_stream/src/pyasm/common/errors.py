from pyasm.common.common_exception import (
    TacticException, ClientTacticException, SetupException, CodeException,
    UserException, SecurityException, SObjectSecurityException, TacticWarning,
)


class UnsupportedContract(Exception):
    """A known TACTIC contract has not been migrated yet."""


class AuthenticationError(Exception):
    """Authentication failed without exposing credential details."""
