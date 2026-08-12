# -*- coding: utf-8 -*-

""" #+begin_org
* ~[Summary]~ :: CS commands for containerProc — build, run, verify, composeUp/Down, status, clean
#+end_org """

####+BEGIN: b:py3:cs:file/dblockControls :classification "cs-u"
""" #+begin_org
* [[elisp:(org-cycle)][| /Control Parameters Of This File/ |]] :: dblk ctrls classifications=cs-u
#+end_org """
####+END:

if 'csInfo' not in globals(): import typing ; csInfo: typing.Dict[str, typing.Any] = { 'moduleName': ['loadAs'], }
csInfo['version'] = '202608100001'
csInfo['status']  = 'inDev'

import typing
import subprocess
import pathlib

from bisos import b
from bisos.b import cs
from bisos.b import b_io

import collections

from bisos.dockerProc import containerProc_seedInfo


###############################################################################
# Helpers
###############################################################################

def _params() -> containerProc_seedInfo.ContainerParams:
    """Resolve ContainerParams from the planted path at dispatch time."""
    return containerProc_seedInfo.paramsFromPlantPath()


def _detectInContainer() -> str | None:
    """If the current process is running inside a container, return a short
    reason string identifying which heuristic matched. Otherwise return None.

    Uses a union of well-known Linux heuristics --- none is 100% by itself,
    but the union catches docker, podman, and most nspawn/lxc runtimes.
    """
    # docker creates /.dockerenv at container-start time.
    if pathlib.Path('/.dockerenv').exists():
        return "/.dockerenv exists (docker)"
    # podman (and some CRI runtimes) create /run/.containerenv.
    if pathlib.Path('/run/.containerenv').exists():
        return "/run/.containerenv exists (podman)"
    # cgroup path of PID 1 mentions the runtime for most container engines.
    try:
        cgroup = pathlib.Path('/proc/1/cgroup').read_text()
        for marker in ('docker', 'containerd', 'libpod', 'kubepods', 'lxc'):
            if marker in cgroup:
                return f"/proc/1/cgroup contains {marker!r}"
    except OSError:
        pass
    return None


def _refuseIfInContainer() -> None:
    """Raise RuntimeError if we are running inside a container.

    The engine-driving commands (build, run, composeUp/Down, verify, status,
    clean) all pass through _run(). Nesting containers is not supported here:
    this package assumes the Container Platform is a host, not itself a
    container. Refuse loudly rather than let the user chase confusing
    nested-engine failures.
    """
    reason = _detectInContainer()
    if reason is not None:
        raise RuntimeError(
            f"Refusing to run: this process appears to be inside a container "
            f"({reason}). bisos.dockerProc's engine-driving commands are "
            f"designed to run on the Container Platform (a host), not from "
            f"inside a container. Run this command from the host instead."
        )


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    _refuseIfInContainer()
    b_io.ann.note(f"Running: {' '.join(cmd)}")
    try:
        return subprocess.run(cmd, check=check)
    except FileNotFoundError as exc:
        # Rewrap so the atexit machinery doesn't reformat this as a
        # misleading "seed file not found" ImportError. The user needs to see
        # that the container engine binary is missing on this host.
        raise RuntimeError(
            f"Command not found: {cmd[0]!r}. Install it with "
            f"'dockerProc-sbom.pcs -i sbom_apt_install' (docker) or "
            f"'podman-sbom.pcs -i sbom_apt_install' (podman)."
        ) from exc


###############################################################################
# commonParamsSpecify --- registers CS parameters used by the containerProc_*
# commands with the PyCS argparse layer. Without this, --noCache / --cgroupVer /
# --detach / --localBuild are rejected as "unrecognized arguments" even though
# the Cmnd classes declare them in cmndParamsOptional.
###############################################################################

def commonParamsSpecify(
        csParams: cs.param.CmndParamDict,
) -> None:
    csParams.parDictAdd(
        parName='localBuild',
        parDescription="Local-only build (no push). Truthy string like 'true'.",
        parDataType=None,
        parDefault=None,
        parChoices=["any"],
        argparseShortOpt=None,
        argparseLongOpt='--localBuild',
    )
    csParams.parDictAdd(
        parName='noCache',
        parDescription="Pass --no-cache to the engine build. Truthy string like 'true'.",
        parDataType=None,
        parDefault=None,
        parChoices=["any"],
        argparseShortOpt=None,
        argparseLongOpt='--noCache',
    )
    csParams.parDictAdd(
        parName='cgroupVer',
        parDescription="Host cgroup version selector for docker compose: 'v1' or 'v2'.",
        parDataType=None,
        parDefault=None,
        parChoices=["v1", "v2"],
        argparseShortOpt=None,
        argparseLongOpt='--cgroupVer',
    )
    csParams.parDictAdd(
        parName='detach',
        parDescription="Run podman container detached (background). Truthy string like 'true'.",
        parDataType=None,
        parDefault=None,
        parChoices=["any"],
        argparseShortOpt=None,
        argparseLongOpt='--detach',
    )
    csParams.parDictAdd(
        parName='follow',
        parDescription="Follow log output (-f). Truthy string like 'true'. For instanceLogs.",
        parDataType=None,
        parDefault=None,
        parChoices=["any"],
        argparseShortOpt=None,
        argparseLongOpt='--follow',
    )
    csParams.parDictAdd(
        parName='execCmd',
        parDescription="Command to exec inside container (default 'bash'). For instanceExec.",
        parDataType=None,
        parDefault=None,
        parChoices=["any"],
        argparseShortOpt=None,
        argparseLongOpt='--execCmd',
    )


###############################################################################
# Image Commands --- operate on the container image (build artefact).
# Independent of any running instance.
###############################################################################

class containerProc_imageBuild(cs.Cmnd):
    """Build the container image for this leaf.

    localBuild: local build only (no push).  noCache: pass --no-cache.
    For rootless-sysd (podman) leaves, auto-builds confined base if missing.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['localBuild', 'noCache']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        localBuild: typing.Optional[str] = None,
        noCache: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """Build container image for this leaf."""
        callParamsDict = {'localBuild': localBuild, 'noCache': noCache}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        leafDir = pathlib.Path(p.plantPath).parent
        noCacheFlag = ['--no-cache'] if noCache else []

        if p.engine == containerProc_seedInfo.Engine.Podman:
            # rootless-sysd: ensure confined base is present, then build
            _ensureConfinedBase(p, leafDir, noCacheFlag)
            cmd = (
                ['podman', 'build', '--isolation=chroot']
                + noCacheFlag
                + ['-t', p.imageName, str(leafDir)]
            )
        else:
            cmd = (
                ['docker', 'build']
                + noCacheFlag
                + ['-t', p.imageName, str(leafDir)]
            )

        _run(cmd)
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Built {p.imageName}")


class containerProc_imageDelete(cs.Cmnd):
    """Remove the container image for this leaf (engine rmi).

    Does NOT touch running or stopped instances --- use instanceDelete first
    if the image is in use. Use fullClean for imageDelete + instanceDelete.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = []
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """engine rmi <image>."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value
        _run([engine, 'rmi', p.imageName], check=False)
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Image deleted: {p.imageName}")


def _ensureConfinedBase(
    p: containerProc_seedInfo.ContainerParams,
    leafDir: pathlib.Path,
    noCacheFlag: list[str],
) -> None:
    """Build confined base image for podman if not present."""
    result = subprocess.run(
        ['podman', 'image', 'exists', p.baseImage],
        check=False,
    )
    if result.returncode != 0:
        # Infer confined base context: ../../../../confined/vnc/xfce/<baseName>
        baseContext = leafDir.parents[3] / 'confined' / 'vnc' / 'xfce' / f'bisos_deb{p.release}-fresh'
        b_io.ann.note(f"Base image {p.baseImage} missing — building from {baseContext}")
        _run(
            ['podman', 'build', '--isolation=chroot']
            + noCacheFlag
            + ['-t', p.baseImage, str(baseContext)]
        )


###############################################################################
# Instance Commands --- operate on a running (or stopped) container instance.
# Anticipate Stage 4 Platform Registrar: will gain --instance=N arg later.
###############################################################################

class containerProc_instanceUp(cs.Cmnd):
    """Create and start the container instance for this leaf.

    Dispatches on p.engine:
      - docker → 'docker compose up -d' with the leaf's compose file.
      - podman → 'podman run --systemd=always -d --name <img> -p ...'.

    For docker leaves, cgroupVer='v1' selects docker-compose.cgv1.yml.
    For podman leaves, detach='true' runs detached (default is foreground).
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['cgroupVer', 'detach']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        cgroupVer: typing.Optional[str] = None,
        detach: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """Create + start instance. Dispatches on p.engine."""
        callParamsDict = {'cgroupVer': cgroupVer, 'detach': detach}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        if p.engine == containerProc_seedInfo.Engine.Docker:
            leafDir = pathlib.Path(p.plantPath).parent
            composeFile = (
                'docker-compose.cgv1.yml'
                if cgroupVer == 'v1'
                else 'docker-compose.yml'
            )
            _run(['docker', 'compose', '-f', str(leafDir / composeFile), 'up', '-d'])
            return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Up: {composeFile}")
        else:
            # podman rootless-sysd
            detachFlag = ['-d'] if detach else []
            cmd = (
                ['podman', 'run', '--systemd=always']
                + detachFlag
                + [
                    '--name', p.imageName,
                    '-p', f'{p.sshPort}:22',
                    '-p', f'{p.vncPort}:5901',
                    '-p', f'{p.novncPort}:6901',
                    p.imageName,
                ]
            )
            _run(cmd)
            return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Started {p.imageName}")


