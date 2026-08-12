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
# build
###############################################################################

class containerProc_build(cs.Cmnd):
    """Build the container image for this leaf.

    -d: local build only (no push).  -n: --no-cache.
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
# composeUp
###############################################################################

class containerProc_composeUp(cs.Cmnd):
    """Bring up a docker-compose service for this leaf.

    cgroupVer: 'v1' selects docker-compose.cgv1.yml; default selects docker-compose.yml.
    Only applicable to docker (confined / privileged) profiles.
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
        """docker compose up -d, selecting v1 or v2 overlay."""
        callParamsDict = {'cgroupVer': cgroupVer}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        if p.engine != containerProc_seedInfo.Engine.Docker:
            b_io.ann.note("composeUp is only for docker leaves; use 'run' for rootless-sysd.")
            return cmndOutcome.set(opError=b.op.OpError.Success, opResults="skipped")

        leafDir = pathlib.Path(p.plantPath).parent
        composeFile = (
            'docker-compose.cgv1.yml'
            if cgroupVer == 'v1'
            else 'docker-compose.yml'
        )
        _run(['docker', 'compose', '-f', str(leafDir / composeFile), 'up', '-d'])
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Up: {composeFile}")


###############################################################################
# composeDown
###############################################################################

class containerProc_composeDown(cs.Cmnd):
    """Bring down the docker-compose service for this leaf."""
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
        """docker compose down."""
        callParamsDict = {'cgroupVer': cgroupVer}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        if p.engine != containerProc_seedInfo.Engine.Docker:
            b_io.ann.note("composeDown is only for docker leaves.")
            return cmndOutcome.set(opError=b.op.OpError.Success, opResults="skipped")

        leafDir = pathlib.Path(p.plantPath).parent
        composeFile = (
            'docker-compose.cgv1.yml'
            if cgroupVer == 'v1'
            else 'docker-compose.yml'
        )
        _run(['docker', 'compose', '-f', str(leafDir / composeFile), 'down'])
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Down: {composeFile}")


###############################################################################
# run  (rootless-sysd / podman only)
###############################################################################

class containerProc_run(cs.Cmnd):
    """podman run --systemd=always for rootless-sysd leaves.

    Runs the container in the foreground (detach=False) or detached (detach=True).
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['detach']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        detach: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """podman run with rootless systemd settings."""
        callParamsDict = {'detach': detach}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        if p.engine != containerProc_seedInfo.Engine.Podman:
            b_io.ann.note("run is only for podman (rootless-sysd) leaves.")
            return cmndOutcome.set(opError=b.op.OpError.Success, opResults="skipped")

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


###############################################################################
# verify
###############################################################################

class containerProc_verify(cs.Cmnd):
    """Smoke-test: port connectivity + noVNC HTTP + SSH-based systemd/service checks.

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
    """SSH into container and run systemd/service checks."""
    sshOpts = [
        '-o', 'StrictHostKeyChecking=no',
        '-o', 'BatchMode=yes',
        '-p', str(p.sshPort),
        'bystar@localhost',
    ]

    def sshRun(cmd: str) -> tuple[int, str]:
        r = subprocess.run(
            ['ssh'] + sshOpts + [cmd],
            capture_output=True, text=True, check=False,
        )
        return r.returncode, r.stdout.strip()

    # systemd PID 1?
    rc, out = sshRun('ps -p 1 -o comm=')
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

class containerProc_status(cs.Cmnd):
    """Show container inspect + systemd state summary."""
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
            sshOpts = [
                '-o', 'StrictHostKeyChecking=no',
                '-o', 'BatchMode=yes',
                '-p', str(p.sshPort),
                'bystar@localhost',
            ]
            subprocess.run(
                ['ssh'] + sshOpts + ['systemctl --no-pager status vncserver@:1 novnc sshd-container'],
                check=False,
            )

        return cmndOutcome.set(opError=b.op.OpError.Success, opResults="status done")


###############################################################################
# clean
###############################################################################

class containerProc_clean(cs.Cmnd):
    """Remove container and image for this leaf."""
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
        """Stop and remove container, then remove image."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value

        subprocess.run([engine, 'stop', p.imageName], check=False)
        subprocess.run([engine, 'rm', p.imageName], check=False)
        subprocess.run([engine, 'rmi', p.imageName], check=False)

        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Cleaned {p.imageName}")


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
    od = collections.OrderedDict
    cmnd = cs.examples.cmndEnter

    cs.examples.menuChapter('*containerProc — build, run, verify, compose, status, clean*')

    cs.examples.menuSection('Build')
    cmnd('containerProc_build', comment="# build with layer cache")
    cmnd('containerProc_build', pars=od([('noCache', 'true')]), comment="# --no-cache build")

    cs.examples.menuSection('Docker compose (confined / privileged)')
    cmnd('containerProc_composeUp', comment="# cgroup v2 host")
    cmnd('containerProc_composeUp', pars=od([('cgroupVer', 'v1')]), comment="# cgroup v1 host")
    cmnd('containerProc_composeDown')

    cs.examples.menuSection('Podman run (rootless-sysd)')
    cmnd('containerProc_run', pars=od([('detach', 'true')]), comment="# detached")

    cs.examples.menuSection('Verify')
    cmnd('containerProc_verify')

    cs.examples.menuSection('Status / Clean')
    cmnd('containerProc_status')
    cmnd('containerProc_clean')


###############################################################################
# End
###############################################################################

### local variables:
### no-byte-compile: t
### end:
