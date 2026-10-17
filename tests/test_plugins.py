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
                        PLUGIN_TEST_LOG=str(self.log))

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
                     ('exit 7' if failure else
                      'destination="${@: -1}"\nmkdir -p "$destination/.git"'))

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
        self.assertIn('.install({wait=true,show=false,clear=false})', log)
        self.assertNotIn('.sync(', log)

    def test_public_git_overrides_are_local_and_home_is_unchanged(self):
        # Replace setup stages with assertions, so no tools or home files run.
        program = '''source "$1"
install_vim_plugins() { printf '%s\\n' "$GIT_CONFIG_GLOBAL|$GIT_CONFIG_NOSYSTEM|$GIT_TERMINAL_PROMPT|$HOME"; }
install_tmux_plugins() { :; }
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