class containerProc_instanceDown(cs.Cmnd):
    """Stop the running container instance (does NOT remove --- use instanceDelete for that).

    Dispatches on p.engine:
      - docker → 'docker compose down' (stops + removes compose service).
      - podman → 'podman stop' (stop only; container still exists).

    For docker leaves, cgroupVer='v1' selects docker-compose.cgv1.yml.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['cgroupVer']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        cgroupVer: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """Stop instance. Dispatches on p.engine."""
        callParamsDict = {'cgroupVer': cgroupVer}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        if p.engine == containerProc_seedInfo.Engine.Docker:
            leafDir = pathlib.Path(p.plantPath).parent
            composeFile = (
                'docker-compose.cgv1.yml'
                if cgroupVer == 'v1'
                else 'docker-compose.yml'
            )
            _run(['docker', 'compose', '-f', str(leafDir / composeFile), 'down'])
            return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Down: {composeFile}")
        else:
            # podman: stop (does not rm; use instanceDelete for stop+rm)
            _run(['podman', 'stop', p.imageName], check=False)
            return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Stopped {p.imageName}")


class containerProc_instanceDelete(cs.Cmnd):
    """Stop and remove the container instance (image is preserved).

    Dispatches on p.engine:
      - docker → 'docker compose down' removes the instance.
      - podman → 'podman stop && podman rm' (in sequence).

    For docker leaves, cgroupVer='v1' selects docker-compose.cgv1.yml.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['cgroupVer']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        cgroupVer: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """Stop + remove instance. Dispatches on p.engine."""
        callParamsDict = {'cgroupVer': cgroupVer}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        if p.engine == containerProc_seedInfo.Engine.Docker:
            # 'docker compose down' already stops + removes.
            leafDir = pathlib.Path(p.plantPath).parent
            composeFile = (
                'docker-compose.cgv1.yml'
                if cgroupVer == 'v1'
                else 'docker-compose.yml'
            )
            _run(['docker', 'compose', '-f', str(leafDir / composeFile), 'down'])
            return cmndOutcome.set(opError=b.op.OpError.Success,
                                   opResults=f"Instance deleted: {composeFile}")
        else:
            _run(['podman', 'stop', p.imageName], check=False)
            _run(['podman', 'rm', p.imageName], check=False)
            return cmndOutcome.set(opError=b.op.OpError.Success,
                                   opResults=f"Instance deleted: {p.imageName}")


class containerProc_instanceRestart(cs.Cmnd):
    """Restart the container instance in place (stop + start; state preserved)."""
    cmndParamsMandatory = []
    cmndParamsOptional = []
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """engine restart <container>."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value
        _run([engine, 'restart', p.imageName])
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Restarted {p.imageName}")


class containerProc_instancePs(cs.Cmnd):
    """Show 'engine ps -a' filtered to this leaf's container.

    Includes stopped instances (unlike bare 'ps'). Empty output = no instance
    (neither running nor stopped) exists for this leaf.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = []
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """engine ps -a --filter name=<container>."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value
        _run([engine, 'ps', '-a', '--filter', f'name={p.imageName}'])
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults="listed")


class containerProc_instanceLogs(cs.Cmnd):
    """Show container logs (stdout+stderr since instance start).

    follow='true' streams new output (tail -f). Ctrl-C to stop.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['follow']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        follow: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """engine logs [-f] <container>."""
        callParamsDict = {'follow': follow}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value
        followFlag = ['-f'] if follow else []
        _run([engine, 'logs'] + followFlag + [p.imageName], check=False)
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults="logs shown")


class containerProc_instanceExec(cs.Cmnd):
    """Exec a command inside the running container (default: interactive bash).

    execCmd='<cmd>' runs the given command instead of bash.
    Note: on old Podman (4.3.1), 'exec' into a rootless systemd container may
    fail with a cgroup.procs permission error --- use SSH instead
    (ssh -p <sshPort> bystar@localhost).
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['execCmd']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        execCmd: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """engine exec -it <container> <cmd>."""
        callParamsDict = {'execCmd': execCmd}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value
        cmdToRun = execCmd or 'bash'
        _run([engine, 'exec', '-it', p.imageName, cmdToRun], check=False)
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"exec {cmdToRun}")


###############################################################################
# verify
###############################################################################

class containerProc_instanceVerify(cs.Cmnd):
    """Smoke-test the instance: port connectivity + noVNC HTTP + SSH-based systemd/service checks.

    For rootless-sysd: exec-free (SSH-based) — podman exec is unreliable on old Podman.
    'degraded' systemd state is WARN not FAIL (polkit is masked but may show on older images).
    """
    cmndParamsMandatory = []
    cmndParamsOptional = []
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """Port + HTTP + SSH-based service checks."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        failures: list[str] = []
        warnings: list[str] = []

        # 1. Container running?
        engine = p.engine.value
        inspect = subprocess.run(
            [engine, 'inspect', '--format', '{{.State.Status}}', p.imageName],
            capture_output=True, text=True, check=False,
        )
        if inspect.returncode != 0 or inspect.stdout.strip() != 'running':
            failures.append(f"Container {p.imageName} not running")
        else:
            b_io.ann.note(f"PASS: container {p.imageName} running")

        # 2. SSH port reachable
        nc = subprocess.run(
            ['nc', '-z', '-w3', 'localhost', str(p.sshPort)],
            check=False,
        )
        if nc.returncode != 0:
            failures.append(f"SSH port {p.sshPort} not reachable")
        else:
            b_io.ann.note(f"PASS: SSH port {p.sshPort} reachable")

        # 3. VNC port reachable
        nc = subprocess.run(
            ['nc', '-z', '-w3', 'localhost', str(p.vncPort)],
            check=False,
        )
        if nc.returncode != 0:
            failures.append(f"VNC port {p.vncPort} not reachable")
        else:
            b_io.ann.note(f"PASS: VNC port {p.vncPort} reachable")

        # 4. noVNC HTTP responds
        curl = subprocess.run(
            ['curl', '-s', '-o', '/dev/null', '-w', '%{http_code}',
             f'http://localhost:{p.novncPort}/'],
            capture_output=True, text=True, check=False,
        )
        if curl.stdout.strip() not in ('200', '301', '302'):
            failures.append(f"noVNC HTTP {p.novncPort} returned {curl.stdout.strip()!r}")
        else:
            b_io.ann.note(f"PASS: noVNC HTTP {p.novncPort} responds")

        # 5. SSH-based systemd/service checks
        _sshVerify(p, failures, warnings)

        if failures:
            b_io.ann.note(f"FAIL: {failures}")
            return cmndOutcome.set(opError=b.op.OpError.Failure, opResults=str(failures))
        if warnings:
            b_io.ann.note(f"WARN: {warnings}")

        return cmndOutcome.set(opError=b.op.OpError.Success, opResults="All checks passed")


def _sshVerify(
    p: containerProc_seedInfo.ContainerParams,
    failures: list[str],
    warnings: list[str],
) -> None:
    """SSH into container and run systemd/service checks.

    Auth precedence (mirrors bro_dockerfiles/.../verify.sh):
      1. sshpass -p insecure (default) --- if sshpass is on PATH.
      2. key-based BatchMode --- if a preinstalled key is present.
      3. no runner --- inside-container checks reported WARN, host-side stand.

    Uses UserKnownHostsFile=/dev/null so container-restart host-key changes
    do not fail SSH silently.
    """
    import shutil

    sshOpts = [
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'UserKnownHostsFile=/dev/null',
        '-o', 'ConnectTimeout=5',
        '-p', str(p.sshPort),
        'bystar@localhost',
    ]

    sshpassPath = shutil.which('sshpass')
    if sshpassPath:
        def sshRun(cmd: str) -> tuple[int, str]:
            r = subprocess.run(
                [sshpassPath, '-p', 'insecure', 'ssh'] + sshOpts + [cmd],
                capture_output=True, text=True, check=False,
            )
            return r.returncode, r.stdout.strip()
        sshMode = "sshpass"
    else:
        def sshRun(cmd: str) -> tuple[int, str]:
            r = subprocess.run(
                ['ssh', '-o', 'BatchMode=yes'] + sshOpts + [cmd],
                capture_output=True, text=True, check=False,
            )
            return r.returncode, r.stdout.strip()
        sshMode = "key/BatchMode"

    # systemd PID 1? --- probes SSH is working. If this returns empty, downstream
    # checks would also all be empty; skip them with a WARN + manual instruction.
    rc, out = sshRun('ps -p 1 -o comm=')
    if rc != 0 or not out:
        warnings.append(
            f"SSH not automatable in {sshMode} mode "
            f"(install sshpass, or set up a key). Manual check: "
            f"ssh -p {p.sshPort} bystar@localhost 'systemctl is-system-running; systemctl --failed'"
        )
        return
    if out.strip() != 'systemd':
        failures.append(f"PID 1 is '{out}', expected systemd")
    else:
        b_io.ann.note("PASS: systemd is PID 1")

    # system state
    rc, out = sshRun('systemctl is-system-running')
    if out in ('running',):
        b_io.ann.note("PASS: systemd state=running")
    elif out in ('degraded',):
        warnings.append("WARN: systemd state=degraded (check masked units)")
    else:
        failures.append(f"systemd is-system-running={out!r}")

    # Required services
    for svc in ('vncserver@:1.service', 'novnc.service', 'sshd-container.service'):
        rc, out = sshRun(f'systemctl is-active {svc}')
        if out != 'active':
            failures.append(f"Service {svc} is-active={out!r}")
        else:
            b_io.ann.note(f"PASS: {svc} active")


###############################################################################
# status
###############################################################################

