"""Plugin bootstrap tests use isolated fixtures and mock commands, never HOME."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/plugins.sh'


class PluginSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='macbook-nix-plugins-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.commands = self.root / 'bin'
        self.commands.mkdir()
        self.log = self.root / 'commands.log'
        self.user = self.root / 'account'
        self.user.mkdir()
        self.env = dict(os.environ, PATH=str(self.commands) + ':' + os.environ['PATH'],
                        PLUGIN_TEST_LOG=str(self.log), NVIM_LOG_FILE=str(self.root / 'nvim.log'))

    def command(self, name, body):
        path = self.commands / name
        path.write_text('#!/bin/bash\nset -eu\n' + body + '\n')
        path.chmod(0o755)

    def run_function(self, name, *arguments):
        # HOME is inherited unchanged. Functions receive an explicit fixture path.
        return subprocess.run(['/bin/bash', '-c', 'source "$1"; shift; "$@"',
                               'plugins-test', str(SCRIPT), name, *map(str, arguments)],
                              env=self.env, text=True, capture_output=True)

    def git_mock(self, failure=False):
        self.command('git', 'printf "%s\\n" "$*" >> "$PLUGIN_TEST_LOG"\n' +
                     ('destination="${@: -1}"\nmkdir -p "$destination"\necho partial > "$destination/incomplete"\nexit 7' if failure else
                      'destination="${@: -1}"\nmkdir -p "$destination/.git"'))

    def git(self, directory, *arguments):
        return subprocess.run(['git', '-C', str(directory), *map(str, arguments)],
                              env=self.env, text=True, capture_output=True, check=True)

    def nvim_repository(self):
        repository = self.root / 'upstream'
        repository.mkdir()
        self.env.update(
            GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_ALLOW_PROTOCOL='file',
            GIT_CONFIG_COUNT='1',
            GIT_CONFIG_KEY_0='url.' + repository.as_uri() + '.insteadOf',
            GIT_CONFIG_VALUE_0='https://github.com/ythosa/nvim-config.git',
        )
        self.git(repository, 'init', '--quiet', '--template=')
        (repository / 'init.lua').write_text('-- upstream init\n')
        (repository / 'lua').mkdir()
        (repository / 'lua/options.lua').write_text('return {}\n')
        self.git(repository, 'add', '.')
        self.git(repository, '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 'commit', '--quiet', '-m', 'Fixture configuration')
        return repository

    def assert_no_nvim_staging(self, config_home):
        self.assertEqual(list(config_home.glob('.macbook-nix-nvim.*')), [])
        self.assertEqual(list(config_home.glob('.macbook-nix-plugin.*')), [])

    def test_missing_checkout_is_cloned(self):
        self.git_mock()
        destination = self.user / 'plugin'
        result = self.run_function('clone_missing', 'https://github.com/example/plugin.git', destination)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((destination / '.git').is_dir())
        self.assertIn('clone --filter=blob:none https://github.com/example/plugin.git', self.log.read_text())

    def test_existing_checkout_and_local_edits_are_preserved(self):
        self.git_mock()
        destination = self.user / 'plugin'
        (destination / '.git').mkdir(parents=True)
        local = destination / 'local.txt'
        local.write_text('my edits')
        result = self.run_function('clone_missing', 'https://github.com/example/plugin.git', destination)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(local.read_text(), 'my edits')
        self.assertFalse(self.log.exists())

    def test_non_checkout_is_not_replaced(self):
        self.git_mock()
        destination = self.user / 'plugin'
        destination.mkdir()
        result = self.run_function('clone_missing', 'https://github.com/example/plugin.git', destination)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not a Git checkout', result.stderr)
        self.assertFalse(self.log.exists())

    def test_clone_failure_is_propagated(self):
        self.git_mock(failure=True)
        result = self.run_function('clone_missing', 'https://github.com/example/plugin.git', self.user / 'plugin')
        self.assertEqual(result.returncode, 7)
        self.assertEqual(len(self.log.read_text().splitlines()), 3)
        self.assertFalse((self.user / 'plugin').exists())
        self.assertEqual(list(self.user.glob('.macbook-nix-plugin.*')), [])

    def test_vim_installs_without_update_and_checks_startup(self):
        self.git_mock()
        self.command('vim', 'printf "%s\\n" "$*" >> "$PLUGIN_TEST_LOG"\n'
                           'if [[ "$*" == *"-Nu NONE"* ]]; then cat >> "$PLUGIN_TEST_LOG"; fi')
        result = self.run_function('install_vim_plugins', self.user)
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.log.read_text()
        self.assertIn('vundle#installer#install(0, plugin.name_spec)', log)
        self.assertNotIn('PluginUpdate', log)
        self.assertIn('-Nu ' + str(self.user / '.vimrc'), log)

    def test_vim_install_failure_stops_bootstrap(self):
        self.git_mock()
        self.command('vim', 'exit 5')
        result = self.run_function('install_vim_plugins', self.user)
        self.assertEqual(result.returncode, 5)

    def test_tmux_installer_uses_and_cleans_an_isolated_server(self):
        tpm = self.user / '.tmux/plugins/tpm'
        (tpm / '.git').mkdir(parents=True)
        (tpm / 'bin').mkdir()
        installer = tpm / 'bin/install_plugins'
        installer.write_text('#!/bin/bash\nprintf "TMUX=%s\\n" "$TMUX" >> "$PLUGIN_TEST_LOG"\nexit 9\n')
        installer.chmod(0o755)
        self.command('tmux', 'printf "%s\\n" "$*" >> "$PLUGIN_TEST_LOG"')
        result = self.run_function('install_tmux_plugins', self.user)
        self.assertEqual(result.returncode, 9, result.stderr)
        log = self.log.read_text()
        self.assertIn('-f /dev/null new-session', log)
        self.assertIn('TMUX_PLUGIN_MANAGER_PATH ' + str(self.user / '.tmux/plugins') + '/', log)
        self.assertIn('TMUX=', log)
        self.assertIn('kill-server', log)

    def test_nvim_honors_xdg_and_does_not_sync_or_update(self):
        self.command('nvim', 'printf "CONFIG=%s\\nDATA=%s\\n%s\\n" '
                            '"$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$*" >> "$PLUGIN_TEST_LOG"')
        config, data = self.root / 'config', self.root / 'data'
        result = self.run_function('install_nvim_plugins', config, data)
        self.assertEqual(result.returncode, 0, result.stderr)
        log = self.log.read_text()
        self.assertIn('CONFIG=' + str(config), log)
        self.assertIn('DATA=' + str(data), log)
        self.assertIn('has_errors()', log)
        self.assertIn('.install({wait=true,show=false,clear=false,lockfile=true})', log)
        self.assertNotIn('.sync(', log)

    def test_nvim_config_is_cloned_as_a_real_checkout(self):
        upstream = self.nvim_repository()
        config_home = self.user / 'config'
        destination = config_home / 'nvim'
        result = self.run_function('ensure_nvim_config', config_home)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((destination / '.git').is_dir())
        self.assertEqual(self.git(destination, 'config', '--get', 'remote.origin.url').stdout.strip(),
                         'https://github.com/ythosa/nvim-config.git')
        self.assertEqual(self.git(destination, 'config', '--get', 'remote.origin.pushurl').stdout.strip(),
                         'git@github.com:ythosa/nvim-config.git')
        self.assertEqual(self.git(destination, 'rev-parse', 'HEAD').stdout,
                         self.git(upstream, 'rev-parse', 'HEAD').stdout)
        self.assertEqual(self.git(destination, 'status', '--porcelain').stdout, '')
        self.assertEqual(list(config_home.glob('nvim.before-git.*')), [])
        self.assert_no_nvim_staging(config_home)

    def test_nvim_directory_adoption_preserves_edits_deletions_permissions_and_symlinks(self):
        upstream = self.nvim_repository()
        config_home = self.user / 'config'
        destination = config_home / 'nvim'
        destination.mkdir(parents=True)
        (destination / 'init.lua').write_text('-- my init\n')
        (destination / 'init.lua').chmod(0o640)
        (destination / '.personal').write_text('keep this untracked file\n')
        (destination / 'linked.lua').symlink_to(destination / '.personal')
        original_inode = (destination / 'init.lua').stat().st_ino

        result = self.run_function('ensure_nvim_config', config_home)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((destination / 'init.lua').read_text(), '-- my init\n')
        self.assertEqual((destination / 'init.lua').stat().st_mode & 0o777, 0o640)
        self.assertEqual((destination / 'init.lua').stat().st_ino, original_inode)
        self.assertEqual((destination / '.personal').read_text(), 'keep this untracked file\n')
        self.assertTrue((destination / 'linked.lua').is_symlink())
        self.assertEqual((destination / 'linked.lua').readlink(), destination / '.personal')
        self.assertFalse((destination / 'lua/options.lua').exists())
        self.assertEqual(self.git(destination, 'rev-parse', 'HEAD').stdout,
                         self.git(upstream, 'rev-parse', 'HEAD').stdout)
        self.assertEqual(self.git(destination, 'config', '--get', 'remote.origin.url').stdout.strip(),
                         'https://github.com/ythosa/nvim-config.git')
        self.assertEqual(self.git(destination, 'config', '--get', 'remote.origin.pushurl').stdout.strip(),
                         'git@github.com:ythosa/nvim-config.git')
        status = self.git(destination, 'status', '--porcelain').stdout
        self.assertIn(' M init.lua\n', status)
        self.assertIn(' D lua/options.lua\n', status)
        self.assertIn('?? .personal\n', status)
        self.assertEqual(list(config_home.glob('nvim.before-git.*')), [])
        self.assert_no_nvim_staging(config_home)

        repeated = self.run_function('ensure_nvim_config', config_home)
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(self.git(destination, 'status', '--porcelain').stdout, status)
        self.assertEqual((destination / 'init.lua').stat().st_ino, original_inode)
        self.assertEqual(list(config_home.glob('nvim.before-git.*')), [])

    def test_nvim_existing_canonical_checkout_keeps_dirty_index_and_files(self):
        upstream = self.nvim_repository()
        origins = (
            'https://github.com/ythosa/nvim-config.git',
            'https://github.com/ythosa/nvim-config',
            'git@github.com:ythosa/nvim-config',
            'git@github.com:ythosa/nvim-config.git',
            'ssh://git@github.com/ythosa/nvim-config',
            'ssh://git@github.com/ythosa/nvim-config.git',
        )
        for index, origin in enumerate(origins):
            with self.subTest(origin=origin):
                config_home = self.user / str(index)
                destination = config_home / 'nvim'
                config_home.mkdir()
                self.git(config_home, 'clone', '--quiet', '--template=', upstream.as_uri(), destination)
                self.git(destination, 'remote', 'set-url', 'origin', origin)
                (destination / 'init.lua').write_text('-- staged edit\n')
                self.git(destination, 'add', 'init.lua')
                (destination / 'init.lua').write_text('-- unstaged edit\n')
                (destination / 'personal.lua').write_text('-- untracked edit\n')
                status = self.git(destination, 'status', '--porcelain').stdout
                head = self.git(destination, 'rev-parse', 'HEAD').stdout
                git_config = (destination / '.git/config').read_bytes()

                result = self.run_function('ensure_nvim_config', config_home)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.git(destination, 'status', '--porcelain').stdout, status)
                self.assertEqual(self.git(destination, 'show', ':init.lua').stdout, '-- staged edit\n')
                self.assertEqual((destination / 'init.lua').read_text(), '-- unstaged edit\n')
                self.assertEqual((destination / 'personal.lua').read_text(), '-- untracked edit\n')
                self.assertEqual(self.git(destination, 'rev-parse', 'HEAD').stdout, head)
                self.assertEqual((destination / '.git/config').read_bytes(), git_config)
                self.assertFalse((destination / '.git/FETCH_HEAD').exists())
                self.assertEqual(list(config_home.glob('nvim.before-git.*')), [])
                self.assert_no_nvim_staging(config_home)

    def test_nvim_foreign_checkout_is_rejected_unchanged(self):
        upstream = self.nvim_repository()
        config_home = self.user / 'config'
        destination = config_home / 'nvim'
        config_home.mkdir()
        self.git(config_home, 'clone', '--quiet', '--template=', upstream.as_uri(), destination)
        origin = 'https://github.com/ythosa/nvim-config.git.evil'
        self.git(destination, 'remote', 'set-url', 'origin', origin)
        (destination / 'init.lua').write_text('-- keep foreign edits\n')
        status = self.git(destination, 'status', '--porcelain').stdout
        head = self.git(destination, 'rev-parse', 'HEAD').stdout

        result = self.run_function('ensure_nvim_config', config_home)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git(destination, 'config', '--get', 'remote.origin.url').stdout.strip(), origin)
        self.assertEqual(self.git(destination, 'status', '--porcelain').stdout, status)
        self.assertEqual(self.git(destination, 'rev-parse', 'HEAD').stdout, head)
        self.assertEqual((destination / 'init.lua').read_text(), '-- keep foreign edits\n')
        self.assertEqual(list(config_home.glob('nvim.before-git.*')), [])
        self.assert_no_nvim_staging(config_home)

    def test_nvim_clone_failure_leaves_existing_directory_without_backup(self):
        self.git_mock(failure=True)
        self.command('sleep', ':')
        config_home = self.user / 'config'
        destination = config_home / 'nvim'
        destination.mkdir(parents=True)
        (destination / 'init.lua').write_text('-- keep original\n')

        result = self.run_function('ensure_nvim_config', config_home)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((destination / 'init.lua').read_text(), '-- keep original\n')
        self.assertEqual([p.name for p in destination.iterdir()], ['init.lua'])
        self.assertEqual(list(config_home.glob('nvim.before-git.*')), [])
        self.assert_no_nvim_staging(config_home)

    def test_nvim_file_and_symlink_destinations_are_rejected_unchanged(self):
        self.git_mock()
        target = self.root / 'target'
        target.mkdir()
        (target / 'init.lua').write_text('-- original target\n')

        for kind in ('file', 'symlink', 'dangling-symlink'):
            with self.subTest(kind=kind):
                config_home = self.user / kind
                config_home.mkdir()
                destination = config_home / 'nvim'
                if kind == 'file':
                    destination.write_text('keep original file\n')
                else:
                    destination.symlink_to(target if kind == 'symlink' else self.root / 'missing')

                result = self.run_function('ensure_nvim_config', config_home)
                self.assertNotEqual(result.returncode, 0)
                if kind == 'file':
                    self.assertEqual(destination.read_text(), 'keep original file\n')
                else:
                    self.assertTrue(destination.is_symlink())
                    self.assertEqual(destination.readlink(), target if kind == 'symlink' else self.root / 'missing')
                self.assertEqual((target / 'init.lua').read_text(), '-- original target\n')
                self.assertEqual(list(config_home.glob('nvim.before-git.*')), [])
                self.assert_no_nvim_staging(config_home)

        self.assertFalse(self.log.exists())

    def test_nvim_checkout_is_prepared_before_plugin_installation(self):
        program = '''source "$1"
install_vim_plugins() { printf 'vim\\n'; }
install_tmux_plugins() { printf 'tmux\\n'; }
ensure_nvim_config() { printf 'config=%s\\n' "$1"; }
install_nvim_plugins() { printf 'plugins=%s|%s\\n' "$1" "$2"; }
setup_plugins "$2"
'''
        config_home, data_home = self.root / 'config', self.root / 'data'
        env = dict(self.env, XDG_CONFIG_HOME=str(config_home), XDG_DATA_HOME=str(data_home))
        result = subprocess.run(['/bin/bash', '-c', program, 'plugins-test', str(SCRIPT), str(self.user)],
                                env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(),
                         ['config=' + str(config_home), 'vim', 'tmux',
                          'plugins=' + str(config_home) + '|' + str(data_home)])

    def test_public_git_overrides_are_local_and_home_is_unchanged(self):
        # Replace setup stages with assertions, so no tools or home files run.
        program = '''source "$1"
install_vim_plugins() {
  [[ ":$PATH:" == *":/etc/profiles/per-user/$(id -un)/bin:"* ]] || exit 1
  [[ ":$PATH:" == *":$1/go/bin:"* ]] || exit 1
  [[ ":$PATH:" == *":$1/.local/bin:"* ]] || exit 1
  printf '%s\\n' "$GIT_CONFIG_GLOBAL|$GIT_CONFIG_NOSYSTEM|$GIT_TERMINAL_PROMPT|$HOME"
}
install_tmux_plugins() { :; }
ensure_nvim_config() { :; }
install_nvim_plugins() { :; }
setup_plugins "$2"
printf 'after=%s\\n' "${GIT_CONFIG_GLOBAL-unset}"
'''
        env = dict(self.env)
        env.pop('GIT_CONFIG_GLOBAL', None)
        result = subprocess.run(['/bin/bash', '-c', program, 'plugins-test', str(SCRIPT), str(self.user)],
                                env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(),
                         ['/dev/null|1|0|' + os.environ['HOME'], 'after=unset'])

    @unittest.skipUnless(shutil.which('nvim'), 'Neovim is not installed yet')
    def test_real_nvim_reports_a_missing_plugin_manager_as_failure(self):
        config = self.root / 'config/nvim'
        config.mkdir(parents=True)
        # Run our own fixture Lua only; do not download or execute any plugins.
        (config / 'init.lua').write_text('error("simulated bootstrap failure")\n')
        for name in ('state', 'cache', 'data'):
            (self.root / name).mkdir()
        self.env.update(XDG_STATE_HOME=str(self.root / 'state'),
                        XDG_CACHE_HOME=str(self.root / 'cache'))
        result = self.run_function('install_nvim_plugins', config.parent, self.root / 'data')
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn('simulated bootstrap failure', result.stderr)

    @unittest.skipUnless(shutil.which('nvim'), 'Neovim is not installed yet')
    def test_real_nvim_reports_plugin_task_failure(self):
        config = self.root / 'config/nvim'
        config.mkdir(parents=True)
        (config / 'init.lua').write_text('''
package.preload["lazy"] = function()
  return {install = function(opts) assert(opts.wait and not opts.clear) end}
end
package.preload["lazy.manage.checker"] = function()
  return {has_errors = function() return true end}
end
''')
        for name in ('state', 'cache', 'data'):
            (self.root / name).mkdir()
        self.env.update(XDG_STATE_HOME=str(self.root / 'state'),
                        XDG_CACHE_HOME=str(self.root / 'cache'))
        result = self.run_function('install_nvim_plugins', config.parent, self.root / 'data')
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertIn('Neovim plugin installation failed', result.stderr)


if __name__ == '__main__':
    unittest.main()
