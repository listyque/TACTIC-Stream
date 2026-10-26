"""No plaintext provider storage or credential export; host/account binding."""
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

try:
    from tactic_stream import provider_credentials as vault
except ImportError:
    vault = None


@unittest.skipIf(vault is None, 'Install tactic-stream[agent] for provider credential checks')
class Credentials(unittest.TestCase):
    def test_at_rest_round_trip_and_unknown_storage_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            key = Path(directory) / 'vault.key'
            key.write_bytes(vault.Fernet.generate_key())
            key.chmod(0o600)
            with patch.dict(os.environ, TACTIC_AGENT_VAULT_KEY_FILE=str(key)):
                value = vault.seal('private-fixture-api-key')
                self.assertNotIn('private-fixture-api-key', value)
                self.assertEqual(vault.unseal(value), 'private-fixture-api-key')
                with self.assertRaises(ValueError):
                    vault.unseal('private-fixture-api-key')

    def test_only_bound_host_and_scope_can_open_envelope(self):
        private, public = vault.new_host_key()
        other, _ = vault.new_host_key()
        secret = 'private-fixture-api-key' * 200
        envelope = vault.host_envelope(secret, public, 'account:host:profile')
        self.assertNotIn(secret, str(envelope))
        self.assertEqual(vault.host_secret(envelope, private, 'account:host:profile'), secret)
        with self.assertRaises(ValueError):
            vault.host_secret(envelope, other, 'account:host:profile')
        with self.assertRaises(ValueError):
            vault.host_secret(envelope, private, 'other-account:host:profile')

    def test_invalid_host_key_and_unconfigured_linux_vault_refused(self):
        with self.assertRaises(ValueError):
            vault.public_key('not a public key')
        with patch.dict(os.environ, {}, clear=True), self.assertRaisesRegex(ValueError, 'vault key file'):
            vault._fernet()


if __name__ == '__main__':
    unittest.main()
