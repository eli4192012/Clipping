import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.check_install import validate_pins


class InstallContractTests(unittest.TestCase):
    def check(self, direct, lock, version='1.2'):
        with tempfile.TemporaryDirectory() as temp:
            required = Path(temp) / 'requirements.txt'
            pins = Path(temp) / 'lock.txt'
            required.write_text(direct)
            pins.write_text(lock)
            with patch('scripts.check_install.importlib.metadata.version', return_value=version):
                validate_pins(required, pins)

    def test_missing_direct_dependency_is_caught(self):
        with self.assertRaisesRegex(ValueError, 'Missing direct'):
            self.check('keyring>=25,<26\n', 'requests==2.34.2\n')

    def test_exact_pins_must_satisfy_constraints_and_installed_version(self):
        for lock, version in (('example>=1\n', '1.2'), ('example==2.0\n', '2.0'), ('example==1.2\n', '1.3')):
            with self.assertRaises(ValueError):
                self.check('example>=1,<2\n', lock, version)
        self.check('Some_Package[extra]>=1,<2\n', 'some-package==1.2\n')
