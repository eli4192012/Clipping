"""Optional, bounded Amphetamine sessions owned by one local queue runner.

Uses the installed app's scripting dictionary. No sudo, pmset writes, private
entitlements or permanent power-setting changes are made by Clipping.
"""
import os
import platform
import subprocess
import sys
import time
import uuid
from pathlib import Path

from project_store import read, write

APP_ID = 'com.if.Amphetamine'
APP_STORE = 'https://apps.apple.com/us/app/amphetamine/id937984704'
DURATION = 24 * 60 * 60


def capability():
    if platform.system() != 'Darwin':
        return False, 'Closed-lid processing is available on macOS.'
    installed = any((folder/'Amphetamine.app/Contents/Info.plist').is_file()
                    for folder in (Path('/Applications'), Path.home()/'Applications'))
    if not installed:
        return False, 'Install the free Amphetamine app and finish its first-run setup.'
    try:
        power = subprocess.run(['/usr/bin/pmset', '-g', 'batt'], capture_output=True,
                               text=True, timeout=5, check=True).stdout
    except (OSError, subprocess.SubprocessError):
        return False, 'The Mac’s power source could not be checked.'
    if "Now drawing from 'AC Power'" not in power:
        return False, 'Plug in your charger before starting closed-lid processing.'
    return True, 'Amphetamine is installed and your charger is connected.'


def applescript(body, timeout=20):
    result = subprocess.run(['/usr/bin/osascript', '-e',
                             f'tell application id "{APP_ID}"\n{body}\nend tell'],
                            capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # The useful action is predictable; do not expose arbitrary OS output.
        raise RuntimeError('Amphetamine could not be controlled. Finish its setup and allow macOS Automation access when prompted.')
    return result.stdout.strip()


def process_identity(pid):
    try:
        output = subprocess.run(['/bin/ps', '-p', str(int(pid)), '-o', 'uid=', '-o', 'lstart=', '-o', 'stat='],
                                capture_output=True, text=True, timeout=5, check=True).stdout.strip()
        identity, state = output.rsplit(maxsplit=1)
        return '' if state.startswith('Z') else identity
    except (OSError, ValueError, subprocess.SubprocessError):
        return ''


def session_snapshot():
    value = applescript('return {(session is active), (closed display mode enabled), (session time remaining)}')
    active, closed, remaining = [part.strip() for part in value.split(',')]
    return active == 'true', closed == 'true', int(remaining)


def owned(snapshot, started, now):
    active, _, remaining = snapshot
    # Amphetamine exposes no session ID. Detect replacement/ended sessions by
    # the finite countdown; never end an existing or differently timed session.
    return active and remaining > 0 and abs(remaining - (DURATION-(now-started))) <= 10


def state_path(root):
    return Path(root)/'work/queue-power.json'


def status(root):
    current = read(state_path(root), {})
    if not isinstance(current, dict):return {}
    if current.get('phase') == 'active' and current.get('updated'):
        if (time.time()-current['updated'] > 45 or
                process_identity(current['watcher']) != current.get('watcher_identity')):
            return dict(current, phase='error', message='The keep-awake monitor stopped responding. Keep the lid open; end the session from Amphetamine’s menu if needed.')
    return current


def watch(root, owner_pid, token, poll=3):
    root = Path(root)
    path = state_path(root)
    stop = root/'work'/f'queue-power-stop-{token}'
    identity = process_identity(owner_pid)
    watcher_identity = process_identity(os.getpid())
    started = None

    def report(phase, message):
        write(path, dict(token=token, phase=phase, message=message, watcher=os.getpid(), owner=owner_pid,
                         watcher_identity=watcher_identity, updated=time.time()))

    report('starting', 'Starting Amphetamine; finish any macOS prompts before closing the lid.')
    try:
        ready, reason = capability()
        if not ready or not identity:
            raise RuntimeError(reason if not ready else 'The queue runner is no longer available.')
        # Check and start in a single Apple event sequence to avoid overwriting
        # an already active personal/Trigger session.
        value = applescript('if session is active then return "busy"\n'
                            'start new session with options {duration:1440, interval:minutes, displaySleepAllowed:true}\n'
                            'return session time remaining', timeout=120)
        if value == 'busy':
            raise RuntimeError('An Amphetamine session is already active. End it in Amphetamine before starting a queue-owned session.')
        initial = int(value)
        if not 0 < initial <= DURATION:
            raise RuntimeError('Amphetamine did not start a timed queue session.')
        started = time.monotonic()-(DURATION-initial)
        applescript('enable closed display mode', timeout=120)
        if not session_snapshot()[1]:
            raise RuntimeError('Closed-display mode is not enabled. Finish Amphetamine’s closed-display setup first.')
        report('active', 'Closed-lid session active through Amphetamine. Keep the charger connected. Maximum session: 24 hours.')
        while not stop.exists() and process_identity(owner_pid) == identity:
            ready, reason = capability()
            snapshot = session_snapshot()
            if not owned(snapshot, started, time.monotonic()):
                report('ended', 'The queue’s Amphetamine session ended or was replaced. Keep the lid open until restarted.')
                return
            if not ready or not snapshot[1]:
                raise RuntimeError(reason if not ready else 'Closed-display mode was turned off. Keep the lid open.')
            report('active', 'Closed-lid session active through Amphetamine. Keep the charger connected. Maximum session: 24 hours.')
            time.sleep(poll)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        report('error', str(error) if isinstance(error, RuntimeError) else 'The keep-awake connection was interrupted. Keep the lid open.')
    finally:
        if started is not None:
            try:
                if owned(session_snapshot(), started, time.monotonic()):
                    applescript('end session')
                current = status(root)
                if current.get('token') == token and current.get('phase') not in ('error', 'ended'):
                    report('ended', 'Queue keep-awake session finished; Amphetamine’s normal behavior is restored.')
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError):
                report('error', 'End the queue session from Amphetamine’s menu. Its 24-hour timer is still the fallback.')
        stop.unlink(missing_ok=True)


class QueuePower:
    def __init__(self, root):
        self.root = Path(root)
        self.token = uuid.uuid4().hex
        self.process = None

    def start(self):
        ready, reason = capability()
        if not ready:
            raise RuntimeError(reason)
        with (self.root/'work/queue-power.log').open('a') as log:
            self.process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--watch',
                                             str(self.root), str(os.getpid()), self.token],
                                            stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        begun = time.monotonic()
        while time.monotonic()-begun < 150:
            current = status(self.root)
            if current.get('token') == self.token:
                if current['phase'] == 'active':
                    return self
                if current['phase'] == 'error':
                    raise RuntimeError(current['message'])
            if self.process.poll() is not None:
                break
            time.sleep(.2)
        self.stop()
        raise RuntimeError('Closed-lid setup did not finish. Complete the macOS prompts and start the queue again.')

    def stop(self):
        (self.root/'work'/f'queue-power-stop-{self.token}').touch()
        if self.process is not None:
            try:
                self.process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                # Keep the independent watcher alive to finish any native prompt
                # and release its session, even after the queue runner exits.
                pass


if __name__ == '__main__':
    if len(sys.argv) != 5 or sys.argv[1] != '--watch':
        raise SystemExit('Use --watch ROOT OWNER_PID TOKEN.')
    watch(Path(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
