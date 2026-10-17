"""Exercise bootstrap ordering and failures without installing anything."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'setup.sh'


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='macbook-nix-bootstrap-')
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.environment = dict(os.environ, TMPDIR=str(self.folder))

    def shell(self, program, *arguments):
        return subprocess.run(['/bin/bash', '-c',
                               'set -euo pipefail; source "$1"; shift; ' + program,
                               'setup-test', str(SCRIPT), *map(str, arguments)],
                              env=self.environment, text=True, capture_output=True)

    def test_unsupported_system_and_root_stop_before_sudo(self):
        for operating_system, uid in [('Linux', '501'), ('Darwin', '0')]:
            with self.subTest(system=operating_system, uid=uid):
                result = self.shell('''
bootstrap_test_system=$1
bootstrap_test_uid=$2
uname() { if [[ "$1" == -s ]]; then echo "$bootstrap_test_system"; else echo arm64; fi; }
id() { echo "$bootstrap_test_uid"; }
sudo() { echo SHOULD_NOT_RUN; }
setup_main
''', operating_system, uid)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('SHOULD_NOT_RUN', result.stdout)

    def test_command_line_tools_wait_for_installation(self):
        result = self.shell('''
checks=0
command_line_tools_ready() { checks=$((checks + 1)); [[ $checks -ge 3 ]]; }
xcode-select() { echo "xcode-select $*"; }
sleep() { echo waiting; }
ensure_command_line_tools
echo ready
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.count('xcode-select --install'), 1)
        self.assertEqual(result.stdout.count('waiting'), 1)
        self.assertTrue(result.stdout.endswith('ready\n'))

    def test_existing_tools_skip_installers(self):
        result = self.shell('''
command_line_tools_ready() { return 0; }
load_brew() { return 0; }
load_nix() { return 0; }
xcode-select() { echo SHOULD_NOT_RUN; return 9; }
run_installer() { echo SHOULD_NOT_RUN; return 9; }
ensure_command_line_tools
ensure_brew
ensure_nix
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')

    def test_existing_apple_install_request_waits_instead_of_failing(self):
        result = self.shell('''
checks=0
command_line_tools_ready() { checks=$((checks + 1)); [[ $checks -ge 3 ]]; }
xcode-select() { echo 'installation already requested' >&2; return 1; }
sleep() { :; }
ensure_command_line_tools
echo ready
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.endswith('ready\n'))

    def test_piped_entry_runs_preflight_before_any_installation(self):
        tools = self.folder / 'bin'
        tools.mkdir()
        uname = tools / 'uname'
        uname.write_text('#!/bin/sh\necho Linux\n')
        uname.chmod(0o755)
        environment = dict(self.environment, PATH=str(tools) + ':/usr/bin:/bin')
        result = subprocess.run(['/bin/bash'], input=SCRIPT.read_text(),
                                env=environment, text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Apple Silicon Mac is required', result.stderr)

    def test_existing_checkout_preserves_local_files_and_rejects_other_repos(self):
        repository = self.folder / 'checkout'
        subprocess.run(['git', 'init', '-q', str(repository)], check=True)
        for name in ('flake.nix', 'Makefile', 'my-edits'):
            (repository / name).write_text('keep my changes')
        for origin, expected_success in [
                ('https://github.com/ythosa/macbook-nix.git', True),
                ('https://github.com/someone/other.git', False)]:
            subprocess.run(['git', '-C', str(repository), 'config',
                            'remote.origin.url', origin], check=True)
            result = self.shell('checkout_repo "$1"', repository)
            self.assertEqual(result.returncode == 0, expected_success, result.stderr)
            self.assertEqual((repository / 'my-edits').read_text(), 'keep my changes')

    def test_new_installations_are_loaded_in_the_same_shell(self):
        result = self.shell('''
brew_ready=0
nix_ready=0
load_brew() { [[ $brew_ready == 1 ]]; }
load_nix() { [[ $nix_ready == 1 ]]; }
run_installer() {
    case "$1" in
        *Homebrew*) brew_ready=1; echo brew-installed ;;
        *nixos.org*) nix_ready=1; echo nix-installed ;;
        *) return 9 ;;
    esac
}
ensure_brew
ensure_nix
load_brew && load_nix
echo ready
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['brew-installed', 'nix-installed', 'ready'])

    def test_failed_download_never_executes_an_installer(self):
        result = self.shell('''
curl() { return 7; }
run_installer https://example.invalid/install /bin/false
echo SHOULD_NOT_RUN
''')
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('SHOULD_NOT_RUN', result.stdout)
        self.assertEqual(list(self.folder.iterdir()), [])

    def workflow(self, fail_check=False):
        repository = self.folder / 'checkout'
        repository.mkdir()
        (repository / 'flake.nix').touch()
        return self.shell('''
uname() { if [[ "$1" == -s ]]; then echo Darwin; else echo arm64; fi; }
id() { echo 501; }
sudo() { echo sudo; }
ensure_command_line_tools() { echo tools; }
ensure_brew() { echo brew; }
ensure_nix() { echo nix; }
checkout_repo() { echo checkout; }
make() { echo "make $*"; ''' +
                          ('[[ "$1" != check ]];' if fail_check else ':;') + ''' }
setup_main "$1"
''', repository)

    def test_full_workflow_checks_before_activation_and_plugins(self):
        result = self.workflow()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[:8],
                         ['sudo', 'tools', 'brew', 'nix', 'checkout',
                          'make check', 'make switch', 'make plugins'])
        self.assertIn('Setup complete', result.stdout)

    def test_failed_check_stops_before_activation(self):
        result = self.workflow(fail_check=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('make switch', result.stdout)
        self.assertNotIn('plugins', result.stdout)
        self.assertNotIn('Setup complete', result.stdout)


if __name__ == '__main__':
    unittest.main()
