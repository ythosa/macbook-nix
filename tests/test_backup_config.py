import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / 'scripts/backup-config.sh'


class BackupConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)

    def backup(self, path):
        result = subprocess.run(['/bin/sh', str(SCRIPT), str(path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(path.exists())
        self.assertFalse(path.is_symlink())
        directories = self.folder.glob(path.name + '.before-home-manager.*')
        return [directory / path.name for directory in directories]

    def test_repeated_backups_keep_all_versions_and_old_fixed_backup(self):
        path = self.folder / '.zshrc'
        previous = self.folder / '.zshrc.before-home-manager'
        previous.write_text('old backup')
        for content in ('first version', 'second version'):
            path.write_text(content)
            path.chmod(0o640)
            backups = self.backup(path)
        self.assertEqual(sorted(backup.read_text() for backup in backups),
                         ['first version', 'second version'])
        self.assertTrue(all(backup.stat().st_mode & 0o777 == 0o640
                            for backup in backups))
        self.assertEqual(previous.read_text(), 'old backup')

    def test_directory_and_its_symlinks_are_preserved(self):
        path = self.folder / 'app settings'
        path.mkdir()
        (path / 'config').write_text('user settings')
        (path / 'config-link').symlink_to('config')
        (path / 'broken-link').symlink_to('missing')
        backup, = self.backup(path)
        self.assertEqual((backup / 'config').read_text(), 'user settings')
        self.assertEqual((backup / 'config-link').readlink(), Path('config'))
        self.assertEqual((backup / 'broken-link').readlink(), Path('missing'))

    def test_symlink_is_moved_without_touching_its_target(self):
        target = self.folder / 'target'
        target.write_text('keep target')
        for name, link_target in [('linked config', target),
                                  ('broken config', self.folder / 'missing')]:
            with self.subTest(name=name):
                path = self.folder / name
                path.symlink_to(link_target)
                backup, = self.backup(path)
                self.assertTrue(backup.is_symlink())
                self.assertEqual(backup.readlink(), link_target)
                self.assertEqual(target.read_text(), 'keep target')

    def test_missing_source_fails_without_leaving_empty_backup(self):
        result = subprocess.run(['/bin/sh', str(SCRIPT), str(self.folder / 'missing')],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_failed_move_keeps_the_original_and_removes_empty_backup(self):
        path = self.folder / 'config'
        path.write_text('keep original')
        tools = self.folder / 'tools'
        tools.mkdir()
        move = tools / 'mv'
        move.write_text('#!/bin/sh\nexit 7\n')
        move.chmod(0o700)
        environment = dict(os.environ, PATH=str(tools) + ':/usr/bin:/bin')
        result = subprocess.run(['/bin/sh', str(SCRIPT), str(path)],
                                env=environment, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(path.read_text(), 'keep original')
        self.assertEqual(list(self.folder.glob('config.before-home-manager.*')), [])

    def test_sourced_backup_failure_aborts_before_home_manager_can_replace(self):
        for command in ('mktemp', 'mv'):
            with self.subTest(command=command):
                path = self.folder / (command + ' config')
                path.write_text('keep original')
                tools = self.folder / command
                tools.mkdir()
                failing_command = tools / command
                failing_command.write_text('#!/bin/sh\nexit 7\n')
                failing_command.chmod(0o700)
                environment = dict(os.environ,
                                   PATH=str(tools) + ':/usr/bin:/bin',
                                   HOME_MANAGER_BACKUP_COMMAND='source ' + str(SCRIPT))
                result = subprocess.run([
                    '/bin/bash', '-c', '''
run() { "$@"; }
run $HOME_MANAGER_BACKUP_COMMAND "$1" || echo 'Backup failed'
printf 'replacement' > "$1"
''', 'home-manager-backup-test', str(path)],
                    env=environment, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(path.read_text(), 'keep original')
                self.assertNotIn('Backup failed', result.stdout)
                self.assertEqual(list(self.folder.glob(path.name + '.before-home-manager.*')), [])

    def test_repeated_sourced_backups_with_spaces_return_to_caller(self):
        path = self.folder / 'config with spaces'
        environment = dict(os.environ,
                           HOME_MANAGER_BACKUP_COMMAND='source ' + str(SCRIPT))
        result = subprocess.run([
            '/bin/bash', '-c', '''
run() { "$@"; }
for version in 'first version' 'second version'; do
  printf '%s' "$version" > "$1"
  run $HOME_MANAGER_BACKUP_COMMAND "$1" || exit 7
done
printf 'finished'
''', 'home-manager-backup-test', str(path)],
            env=environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'finished')
        self.assertFalse(path.exists())
        backups = [directory / path.name
                   for directory in self.folder.glob(path.name + '.before-home-manager.*')]
        self.assertEqual(sorted(backup.read_text() for backup in backups),
                         ['first version', 'second version'])


if __name__ == '__main__':
    unittest.main()
