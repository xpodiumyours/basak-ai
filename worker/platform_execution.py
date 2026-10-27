"""Cloud workspaces and gVisor-isolated command execution; never a host shell.

https://gvisor.dev/docs/user_guide/faq/
https://www.kimi.com/code/docs/en/kimi-code-cli/guides/tower.html
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import time
import uuid

_SAFE_ID = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$')
_PINNED = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9./:_-]*@sha256:[0-9a-f]{64}$')


class ExecutionUnavailable(RuntimeError):
    pass


class Workspace:
    def __init__(self, state_root, user_id, workspace_id):
        if not all(_SAFE_ID.fullmatch(str(x or '')) for x in (user_id, workspace_id)):
            raise ValueError('Gecersiz calisma alani kimligi')
        root = Path(state_root).resolve()
        self.path = (root / 'workspaces' / user_id / workspace_id).resolve()
        if not self.path.is_relative_to(root):
            raise ValueError('Calisma alani kok disinda')
        self.path.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative):
        relative = str(relative or '').replace('\\', '/')
        if not relative or PurePosixPath(relative).is_absolute() or ':' in relative:
            raise ValueError('Calisma alanina gore dosya yolu gerekli')
        if '..' in PurePosixPath(relative).parts:
            raise ValueError('Ust dizine erisim reddedildi')
        path = (self.path / relative).resolve()
        if not path.is_relative_to(self.path):
            raise ValueError('Dosya calisma alaninin disinda')
        if any(part == '.git' or part in ('.ssh', '.aws') for part in path.relative_to(self.path).parts):
            raise ValueError('Bu dosya uygulama tarafindan yonetilir')
        return path

    def write(self, path, content):
        target = self.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        data = str(content).encode('utf-8')
        temp = target.with_name(target.name + '.basak-' + uuid.uuid4().hex)
        temp.write_bytes(data)
        os.replace(temp, target)
        return {'path': str(target.relative_to(self.path)), 'bytes': len(data),
                'sha256': hashlib.sha256(data).hexdigest()}

    def read(self, path, offset=0, length=40000):
        target = self.resolve(path)
        text = target.read_text(encoding='utf-8', errors='strict')
        offset = max(0, int(offset))
        length = max(1, min(int(length), 500000))
        return {'path': str(target.relative_to(self.path)), 'content': text[offset:offset+length],
                'total_characters': len(text),
                'next_offset': offset+length if offset+length < len(text) else None}

    def files(self):
        result = []
        for path in self.path.rglob('*'):
            if path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(self.path)
            if any(x in ('.git', 'node_modules', '.venv') for x in rel.parts):
                continue
            result.append({'path': str(rel).replace('\\', '/'), 'bytes': path.stat().st_size})
        return sorted(result, key=lambda x: x['path'])


class Sandbox:
    """Only a digest-pinned trusted image may execute untrusted project code."""
    def __init__(self, workspace, image, control=None, runner=None):
        self.workspace = Path(workspace).resolve()
        self.image = str(image or '')
        self.control = control
        self._runner = runner or subprocess.run

    def _docker(self, args, **kwargs):
        return self._runner(['docker', *args], capture_output=True, text=True,
                            encoding='utf-8', errors='replace', shell=False, **kwargs)

    def run(self, argv, timeout=900):
        if not _PINNED.fullmatch(self.image):
            raise ExecutionUnavailable('Guvenilir imajin sha256 ozeti yapilandirilmamis')
        if os.name != 'posix' and self._runner is subprocess.run:
            raise ExecutionUnavailable('Bulut kod iscisi Linux ve gVisor gerektirir')
        if not isinstance(argv, list) or not argv or not all(
                isinstance(a, str) and a and '\x00' not in a for a in argv):
            raise ValueError('Komut shell metni degil argv listesi olmali')
        if not self.workspace.is_dir():
            raise ValueError('Calisma alani yok')
        info = self._docker(['info', '--format', '{{json .Runtimes}}'], timeout=15)
        if info.returncode or 'runsc' not in info.stdout:
            raise ExecutionUnavailable('gVisor runsc kullanilabilir degil')
        name = 'basak-job-' + uuid.uuid4().hex
        create = self._docker([
            'create', '--name', name, '--runtime', 'runsc', '--network', 'none',
            '--read-only', '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges',
            '--pids-limit', '256', '--memory', '4g', '--cpus', '1',
            '--user', '65532:65532', '--tmpfs', '/tmp:rw,nosuid,nodev,size=256m',
            '--mount', 'type=bind,src=%s,dst=/workspace' % self.workspace,
            '--workdir', '/workspace', '--env', 'HOME=/tmp', self.image, *argv], timeout=30)
        if create.returncode:
            raise ExecutionUnavailable('Izole calistirma ortami olusturulamadi')
        try:
            start = self._docker(['start', name], timeout=30)
            if start.returncode:
                raise ExecutionUnavailable('Izole islem baslatilamadi')
            end = time.monotonic() + max(1, int(timeout))
            while True:
                if self.control:
                    self.control.check_cancelled()
                state = self._docker(['inspect', '--format', '{{json .State}}', name], timeout=15)
                if state.returncode:
                    raise ExecutionUnavailable('Islem durumu okunamadi')
                data = json.loads(state.stdout)
                if not data.get('Running'):
                    break
                if time.monotonic() >= end:
                    self._docker(['stop', '--time', '3', name], timeout=15)
                    raise TimeoutError('Komutun calisma suresi doldu')
                time.sleep(0.25)
            logs = self._docker(['logs', name], timeout=30)
            return {'exit_code': int(data.get('ExitCode', -1)), 'stdout': logs.stdout,
                    'stderr': logs.stderr, 'image': self.image,
                    'oom_killed': bool(data.get('OOMKilled'))}
        finally:
            # Only the generated container is removed. Workspace data is retained.
            self._docker(['rm', '--force', name], timeout=20)


def availability():
    return {'configured': bool(os.environ.get('BASAK_SANDBOX_IMAGE_PYTHON') or
                               os.environ.get('BASAK_SANDBOX_IMAGE_NODE')),
            'docker_installed': bool(shutil.which('docker')),
            'platform': os.name,
            'isolation': 'gvisor', 'network': 'none'}