class containerProc_instanceStatus(cs.Cmnd):
    """Show instance inspect + systemd state summary."""
    cmndParamsMandatory = []
    cmndParamsOptional = []
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """Engine inspect + SSH systemd status."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value

        _run([engine, 'inspect', p.imageName], check=False)

        # SSH systemd summary if running
        inspect = subprocess.run(
            [engine, 'inspect', '--format', '{{.State.Status}}', p.imageName],
            capture_output=True, text=True, check=False,
        )
        if inspect.stdout.strip() == 'running':
            import shutil as _shutil
            sshOpts = [
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'UserKnownHostsFile=/dev/null',
                '-o', 'ConnectTimeout=5',
                '-p', str(p.sshPort),
                'bystar@localhost',
            ]
            sshpassPath = _shutil.which('sshpass')
            statusCmd = 'systemctl --no-pager status vncserver@:1 novnc sshd-container'
            if sshpassPath:
                subprocess.run(
                    [sshpassPath, '-p', 'insecure', 'ssh'] + sshOpts + [statusCmd],
                    check=False,
                )
            else:
                subprocess.run(
                    ['ssh', '-o', 'BatchMode=yes'] + sshOpts + [statusCmd],
                    check=False,
                )

        return cmndOutcome.set(opError=b.op.OpError.Success, opResults="status done")


###############################################################################
# Combined
###############################################################################

class containerProc_fullClean(cs.Cmnd):
    """Full clean: instanceDelete + imageDelete.

    Equivalent to running containerProc_instanceDelete followed by
    containerProc_imageDelete. Convenience for a from-scratch rebuild.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = []
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """Stop + rm instance, then rmi image."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value

        subprocess.run([engine, 'stop', p.imageName], check=False)
        subprocess.run([engine, 'rm', p.imageName], check=False)
        subprocess.run([engine, 'rmi', p.imageName], check=False)

        return cmndOutcome.set(opError=b.op.OpError.Success,
                               opResults=f"fullClean: {p.imageName}")


###############################################################################
# Backward-compat aliases --- one release only, then remove.
# Old Cmnd names get shims that emit a DeprecationWarning and delegate to the
# new class. Anything that references the old names via CLI still works during
# the transition.
###############################################################################

import warnings as _warnings


def _deprecated(oldName: str, newCls: type) -> type:
    """Build a Cmnd subclass that warns then delegates to newCls."""
    class _Deprecated(newCls):  # type: ignore[valid-type,misc]
        def cmnd(self, *a, **kw):
            _warnings.warn(
                f"{oldName} is deprecated; use {newCls.__name__} instead.",
                DeprecationWarning,
                stacklevel=2,
            )
            return super().cmnd(*a, **kw)
    _Deprecated.__name__ = oldName
    _Deprecated.__qualname__ = oldName
    return _Deprecated


containerProc_build      = _deprecated('containerProc_build',      containerProc_imageBuild)
containerProc_composeUp  = _deprecated('containerProc_composeUp',  containerProc_instanceUp)
containerProc_composeDown = _deprecated('containerProc_composeDown', containerProc_instanceDown)
containerProc_run        = _deprecated('containerProc_run',        containerProc_instanceUp)
containerProc_verify     = _deprecated('containerProc_verify',     containerProc_instanceVerify)
containerProc_status     = _deprecated('containerProc_status',     containerProc_instanceStatus)
containerProc_clean      = _deprecated('containerProc_clean',      containerProc_fullClean)


###############################################################################
# podmanDirectCmnds — cheat sheet (mirrors dockerDirectCmnds with s/docker/podman)
###############################################################################

class podmanDirectCmnds(cs.Cmnd):
    cmndParamsMandatory = []
    cmndParamsOptional = ['perfName']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        perfName: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """Direct Podman interface cheat-sheet (equivalent of dockerDirectCmnds)."""
        from bisos.common import csParam
        callParamsDict = {'perfName': perfName}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)
        perfName = csParam.mappedValue('perfName', perfName)

        literal = cs.examples.execInsert

        if b.subProc.Op(outcome=cmndOutcome, log=0).bash(
                "podman image ls -q | head -1",
        ).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)
        oneImageId = cmndOutcome.stdout.strip()

        if b.subProc.Op(outcome=cmndOutcome, log=0).bash(
                "podman ps -q | head -1",
        ).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)
        oneContainerId = cmndOutcome.stdout.strip() or "<containerId>"

        cs.examples.menuChapter('=Direct Podman Interface Commands=')

        cs.examples.menuSection('/Initializations and Setup/')
        literal("NOTYET -- PKG sbom (use podman-sbom.pcs)")
        literal("# rootless: no group setup needed — runs as current user")

        literal("https://hub.docker.com")
        literal("podman search --help")

        cs.examples.menuSection('/BISOS Podman Base Dockerfiles/')
        literal("ls -ld /bisos/git/bxRepos/bxObjects/bro_dockerfiles/debian")
        literal("tree /bisos/git/bxRepos/bxObjects/bro_dockerfiles/debian/12")

        cs.examples.menuSection('/Podman:: Inspect, Examine/')
        literal("podman ps --help")
        literal("podman ps")
        literal("podman ps -a")
        literal("podman logs --help")
        literal(f"podman logs {oneContainerId}")

        cs.examples.menuSection('/Podman Images/')
        literal("podman image --help")
        literal("podman image ls")
        literal(f"podman image inspect {oneImageId}")
        literal("podman build --isolation=chroot -t bisos-image .")
        literal("podman build --no-cache --isolation=chroot --progress=plain -t bisos-image .")
        literal("podman image prune -a -f  # Remove all unused images -- forced")
        literal("podman images -f dangling=true -q  # -q provides only image ids")
        literal("podman rmi $(podman images -f dangling=true -q)  # Remove dangling images")

        cs.examples.menuSection('/Podman Run Interface/')
        # --systemd=always: configure the container for systemd as PID 1
        #   (tmpfs on /run, /run/lock, /tmp, /var/log/journal; cgroup delegation).
        # -d: detached (background). Returns the container ID immediately.
        # --name mycontainer: stable name for later stop/start/rm/exec/logs
        #   reference (default is auto-generated two-word name).
        # bisos-image: the image to instantiate (positional, after all flags).
        literal("podman run --systemd=always -d --name mycontainer bisos-image  # rootless-sysd (systemd PID 1)")
        # No --systemd=always: use only for non-systemd (confined) images.
        # -p <host>:<container>: publish a port. Repeatable.
        # Note: ports below are illustrative — bisos_deb*-fresh uses 6901/5901 on both sides.
        literal("podman run -d -p 6901:6901 -p 5901:5901 -p 2222:22 --name mycontainer bisos-image  # confined (no systemd)")

        cs.examples.menuSection('/Podman Container Lifecycle -- stop, start, restart/')
        # podman stop: send SIGTERM, wait <timeout>s, then SIGKILL. Preferred over kill.
        #   Rootless-sysd containers: use --time=10 or more; systemd needs time to shut down services.
        literal(f"podman stop {oneContainerId}  # graceful stop (SIGTERM, 10s grace, then SIGKILL)")
        literal(f"podman stop --time=30 {oneContainerId}  # longer grace for systemd containers")
        literal(f"podman kill {oneContainerId}  # immediate SIGKILL -- avoid for systemd containers")
        # Container still exists after stop; start restarts it in place with the same config.
        literal(f"podman start {oneContainerId}  # restart a stopped container (keeps state)")
        literal(f"podman restart {oneContainerId}  # stop then start")
        # podman ps -a shows stopped containers too (bare 'ps' shows only running).
        literal("podman ps          # running containers only")
        literal("podman ps -a       # all containers including stopped")

        cs.examples.menuSection('/Podman Container Removal/')
        # A stopped container still exists on disk (config + layer diff). rm deletes it.
        # rm requires the container to be stopped first, unless -f is passed.
        literal(f"podman rm {oneContainerId}       # remove a stopped container")
        literal(f"podman rm -f {oneContainerId}    # force-remove even if running (stops + rm in one step)")
        literal("podman rm -a       # remove all stopped containers")
        literal("podman container prune  # remove all stopped containers (interactive)")

        cs.examples.menuSection('/Podman Exec/')
        literal("podman exec --help")
        literal(f"podman exec -it {oneContainerId} bash")

        cs.examples.menuSection('/Podman Logs and Inspect/')
        literal(f"podman logs {oneContainerId}         # print stdout/stderr of container")
        literal(f"podman logs -f {oneContainerId}      # follow (like tail -f)")
        literal(f"podman inspect {oneContainerId}      # full JSON: image, mounts, network, state")

        cs.examples.menuSection('/Podman Cleanups/')
        literal("podman image prune -a -f  # Remove all unused images -- forced")
        literal("podman system prune  # DANGER: Prune entire Podman system")

        cs.examples.menuSection('/Rootless-sysd Specific/')
        literal("podman info --format '{{.Host.CgroupManager}}'  # should be systemd")
        literal("stat -fc %T /sys/fs/cgroup  # cgroup2fs = v2 (required for rootless-sysd)")
        literal("loginctl enable-linger $(id -un)  # persist user services across logout")
        literal("podmanHostVerify.cs -i verify  # full host readiness check")

        return cmndOutcome


###############################################################################
# examples_csu
###############################################################################

def examples_csu() -> None:
    """Examples menu, filtered by p.engine, p.profile, and p.cgroupVariants.

    Reads params from the planted path so the menu shows only commands and
    options relevant to *this* leaf: no docker-compose commands on rootless-sysd
    leaves, no podman run on docker leaves, no cgv1 option on v2-only leaves.

    If we are NOT inside a planted context (e.g. running containerProc-seed.cs
    directly with no .spcs), falls back to the unfiltered full menu.
    """
    od = collections.OrderedDict
    cmnd = cs.examples.cmndEnter

    # Try to read params; if not planted, show the full unfiltered menu.
    try:
        p = _params()
    except (ValueError, Exception):
        _examplesUnfiltered()
        return

    isDocker = (p.engine == containerProc_seedInfo.Engine.Docker)
    isPodman = (p.engine == containerProc_seedInfo.Engine.Podman)
    supportsV1 = (containerProc_seedInfo.CgroupVer.V1 in p.cgroupVariants)

    cs.examples.menuChapter(
        f'*containerProc for {p.imageName}* '
        f'(engine={p.engine.value}, profile={p.profile.value})'
    )

    # -----------------------------------------------------------------
    # Image section
    # -----------------------------------------------------------------
    cs.examples.menuSection('Image')
    cmnd('containerProc_imageBuild', comment="# build with layer cache")
    cmnd('containerProc_imageBuild', pars=od([('noCache', 'true')]),
         comment="# --no-cache build")
    cmnd('containerProc_imageDelete', comment="# rmi (image only)")

    # -----------------------------------------------------------------
    # Instance section --- engine-specific
    # -----------------------------------------------------------------
    cs.examples.menuSection('Instance')

    if isDocker:
        cmnd('containerProc_instanceUp', comment="# docker compose up -d (cgroup v2)")
        if supportsV1:
            cmnd('containerProc_instanceUp', pars=od([('cgroupVer', 'v1')]),
                 comment="# cgroup v1 host: uses docker-compose.cgv1.yml")
        cmnd('containerProc_instanceDown', comment="# docker compose down")
        if supportsV1:
            cmnd('containerProc_instanceDown', pars=od([('cgroupVer', 'v1')]),
                 comment="# cgroup v1 host")
    elif isPodman:
        cmnd('containerProc_instanceUp', pars=od([('detach', 'true')]),
             comment="# podman run --systemd=always -d")
        cmnd('containerProc_instanceDown', comment="# podman stop")

    cmnd('containerProc_instanceRestart')
    cmnd('containerProc_instancePs', comment="# ps -a filtered to this leaf")
    cmnd('containerProc_instanceLogs')
    cmnd('containerProc_instanceLogs', pars=od([('follow', 'true')]),
         comment="# follow (tail -f)")
    cmnd('containerProc_instanceExec', comment="# interactive bash")
    if isPodman:
        # Rootless-sysd exec-into is unreliable on old Podman; SSH is preferred
        cs.examples.execInsert(
            f"ssh -p {p.sshPort} bystar@localhost   # preferred for rootless-sysd"
        )
    cmnd('containerProc_instanceDelete', comment="# stop + rm instance (keeps image)")
    if isDocker and supportsV1:
        cmnd('containerProc_instanceDelete', pars=od([('cgroupVer', 'v1')]),
             comment="# cgroup v1 host")

    # -----------------------------------------------------------------
    # Verify + Status
    # -----------------------------------------------------------------
    cs.examples.menuSection('Verify + Status')
    cmnd('containerProc_instanceVerify')
    cmnd('containerProc_instanceStatus')

    # -----------------------------------------------------------------
    # Full clean
    # -----------------------------------------------------------------
    cs.examples.menuSection('Combined')
    cmnd('containerProc_fullClean',
         comment="# = instanceDelete + imageDelete")


def _examplesUnfiltered() -> None:
    """Full unfiltered menu, shown when there is no planted context.

    Used e.g. when someone runs containerProc-seed.cs directly to browse
    available commands without a leaf.
    """
    od = collections.OrderedDict
    cmnd = cs.examples.cmndEnter

    cs.examples.menuChapter('*containerProc --- full command surface (no leaf context)*')

    cs.examples.menuSection('Image')
    cmnd('containerProc_imageBuild')
    cmnd('containerProc_imageBuild', pars=od([('noCache', 'true')]))
    cmnd('containerProc_imageDelete')

    cs.examples.menuSection('Instance')
    cmnd('containerProc_instanceUp')
    cmnd('containerProc_instanceUp', pars=od([('cgroupVer', 'v1')]))
    cmnd('containerProc_instanceUp', pars=od([('detach', 'true')]))
    cmnd('containerProc_instanceDown')
    cmnd('containerProc_instanceRestart')
    cmnd('containerProc_instancePs')
    cmnd('containerProc_instanceLogs')
    cmnd('containerProc_instanceLogs', pars=od([('follow', 'true')]))
    cmnd('containerProc_instanceExec')
    cmnd('containerProc_instanceDelete')

    cs.examples.menuSection('Verify + Status')
    cmnd('containerProc_instanceVerify')
    cmnd('containerProc_instanceStatus')

    cs.examples.menuSection('Combined')
    cmnd('containerProc_fullClean')


###############################################################################
# End
###############################################################################

### local variables:
### no-byte-compile: t
### end:
