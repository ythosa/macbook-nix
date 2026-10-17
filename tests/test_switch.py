import importlib.util
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    'switch', Path(__file__).parents[1] / 'scripts/switch.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InvokingUserTests(unittest.TestCase):
    def test_normal_user_ignores_stale_sudo_and_username_variables(self):
        with patch.object(module.os, 'geteuid', return_value=501), \
                patch.object(module.os, 'getuid', return_value=501), \
                patch.dict(module.os.environ, {'SUDO_UID': '0',
                                              'MACBOOK_NIX_USERNAME': 'root'}), \
                patch.object(module.pwd, 'getpwuid', return_value=
                             SimpleNamespace(pw_name='alice')) as lookup:
            self.assertEqual(module.invoking_username(), 'alice')
        lookup.assert_called_once_with(501)

    def test_sudo_activation_keeps_calling_user_when_environment_is_cleared(self):
        with patch.object(module.os, 'geteuid', return_value=0), \
                patch.dict(module.os.environ, {'SUDO_UID': '502', 'USER': 'root'},
                           clear=True), \
                patch.object(module.pwd, 'getpwuid', return_value=
                             SimpleNamespace(pw_name='bob')), \
                patch.object(module.Path, 'is_file', return_value=True), \
                patch.object(module.sys, 'platform', 'darwin'), \
                patch.object(module.sys, 'argv', ['switch.py', '--apply']), \
                patch.object(module, 'backup_plan', return_value=[]), \
                patch.object(module.subprocess, 'run', return_value=
                             subprocess.CompletedProcess([], 0)) as run:
            self.assertEqual(module.main(), 0)
        command = run.call_args.args[0]
        self.assertEqual(command[:2], ['/usr/bin/env', 'MACBOOK_NIX_USERNAME=bob'])
        self.assertIn('--impure', command)

    def test_direct_root_and_sudo_from_root_are_rejected(self):
        for environment in ({}, {'SUDO_UID': '0'}):
            with self.subTest(environment=environment), \
                    patch.object(module.os, 'geteuid', return_value=0), \
                    patch.dict(module.os.environ, environment, clear=True):
                with self.assertRaisesRegex(ValueError, 'without sudo'):
                    module.invoking_username()


class SwitchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.etc = Path(self.temp.name)

    def installer_file(self, name):
        original = b'# Original system shell config\n'
        source = self.etc / name
        (self.etc / (name + '.backup-before-nix')).write_bytes(original)
        source.write_bytes(module.NIX_INIT + b'\n' + original)
        return source

    def test_only_exact_installer_changes_are_backed_up(self):
        source = self.installer_file('bashrc')
        self.assertEqual(module.backup_plan(self.etc), [
            (source, self.etc / 'bashrc.before-nix-darwin')])
        source.write_bytes(source.read_bytes() + b'# User modification\n')
        self.assertEqual(module.backup_plan(self.etc), [])

    def test_zshrc_is_never_moved_even_with_installer_block(self):
        source = self.installer_file('zshrc')
        (self.etc / 'zshrc.before-nix-darwin').write_text('Previous backup')
        self.assertEqual(module.backup_plan(self.etc), [])
        self.assertTrue(source.exists())

    def test_unmodified_files_and_nix_managed_links_are_untouched(self):
        (self.etc / 'bashrc').write_text('# Stock config\n')
        (self.etc / 'zshrc').symlink_to('/etc/static/zshrc')
        self.assertEqual(module.backup_plan(self.etc), [])

    def test_installer_file_without_original_is_untouched(self):
        source = self.installer_file('bashrc')
        (self.etc / 'bashrc.backup-before-nix').unlink()
        self.assertEqual(module.backup_plan(self.etc), [])
        self.assertTrue(source.exists())

    def test_existing_backup_aborts_entire_plan_before_mutation(self):
        self.installer_file('bashrc')
        (self.etc / 'bashrc.before-nix-darwin').symlink_to('/missing/backup')
        with self.assertRaises(FileExistsError):
            module.backup_plan(self.etc)
        self.assertTrue((self.etc / 'bashrc').exists())

    def test_failed_activation_restores_shell_files_and_keeps_backups(self):
        source = self.installer_file('bashrc')
        content = source.read_bytes()
        source.chmod(0o640)
        with patch.object(module.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 7)):
            self.assertEqual(module.switch(module.backup_plan(self.etc), ['rebuild']), 7)
        self.assertEqual(source.read_bytes(), content)
        self.assertEqual(source.stat().st_mode & 0o777, 0o640)
        self.assertEqual((self.etc / 'bashrc.before-nix-darwin').read_bytes(), content)

    def test_partial_activation_preserves_new_nix_links(self):
        source = self.installer_file('bashrc')

        def activate(command, check):
            source.symlink_to('/etc/static/bashrc')
            return subprocess.CompletedProcess(command, 7)

        with patch.object(module.subprocess, 'run', side_effect=activate):
            self.assertEqual(module.switch(module.backup_plan(self.etc), ['rebuild']), 7)
        self.assertEqual(source.readlink(), Path('/etc/static/bashrc'))
        self.assertTrue((self.etc / 'bashrc.before-nix-darwin').is_file())

    def test_retry_after_failed_activation_reuses_identical_backup(self):
        source = self.installer_file('bashrc')
        content = source.read_bytes()
        with patch.object(module.subprocess, 'run', return_value=
                          subprocess.CompletedProcess([], 7)):
            for _ in range(2):
                self.assertEqual(module.switch(module.backup_plan(self.etc), ['rebuild']), 7)
        self.assertEqual(source.read_bytes(), content)
        self.assertEqual((self.etc / 'bashrc.before-nix-darwin').read_bytes(), content)

    def test_racing_backup_is_never_overwritten(self):
        source = self.installer_file('bashrc')
        plan = module.backup_plan(self.etc)
        backup = self.etc / 'bashrc.before-nix-darwin'
        backup.write_text('Keep me')
        with patch.object(module.subprocess, 'run') as run:
            with self.assertRaises(FileExistsError):
                module.switch(plan, ['rebuild'])
        run.assert_not_called()
        self.assertTrue(source.exists())
        self.assertEqual(backup.read_text(), 'Keep me')


if __name__ == '__main__':
    unittest.main()
