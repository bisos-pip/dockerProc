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
import shutil

from bisos import b
from bisos.b import cs
from bisos.b import b_io

import collections

from bisos.dockerProc import containerProc_seedInfo
from bisos.fileObj import ftoLeaf_seedInfo


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


def _isCgroupV2() -> bool:
    """True on a cgroup v2 (unified) host. Same test as 'stat -fc %T /sys/fs/cgroup' == cgroup2fs:
    only the unified hierarchy has cgroup.controllers at its root (v1 and hybrid do not)."""
    return pathlib.Path('/sys/fs/cgroup/cgroup.controllers').exists()


def _refuseIfCgroupV1() -> None:
    """Raise RuntimeError on a cgroup v1 (or hybrid) host.

    bisos.dockerProc supports cgroup v2 hosts only; cgroup v1 is considered
    obsolete here. The leaves' standalone scripts (imageBuild.sh,
    containerManage.sh) still support cgroup v1, through each privileged
    leaf's docker-compose.cgv1.yml.
    """
    if not _isCgroupV2():
        raise RuntimeError(
            "Refusing to run: this host is on cgroup v1 (or hybrid); /sys/fs/cgroup is not "
            "cgroup2fs. bisos.dockerProc supports cgroup v2 hosts only. On a cgroup v1 host, "
            "use the leaf's standalone ./imageBuild.sh and ./containerManage.sh instead "
            "(privileged leaves run there through docker-compose.cgv1.yml)."
        )


def _refuseIfUnsupportedHost() -> None:
    """Every engine-driving command runs only on a cgroup v2 host, not inside a container."""
    _refuseIfInContainer()
    _refuseIfCgroupV1()


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    _refuseIfUnsupportedHost()
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
# Instance checks --- the same checks as the leaves' standalone
# containerManage.sh, so that both ways refuse the same things.
###############################################################################

def _engineProblem(engine: str) -> str | None:
    """None if the engine is installed and usable by this user, else why not."""
    if shutil.which(engine) is None:
        return (f"{engine} is not installed on this host. Install it with "
                f"'{'dockerProc' if engine == 'docker' else 'podman'}-sbom.pcs -i sbom_apt_install'.")
    if subprocess.run([engine, 'info'], capture_output=True, check=False).returncode != 0:
        if engine == 'docker':
            return ("cannot talk to the docker daemon. Is it running? Are you in the docker "
                    "group (or do you need sudo)?")
        return "'podman info' fails for this user; rootless podman is not usable here."
    return None


def _containerState(engine: str, name: str) -> str | None:
    """The container's state (running, exited, created, ...), or None if it does not exist."""
    r = subprocess.run(
        [engine, 'container', 'inspect', '-f', '{{.State.Status}}', name],
        capture_output=True, text=True, check=False,
    )
    return r.stdout.strip() if r.returncode == 0 else None


def _imageExists(engine: str, image: str) -> bool:
    return subprocess.run(
        [engine, 'image', 'inspect', image], capture_output=True, check=False,
    ).returncode == 0


def _hostPortInUse(port: int) -> bool:
    """True if something on the host listens on TCP <port> (any address)."""
    r = subprocess.run(['ss', '-ltnH'], capture_output=True, text=True, check=False)
    for line in r.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[3].rsplit(':', 1)[-1] == str(port):
            return True
    return False


def _hostPorts(p: containerProc_seedInfo.ContainerParams) -> list[int]:
    return [p.sshPort, p.vncPort, p.novncPort]


def _spcsName(p: containerProc_seedInfo.ContainerParams) -> str:
    return pathlib.Path(p.plantPath).name


def _reportProblems(cmndOutcome: b.op.Outcome, what: str, problems: list[str]) -> b.op.Outcome:
    """Report every problem, then fail the command without changing anything."""
    for problem in problems:
        b_io.ann.note(f"PROBLEM: {problem}")
    b_io.ann.note(f"ERROR: not {what}.")
    return cmndOutcome.set(opError=b.op.OpError.Failure, opResults=f"not {what}: {problems}")


def _requireInstance(
    cmndOutcome: b.op.Outcome,
    p: containerProc_seedInfo.ContainerParams,
    what: str,
) -> b.op.Outcome | None:
    """None if the engine is usable and the instance exists; else a failed outcome."""
    engine = p.engine.value
    if (problem := _engineProblem(engine)) is not None:
        return _reportProblems(cmndOutcome, what, [problem])
    if _containerState(engine, p.containerName) is None:
        return _reportProblems(cmndOutcome, what, [
            f"container {p.containerName} does not exist. "
            f"Run: ./{_spcsName(p)} -i containerProc_instanceUp"])
    return None


###############################################################################
# commonParamsSpecify --- registers CS parameters used by the containerProc_*
# commands with the PyCS argparse layer. Without this, --noCache /
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

        if p.isSecondary:
            b_io.ann.note(f"{p.leafName} is an instance of the image of ../{p.primaryLeaf}; "
                          f"it has no image of its own. Build it there: "
                          f"( cd ../{p.primaryLeaf} && ./{_spcsName(p)} -i containerProc_imageBuild )")
            return cmndOutcome.set(opError=b.op.OpError.Success,
                                   opResults=f"No image of its own: built in ../{p.primaryLeaf}")
        _refuseIfUnsupportedHost()
        _copyRawBisosIfNeeded(leafDir)

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
        if p.isSecondary:
            b_io.ann.note(f"{p.leafName} has no image of its own; the shared image "
                          f"{p.imageName} is left alone (delete it in ../{p.primaryLeaf}).")
            return cmndOutcome.set(opError=b.op.OpError.Success,
                                   opResults=f"No image of its own: {p.leafName}")
        engine = p.engine.value
        _run([engine, 'rmi', p.imageName], check=False)
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Image deleted: {p.imageName}")


_RAW_BISOS_COPY_RE = r'^COPY.*\s\./raw-bisos(\s|$)'


def _copyRawBisosIfNeeded(contextDir: pathlib.Path) -> None:
    """Copy bro_dockerfiles/common/raw-bisos into a build context whose Dockerfile COPYs it.

    Same step as the leaves' standalone imageBuild.sh: the confined Dockerfile does
    'COPY ./raw-bisos ...', and the single canonical copy is common/raw-bisos (six
    levels up from a leaf). Removed first, so a repeat copy does not nest.
    """
    import re
    dockerfile = contextDir / 'Dockerfile'
    if not dockerfile.is_file() or not re.search(_RAW_BISOS_COPY_RE, dockerfile.read_text(), re.M):
        return
    source = contextDir.parents[5] / 'common' / 'raw-bisos'
    if not source.is_dir():
        raise RuntimeError(f"Missing Raw-BISOS payload directory: {source}")
    target = contextDir / 'raw-bisos'
    if target.is_symlink() or target.is_file():
        target.unlink()
    elif target.is_dir():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    b_io.ann.note(f"Copied {source} -> {target}")


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
        _copyRawBisosIfNeeded(baseContext)
        _run(
            ['podman', 'build', '--isolation=chroot']
            + noCacheFlag
            + ['-t', p.baseImage, str(baseContext)]
        )


###############################################################################
# Instance Commands --- operate on a running (or stopped) container instance.
# Anticipate Stage 4 Platform Registrar: will gain --instance=N arg later.
###############################################################################

def _instanceUp(
    cmndOutcome: b.op.Outcome,
    p: containerProc_seedInfo.ContainerParams,
    detach: bool = False,
    start: bool = True,
) -> b.op.Outcome:
    """Check, then create (if needed) and --- unless start=False --- start the instance.

    The body of containerProc_instanceUp. start=False creates without starting
    (docker compose up --no-start; podman create), for reMaterialize, which puts
    the VNC password back before the first start. A new podman container is
    always detached when start=False is followed by a separate start.
    """
    engine = p.engine.value
    leafDir = pathlib.Path(p.plantPath).parent
    composeFile = leafDir / 'docker-compose.yml'

    if (problem := _engineProblem(engine)) is not None:
        return _reportProblems(cmndOutcome, f"starting {p.containerName}", [problem])

    state = _containerState(engine, p.containerName)
    if state == 'running':
        b_io.ann.note(f"Container {p.containerName} is already running; nothing to do.")
        return cmndOutcome.set(opError=b.op.OpError.Success,
                               opResults=f"Already running: {p.containerName}")

    problems: list[str] = []
    if p.engine == containerProc_seedInfo.Engine.Docker and not composeFile.is_file():
        problems.append(f"{composeFile} is missing.")
    if not _imageExists(engine, p.imageName):
        build = (f"( cd ../{p.primaryLeaf} && ./{_spcsName(p)} -i containerProc_imageBuild )"
                 if p.isSecondary else f"./{_spcsName(p)} -i containerProc_imageBuild")
        problems.append(f"image {p.imageName} is not in {engine}'s local store. Run: {build}")
    for port in _hostPorts(p):
        if _hostPortInUse(port):
            problems.append(f"host port {port} is already in use.")
    if problems:
        return _reportProblems(cmndOutcome, f"starting {p.containerName}", problems)

    if p.engine == containerProc_seedInfo.Engine.Docker:
        # --no-build: building is containerProc_imageBuild's job, never a side effect here.
        upFlags = ['-d'] if start else ['--no-start']
        _run(['docker', 'compose', '-f', str(composeFile), 'up', *upFlags, '--no-build'])
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Up: {composeFile.name}")

    # podman rootless-sysd
    if state is not None:
        if start:
            _run(['podman', 'start', p.containerName])
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Started {p.containerName}")
    verb = (['run', '-d'] if detach else ['run']) if start else ['create']
    cmd = (
        ['podman', *verb, '--pids-limit=16384', '--systemd=always',
         '--stop-signal', 'SIGRTMIN+3']
        + [
            '--name', p.containerName,
            '-p', f'{p.sshPort}:22',
            '-p', f'{p.vncPort}:5901',
            '-p', f'{p.novncPort}:6901',
            '-v', f'{leafDir}:/shuttle/this',
            p.imageName,
        ]
    )
    _run(cmd)
    return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Started {p.containerName}")


class containerProc_instanceUp(cs.Cmnd):
    """Create (if needed) and start the container instance for this leaf.

    Dispatches on p.engine:
      - docker → 'docker compose up -d --no-build' with the leaf's docker-compose.yml.
      - podman → 'podman run --systemd=always --name <img> -p ...' for a new
        container, 'podman start <img>' for an existing stopped one.

    Already running: says so and changes nothing. Otherwise first checks, as the
    leaf's standalone containerManage.sh does before create, and if any check
    fails reports every problem and changes nothing:
      - the engine is installed and usable;
      - (docker) the leaf has a docker-compose.yml;
      - the image has been built (never built here: --no-build);
      - none of the instance's host ports is in use.
    cgroup v2 hosts only.

    For podman leaves, detach='true' runs a new container detached (default is
    foreground).
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
        """Check, then create + start instance. Dispatches on p.engine."""
        callParamsDict = {'detach': detach}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        _refuseIfUnsupportedHost()
        return _instanceUp(cmndOutcome, p, detach=bool(detach))


class containerProc_instanceDown(cs.Cmnd):
    """Stop the running container instance (does NOT remove --- use instanceDelete for that).

    Dispatches on p.engine:
      - docker → 'docker compose stop' (stop only; container still exists).
      - podman → 'podman stop' (stop only; container still exists).

    Fails, changing nothing, if the instance does not exist.
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
        """Stop instance. Dispatches on p.engine."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        _refuseIfUnsupportedHost()
        if (failed := _requireInstance(cmndOutcome, p, f"stopping {p.containerName}")) is not None:
            return failed
        if p.engine == containerProc_seedInfo.Engine.Docker:
            composeFile = pathlib.Path(p.plantPath).parent / 'docker-compose.yml'
            _run(['docker', 'compose', '-f', str(composeFile), 'stop'])
            return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Stopped: {composeFile.name}")
        else:
            # podman: stop (does not rm; use instanceDelete for stop+rm)
            _run(['podman', 'stop', p.containerName])
            return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Stopped {p.containerName}")


class containerProc_instanceDelete(cs.Cmnd):
    """Stop and remove the container instance (image is preserved).

    Dispatches on p.engine:
      - docker → 'docker compose down' removes the instance (and its network).
      - podman → 'podman stop && podman rm' (in sequence).

    The instance's writable layer is lost. Nothing to do if it does not exist.
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
        """Stop + remove instance. Dispatches on p.engine."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        _refuseIfUnsupportedHost()
        return _instanceDelete(cmndOutcome, p)


def _instanceDelete(
    cmndOutcome: b.op.Outcome,
    p: containerProc_seedInfo.ContainerParams,
) -> b.op.Outcome:
    """The body of containerProc_instanceDelete (also used by reMaterialize / unMaterialize)."""
    engine = p.engine.value
    if (problem := _engineProblem(engine)) is not None:
        return _reportProblems(cmndOutcome, f"deleting {p.containerName}", [problem])
    if _containerState(engine, p.containerName) is None:
        b_io.ann.note(f"Container {p.containerName} does not exist; nothing to delete.")
        return cmndOutcome.set(opError=b.op.OpError.Success,
                               opResults=f"No instance: {p.containerName}")
    b_io.ann.note("NOTE: deleting loses the container's writable layer; the image is kept.")
    if p.engine == containerProc_seedInfo.Engine.Docker:
        # 'docker compose down' already stops + removes.
        composeFile = pathlib.Path(p.plantPath).parent / 'docker-compose.yml'
        _run(['docker', 'compose', '-f', str(composeFile), 'down'])
        return cmndOutcome.set(opError=b.op.OpError.Success,
                               opResults=f"Instance deleted: {composeFile.name}")
    _run(['podman', 'stop', p.containerName], check=False)
    _run(['podman', 'rm', p.containerName])
    return cmndOutcome.set(opError=b.op.OpError.Success,
                           opResults=f"Instance deleted: {p.containerName}")


class containerProc_instanceRestart(cs.Cmnd):
    """Restart the container instance in place (stop + start; state preserved).

    Fails, changing nothing, if the instance does not exist.
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
        """engine restart <container>."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        _refuseIfUnsupportedHost()
        if (failed := _requireInstance(cmndOutcome, p, f"restarting {p.containerName}")) is not None:
            return failed
        engine = p.engine.value
        _run([engine, 'restart', p.containerName])
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"Restarted {p.containerName}")


###############################################################################
# VNC password --- optional. No password is the default: no (or an empty)
# password file in the container. /usr/local/bin/vncStart.sh in the image reads
# it at each VNC start. Same file and steps as the leaves' standalone
# containerManage.sh vncPassword set|clear.
###############################################################################

_VNC_PASSWD_PATH = '/home/bystar/.config/bisosVncPasswd'


def _vncAuthMode(engine: str, name: str) -> str:
    """'password' if the container holds a non-empty VNC password file, else 'none'.

    Read with 'cp <container>:<path> -' (a tar stream), which works on a stopped container.
    """
    import io
    import tarfile
    r = subprocess.run([engine, 'cp', f'{name}:{_VNC_PASSWD_PATH}', '-'],
                       capture_output=True, check=False)
    if r.returncode != 0 or not r.stdout:
        return 'none'
    try:
        with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
            member = tar.next()
            return 'password' if member is not None and member.size > 0 else 'none'
    except tarfile.TarError:
        return 'none'


class containerProc_instanceVncPassword(cs.Cmnd):
    """Set or clear the instance's VNC password. No password is the default.

    Args: =set= or =clear=.
      - set: asks for the password (twice, not echoed), makes the password file with
        the image's own =vncpasswd -f= in a throw-away container, copies it in.
      - clear: copies in an empty file --- back to no password.
    A running instance is restarted so that VNC uses the new setting. The password is
    lost on instanceDelete. Only its first 8 characters count, and VNC traffic is not
    encrypted: across a network, use an SSH tunnel.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = []
    cmndArgsLen = {'Min': 1, 'Max': 1}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """set | clear the VNC password of this leaf's instance."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        action = (argsList or [''])[0]
        p = _params()
        what = f"changing the VNC password of {p.containerName}"
        if action not in ('set', 'clear'):
            return _reportProblems(cmndOutcome, what, [f"argument must be set or clear, not {action!r}"])
        _refuseIfUnsupportedHost()
        if (failed := _requireInstance(cmndOutcome, p, what)) is not None:
            return failed
        engine = p.engine.value
        image = f"{p.imageName}:latest"

        # An image built before VNC passwords existed would ignore the file.
        hasVncStart = subprocess.run(
            [engine, 'run', '--rm', '--network', 'none', '--entrypoint', 'test',
             image, '-x', '/usr/local/bin/vncStart.sh'],
            capture_output=True, check=False,
        ).returncode == 0
        if not hasVncStart:
            return _reportProblems(cmndOutcome, what, [
                f"image {image} has no /usr/local/bin/vncStart.sh, so it would ignore a VNC "
                f"password. Rebuild it (./{_spcsName(p)} -i containerProc_imageBuild, its "
                f"confined base first), then instanceDelete + instanceUp."])

        import getpass
        import tempfile
        content = b''
        if action == 'set':
            pw1 = getpass.getpass("New VNC password: ")
            pw2 = getpass.getpass("Same password again: ")
            if not pw1:
                return _reportProblems(cmndOutcome, what, [
                    "empty password. For no password: containerProc_instanceVncPassword clear"])
            if pw1 != pw2:
                return _reportProblems(cmndOutcome, what, ["the two passwords differ; nothing changed."])
            if len(pw1) > 8:
                b_io.ann.note("NOTE: VNC uses only the first 8 characters of the password.")
            # The password goes through stdin, never the command line.
            gen = subprocess.run(
                [engine, 'run', '--rm', '-i', '--network', 'none', '--entrypoint', 'vncpasswd',
                 image, '-f'],
                input=(pw1 + '\n').encode(), capture_output=True, check=False,
            )
            if gen.returncode != 0 or not gen.stdout:
                return _reportProblems(cmndOutcome, what, ["vncpasswd produced no output; nothing changed."])
            content = gen.stdout

        # 'clear' copies in an empty file: vncStart.sh then runs VNC with no password.
        with tempfile.NamedTemporaryFile(prefix='bisosVncPasswd.') as tmp:
            tmp.write(content)
            tmp.flush()
            _run([engine, 'cp', tmp.name, f'{p.containerName}:{_VNC_PASSWD_PATH}'])

        if _containerState(engine, p.containerName) == 'running':
            b_io.ann.note(f"Restarting {p.containerName} so that VNC uses the new setting.")
            _run([engine, 'restart', p.containerName])
        else:
            b_io.ann.note("It takes effect when the instance starts.")
        mode = 'password' if action == 'set' else 'none'
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"VNC auth: {mode}")


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
        _run([engine, 'ps', '-a', '--filter', f'name={p.containerName}'])
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
        _run([engine, 'logs'] + followFlag + [p.containerName], check=False)
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults="logs shown")


class containerProc_instanceExec(cs.Cmnd):
    """Exec a command inside the running container.

    Positional args (after =--=) go straight to =<engine> exec -it <container> ...=.
    With no args, drops into interactive bash.

    Examples:
      containerProc_instanceExec                    # interactive bash
      containerProc_instanceExec -- uname -a        # run uname -a
      containerProc_instanceExec -- ls -la /home    # run ls with args

    Legacy: =execCmd='<cmd>'= still supported for single-command invocation
    without =--= --- kept for backward compatibility; prefer positional args.

    Note: on old Podman (4.3.1), 'exec' into a rootless systemd container may
    fail with a cgroup.procs permission error --- use SSH instead
    (ssh -p <sshPort> bystar@localhost).
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['execCmd']
    cmndArgsLen = {'Min': 0, 'Max': 9999}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        execCmd: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """engine exec -it <container> <argsList...> | execCmd | bash."""
        callParamsDict = {'execCmd': execCmd}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value

        # Precedence: positional args > --execCmd > interactive bash
        if argsList:
            argv = [engine, 'exec', '-it', p.containerName, *argsList]
            resultLabel = f"exec {' '.join(argsList)}"
        elif execCmd:
            argv = [engine, 'exec', '-it', p.containerName, execCmd]
            resultLabel = f"exec {execCmd}"
        else:
            argv = [engine, 'exec', '-it', p.containerName, 'bash']
            resultLabel = "exec bash"

        _run(argv, check=False)
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=resultLabel)


###############################################################################
# exec_* --- one-shot install / post-install scripts inside the container.
# These are convenience wrappers over 'engine exec': they know a specific
# script path + invocation pattern, so the user doesn't have to remember it.
###############################################################################

class containerProc_exec_installRawBisos(cs.Cmnd):
    """Run ~/raw-bisos/installRawBisos.sh inside the running container.

    installRawBisos.sh (part of the image at /home/<user>/raw-bisos/) refreshes
    raw-bisos.sh via wget from bxGenesis/start and then runs it
    non-interactively as =raw-bisos.sh -v -n showRun -i installUnsitedBisos=.

    Roughly equivalent to:
      <engine> exec -it <container> bash -l -c 'cd ~/raw-bisos && bash installRawBisos.sh'

    The container's image default USER (typically =bystar=) is honored --- no =-u=.
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
        """engine exec -u bystar <container> bash -l -c 'cd ~/raw-bisos && bash installRawBisos.sh'."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        p = _params()
        engine = p.engine.value
        # Run as bystar (not the image's default USER, which is root on sysd/privileged
        # leaves) so ~ resolves to /home/bystar. No -t: this is driven non-interactively
        # and 'exec -it' aborts with "the input device is not a TTY".
        result = _run(
            [engine, 'exec', '-u', 'bystar', p.containerName,
             'bash', '-l', '-c', 'cd ~/raw-bisos && bash installRawBisos.sh'],
            check=False,
        )
        if result.returncode != 0:
            return b_io.eh.badOutcome(cmndOutcome)
        return cmndOutcome.set(
            opError=b.op.OpError.Success,
            opResults="ran installRawBisos.sh",
        )


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
        _refuseIfUnsupportedHost()
        failures: list[str] = []
        warnings: list[str] = []

        # 1. Container running?
        engine = p.engine.value
        inspect = subprocess.run(
            [engine, 'inspect', '--format', '{{.State.Status}}', p.containerName],
            capture_output=True, text=True, check=False,
        )
        if inspect.returncode != 0 or inspect.stdout.strip() != 'running':
            failures.append(f"Container {p.containerName} not running")
        else:
            b_io.ann.note(f"PASS: container {p.containerName} running")

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
        _refuseIfUnsupportedHost()
        engine = p.engine.value

        _run([engine, 'inspect', p.containerName], check=False)

        if _containerState(engine, p.containerName) is not None:
            b_io.ann.note(f"VNC auth: {_vncAuthMode(engine, p.containerName)}")

        # SSH systemd summary if running
        inspect = subprocess.run(
            [engine, 'inspect', '--format', '{{.State.Status}}', p.containerName],
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
        _refuseIfUnsupportedHost()
        engine = p.engine.value

        subprocess.run([engine, 'stop', p.containerName], check=False)
        subprocess.run([engine, 'rm', p.containerName], check=False)
        if p.isSecondary:
            b_io.ann.note(f"Shared image {p.imageName} left alone (delete it in ../{p.primaryLeaf}).")
        else:
            subprocess.run([engine, 'rmi', p.imageName], check=False)

        return cmndOutcome.set(opError=b.op.OpError.Success,
                               opResults=f"fullClean: {p.containerName}")


###############################################################################
# The generic lifecycle verbs (fto_prepare ... fto_status) come from bisos.fileObj
# (ftoLeaf_csu, on this seed's csuList; design: bisos.fileObj's README, "Generic
# Lifecycle Verbs"). fileObj owns the verbs, the gate (<leaf>/dockerProc.control,
# podmanProc.control) and the status log; this package registers only what each
# verb does for a container leaf (the _lifecycle* actions at the end of this
# section, ftoLeaf_seedInfo.setup(...)), plus the container-specific staleness checks.
###############################################################################

# --- Staleness ---------------------------------------------------------------

def _inspectField(engine: str, kind: str, ref: str, field: str) -> str | None:
    r = subprocess.run([engine, kind, 'inspect', '-f', '{{' + field + '}}', ref],
                       capture_output=True, text=True, check=False)
    return r.stdout.strip() if r.returncode == 0 else None


def _bareId(imageId: str | None) -> str:
    return (imageId or '').removeprefix('sha256:')


def _createdTime(text: str | None) -> float | None:
    """Seconds since the epoch from docker's (RFC 3339) or podman's (Go time) 'Created'."""
    import datetime
    import re
    if not text:
        return None
    m = re.match(r'(\d{4}-\d\d-\d\d)[T ](\d\d:\d\d:\d\d)(\.\d+)?\s*(Z|[+-]\d\d:?\d\d)?', text)
    if not m:
        return None
    when = datetime.datetime.fromisoformat(f"{m.group(1)}T{m.group(2)}")
    zone = m.group(4) or 'Z'
    if zone == 'Z':
        offset = datetime.timedelta(0)
    else:
        sign = 1 if zone[0] == '+' else -1
        digits = zone[1:].replace(':', '')
        offset = sign * datetime.timedelta(hours=int(digits[:2]), minutes=int(digits[2:]))
    when = when.replace(tzinfo=datetime.timezone(offset))
    return when.timestamp() + float(m.group(3) or 0)


def _imageStaleness(p: containerProc_seedInfo.ContainerParams) -> tuple[str, str]:
    """('notBuilt' | 'stale' | 'current' | 'secondary', explanation)."""
    engine = p.engine.value
    if p.isSecondary:
        return 'secondary', f"no image of its own (built in ../{p.primaryLeaf})"
    created = _createdTime(_inspectField(engine, 'image', p.imageName, '.Created'))
    if created is None:
        return 'notBuilt', f"image {p.imageName} is not in {engine}'s local store"
    if p.profile == containerProc_seedInfo.Profile.Confined or not p.baseImage:
        return 'current', f"image {p.imageName} exists (FROM an external base)"
    baseCreated = _createdTime(_inspectField(engine, 'image', p.baseImage, '.Created'))
    if baseCreated is None:
        return 'stale', f"its base {p.baseImage} is not in {engine}'s local store"
    if created < baseCreated:
        return 'stale', f"{p.imageName} is older than its base {p.baseImage}"
    return 'current', f"{p.imageName} is newer than its base {p.baseImage}"


def _instanceStaleness(p: containerProc_seedInfo.ContainerParams) -> tuple[str, str]:
    """('noInstance' | 'notBuilt' | 'stale' | 'current', explanation)."""
    engine = p.engine.value
    usedId = _bareId(_inspectField(engine, 'container', p.containerName, '.Image'))
    if not usedId:
        return 'noInstance', f"container {p.containerName} does not exist"
    tagId = _bareId(_inspectField(engine, 'image', f"{p.imageName}:latest", '.Id'))
    if not tagId:
        return 'notBuilt', f"image {p.imageName}:latest is not in {engine}'s local store"
    if usedId != tagId:
        return 'stale', f"{p.containerName} runs an older {p.imageName} (re-create to use the current one)"
    return 'current', f"{p.containerName} runs the current {p.imageName}"


class _StalenessMixin:
    """Behaviour of the two read-only staleness checks; subclasses set _check and _label.

    A mixin, not a cs.Cmnd: PyCS dispatches only *direct* subclasses of cs.Cmnd that are
    top-level classes in the source, so each check is class x(_StalenessMixin, cs.Cmnd).
    """
    cmndParamsMandatory = []
    cmndParamsOptional = []
    cmndArgsLen = {'Min': 0, 'Max': 0}
    _label = ''

    @staticmethod
    def _check(p: containerProc_seedInfo.ContainerParams) -> tuple[str, str]:
        raise NotImplementedError

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """Print '<leaf>: <label> <verdict> --- <why>'."""
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)
        p = _params()
        _refuseIfUnsupportedHost()
        if (problem := _engineProblem(p.engine.value)) is not None:
            return _reportProblems(cmndOutcome, f"checking {p.leafName}", [problem])
        verdict, why = self._check(p)
        b_io.ann.write(f"{p.leafName}: {self._label} {verdict} --- {why}")
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=verdict)


class containerProc_imageIsStale(_StalenessMixin, cs.Cmnd):
    """Read-only. Is this leaf's image older than its base image (a rebuild is due)?

    Verdicts: current | stale | notBuilt | secondary (no image of its own).
    """
    _label = 'image'
    _check = staticmethod(_imageStaleness)


class containerProc_instanceIsStale(_StalenessMixin, cs.Cmnd):
    """Read-only. Does this leaf's instance run an older image than the tag's current one?

    Verdicts: current | stale | noInstance | notBuilt. 'stale' is what reMaterialize re-creates.
    """
    _label = 'instance'
    _check = staticmethod(_instanceStaleness)


# --- Helpers of the lifecycle actions ----------------------------------------

def _vncPasswdRead(engine: str, name: str) -> bytes:
    """The instance's VNC password file content (b'' if none), read with 'cp ... -' (a tar stream)."""
    import io
    import tarfile
    r = subprocess.run([engine, 'cp', f'{name}:{_VNC_PASSWD_PATH}', '-'],
                       capture_output=True, check=False)
    if r.returncode != 0 or not r.stdout:
        return b''
    try:
        with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
            member = tar.next()
            handle = tar.extractfile(member) if member is not None else None
            return handle.read() if handle is not None else b''
    except tarfile.TarError:
        return b''


def _vncPasswdWrite(engine: str, name: str, content: bytes) -> None:
    import tempfile
    with tempfile.NamedTemporaryFile(prefix='bisosVncPasswd.') as tmp:
        tmp.write(content)
        tmp.flush()
        _run([engine, 'cp', tmp.name, f'{name}:{_VNC_PASSWD_PATH}'])


def _instanceStart(p: containerProc_seedInfo.ContainerParams) -> None:
    if p.engine == containerProc_seedInfo.Engine.Docker:
        composeFile = pathlib.Path(p.plantPath).parent / 'docker-compose.yml'
        _run(['docker', 'compose', '-f', str(composeFile), 'start'])
    else:
        _run(['podman', 'start', p.containerName])


# --- The lifecycle actions, registered with bisos.fileObj --------------------------
# Each is (cmndOutcome) -> b.op.Outcome, called by fileObj's fto_<verb> after its gate
# check; fileObj writes the status line.

def _lifecycleParams() -> containerProc_seedInfo.ContainerParams:
    p = _params()
    _refuseIfUnsupportedHost()
    return p


def _lifecyclePrepare(cmndOutcome: b.op.Outcome) -> b.op.Outcome:
    """prepare = containerProc_imageBuild (nothing to build in a secondary leaf)."""
    return containerProc_imageBuild().cmnd(rtInv=cs.RtInvoker.new_py(), cmndOutcome=cmndOutcome)


def _lifecycleMaterialize(cmndOutcome: b.op.Outcome) -> b.op.Outcome:
    """materialize = instanceUp, detached: running is left alone, stopped is started."""
    return _instanceUp(cmndOutcome, _lifecycleParams(), detach=True)


def _lifecycleReMaterialize(cmndOutcome: b.op.Outcome) -> b.op.Outcome:
    """reMaterialize: re-create a stale instance from the current image, keeping its VNC password.

    No instance: create and start it. Current instance: nothing to do. Stale instance (it runs
    an older image than the tag's): save the VNC password, delete, create without starting,
    put the password back, start. Everything else inside the old container (e.g. a Raw-BISOS
    installation) is lost --- /shuttle/share and /shuttle/this are outside it and survive.
    """
    p = _lifecycleParams()
    engine = p.engine.value
    if (problem := _engineProblem(engine)) is not None:
        return _reportProblems(cmndOutcome, f"re-materializing {p.containerName}", [problem])
    verdict, why = _instanceStaleness(p)
    if verdict == 'noInstance':
        return _instanceUp(cmndOutcome, p, detach=True)
    if verdict == 'current':
        b_io.ann.note(f"{p.leafName}: {why}; nothing to do.")
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults="current: nothing to do")
    if verdict == 'notBuilt':
        return _reportProblems(cmndOutcome, f"re-materializing {p.containerName}", [why])
    b_io.ann.note(f"{p.leafName}: {why}.")
    vncPasswd = _vncPasswdRead(engine, p.containerName)
    outcome = _instanceDelete(cmndOutcome, p)
    if outcome.error != b.op.OpError.Success:
        return outcome
    outcome = _instanceUp(cmndOutcome, p, start=False)
    if outcome.error != b.op.OpError.Success:
        return outcome
    if vncPasswd:
        _vncPasswdWrite(engine, p.containerName, vncPasswd)
        b_io.ann.note("VNC password kept across the re-create.")
    _instanceStart(p)
    return cmndOutcome.set(opError=b.op.OpError.Success,
                           opResults=f"re-created {p.containerName} from the current {p.imageName}")


def _lifecycleUnMaterialize(cmndOutcome: b.op.Outcome) -> b.op.Outcome:
    """unMaterialize = instanceDelete (the image is kept)."""
    return _instanceDelete(cmndOutcome, _lifecycleParams())


def _lifecycleClean(cmndOutcome: b.op.Outcome) -> b.op.Outcome:
    """clean: remove the leaf's image and its copied raw-bisos/ build context.

    Refuses while any container (running or stopped) uses the image. In a secondary leaf
    there is nothing to clean: the shared image belongs to the primary leaf.
    """
    import re
    p = _lifecycleParams()
    engine = p.engine.value
    if p.isSecondary:
        b_io.ann.note(f"{p.leafName}: no image of its own; the shared {p.imageName} is left alone.")
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults="secondary: nothing to clean")
    if (problem := _engineProblem(engine)) is not None:
        return _reportProblems(cmndOutcome, f"cleaning {p.imageName}", [problem])
    users = subprocess.run(
        [engine, 'ps', '-a', '--filter', f'ancestor={p.imageName}', '--format', '{{.Names}}'],
        capture_output=True, text=True, check=False,
    ).stdout.split()
    if users:
        return _reportProblems(cmndOutcome, f"cleaning {p.imageName}", [
            f"containers still use {p.imageName}: {', '.join(users)}. "
            f"Delete them first (fto_unMaterialize / containerProc_instanceDelete)."])
    if _imageExists(engine, p.imageName):
        _run([engine, 'rmi', p.imageName])
    leafDir = pathlib.Path(p.plantPath).parent
    dockerfile = leafDir / 'Dockerfile'
    rawBisos = leafDir / 'raw-bisos'
    if (dockerfile.is_file() and re.search(_RAW_BISOS_COPY_RE, dockerfile.read_text(), re.M)
            and rawBisos.is_dir() and not rawBisos.is_symlink()):
        shutil.rmtree(rawBisos)
        b_io.ann.note(f"Removed the copied build context {rawBisos}")
    return cmndOutcome.set(opError=b.op.OpError.Success, opResults=f"cleaned {p.imageName}")


def _lifecycleVerify(cmndOutcome: b.op.Outcome) -> b.op.Outcome:
    """verify = containerProc_instanceVerify."""
    return containerProc_instanceVerify().cmnd(rtInv=cs.RtInvoker.new_py(), cmndOutcome=cmndOutcome)


def _lifecycleStatus(cmndOutcome: b.op.Outcome) -> b.op.Outcome:
    """status = containerProc_instanceStatus."""
    return containerProc_instanceStatus().cmnd(rtInv=cs.RtInvoker.new_py(), cmndOutcome=cmndOutcome)


ftoLeaf_seedInfo.setup(
    prepare=_lifecyclePrepare,
    materialize=_lifecycleMaterialize,
    reMaterialize=_lifecycleReMaterialize,
    unMaterialize=_lifecycleUnMaterialize,
    clean=_lifecycleClean,
    verify=_lifecycleVerify,
    status=_lifecycleStatus,
)


###############################################################################
# Backup / Snapshot helpers
###############################################################################

def _backupsDir(p: containerProc_seedInfo.ContainerParams) -> pathlib.Path:
    """BISOS-convention backup directory for the planted leaf.

    Path: /bisos/var/dockerProc/backups/<user>/<imageName>/

    Ensures the directory exists and drops two symlinks the first time it's
    called (idempotent):

      <leafDir>/backups          → /bisos/var/dockerProc/backups/<user>/<imageName>/
      /bisos/var/.../leaf        → <leafDir>/
    """
    import getpass
    user = getpass.getuser()
    backupsDir = pathlib.Path("/bisos/var/dockerProc/backups") / user / p.imageName
    backupsDir.mkdir(parents=True, exist_ok=True)

    leafDir = pathlib.Path(p.plantPath).parent

    # leaf -> backups
    leafBackupsLink = leafDir / "backups"
    if not leafBackupsLink.exists() and not leafBackupsLink.is_symlink():
        try:
            leafBackupsLink.symlink_to(backupsDir)
        except OSError as exc:
            b_io.ann.write(f"warn: could not create {leafBackupsLink} -> {backupsDir}: {exc}")

    # backups -> leaf
    backupsLeafLink = backupsDir / "leaf"
    if not backupsLeafLink.exists() and not backupsLeafLink.is_symlink():
        try:
            backupsLeafLink.symlink_to(leafDir)
        except OSError as exc:
            b_io.ann.write(f"warn: could not create {backupsLeafLink} -> {leafDir}: {exc}")

    return backupsDir


###############################################################################
# containerProc_instanceCommit --- snapshot the running container to a new image tag.
#
# Scenario A ("Checkpoint my experimental container"). Commits the running
# instance's writable layer as a new image, tagged <imageName>:snapshot-<timestamp>
# (or a user-supplied tag). Does NOT capture volumes.
###############################################################################

class containerProc_instanceCommit(cs.Cmnd):
    """Snapshot the running instance to a new image tag (docker commit / podman commit).

    Captures the writable layer only. Does NOT capture volumes.
    Default tag is <leafName>:snapshot-<YYYYmmdd-HHMMSS>; override with --tag=.

    Optional --message= and --author= populate commit metadata.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['tag', 'message', 'author']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        tag: typing.Optional[str] = None,
        message: typing.Optional[str] = None,
        author: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """engine commit <container> <imageName>:<tag>"""
        callParamsDict = {'tag': tag, 'message': message, 'author': author}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        import datetime

        p = _params()
        engine = p.engine.value

        if tag is None:
            tag = f"snapshot-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

        targetTag = f"{p.leafName}:{tag}"

        cmd = [engine, 'commit']
        if message:
            cmd += ['-m', message]
        if author:
            cmd += ['-a', author]
        # The snapshot is named after the instance's leaf (for a secondary leaf, not the shared image).
        cmd += [p.containerName, targetTag]

        _run(cmd)
        b_io.ann.write(f"committed {p.containerName} -> {targetTag}")
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=targetTag)


###############################################################################
# containerProc_imageSave --- portable export of an image to a tarball.
#
# Scenario B ("Transfer this image to another host"). Saves the image (default:
# <imageName>:latest, or --tag= to save a specific tag such as a commit
# snapshot) to a tarball under /bisos/var/dockerProc/backups/<user>/<imageName>/.
###############################################################################

class containerProc_imageSave(cs.Cmnd):
    """Save the image to a portable tarball (docker save / podman save).

    Default source: the leaf's <imageName>:latest. Override with --tag= to
    save a specific tag (e.g. a commit snapshot).

    Default output path:
        /bisos/var/dockerProc/backups/<user>/<imageName>/<imageName>-<tag>-<timestamp>.tar
    Override with --outPath=. First invocation creates the backup directory
    and lays down symlinks between the backup dir and the leaf.
    """
    cmndParamsMandatory = []
    cmndParamsOptional = ['tag', 'outPath']
    cmndArgsLen = {'Min': 0, 'Max': 0}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(
        self,
        rtInv: cs.RtInvoker,
        cmndOutcome: b.op.Outcome,
        tag: typing.Optional[str] = None,
        outPath: typing.Optional[str] = None,
        argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """engine save <image>:<tag> -o <outPath>"""
        callParamsDict = {'tag': tag, 'outPath': outPath}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return b_io.eh.badOutcome(cmndOutcome)

        import datetime

        p = _params()
        engine = p.engine.value

        srcTag = tag if tag else "latest"
        srcImage = f"{p.imageName}:{srcTag}"

        if outPath is None:
            backupsDir = _backupsDir(p)
            timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            outFile = backupsDir / f"{p.imageName}-{srcTag}-{timestamp}.tar"
        else:
            outFile = pathlib.Path(outPath).expanduser().resolve()
            outFile.parent.mkdir(parents=True, exist_ok=True)

        _run([engine, 'save', srcImage, '-o', str(outFile)])
        b_io.ann.write(f"saved {srcImage} -> {outFile}")
        return cmndOutcome.set(opError=b.op.OpError.Success, opResults=str(outFile))


###############################################################################
# Backward-compat aliases --- one release only, then remove.
# Old Cmnd names get shims that emit a DeprecationWarning and delegate to the
# new class. Anything that references the old names via CLI still works during
# the transition.
###############################################################################

import warnings as _warnings


class _AliasMixin:
    """Run another command class: an alias that is still a *direct* cs.Cmnd subclass.

    PyCS dispatches only names that are top-level classes in the source and direct
    subclasses of cs.Cmnd, so an alias cannot simply derive from its target. Use as
    class alias(_AliasMixin, cs.Cmnd) with _target set and the target's parameter
    declarations copied (the dispatcher reads them from the alias).
    """
    _target: typing.Any = None

    def cmnd(self, rtInv, cmndOutcome, **kwArgs):
        return self._target().cmnd(rtInv=rtInv, cmndOutcome=cmndOutcome, **kwArgs)


class _DeprecatedNameMixin(_AliasMixin):
    """An alias (see _AliasMixin) that first warns that its name is deprecated."""

    def cmnd(self, rtInv, cmndOutcome, **kwArgs):
        _warnings.warn(
            f"{type(self).__name__} is deprecated; use {self._target.__name__} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return super().cmnd(rtInv, cmndOutcome, **kwArgs)


class containerProc_build(_DeprecatedNameMixin, cs.Cmnd):
    """Deprecated name of containerProc_imageBuild."""
    _target = containerProc_imageBuild
    cmndParamsMandatory = containerProc_imageBuild.cmndParamsMandatory
    cmndParamsOptional = containerProc_imageBuild.cmndParamsOptional
    cmndArgsLen = containerProc_imageBuild.cmndArgsLen


class containerProc_composeUp(_DeprecatedNameMixin, cs.Cmnd):
    """Deprecated name of containerProc_instanceUp."""
    _target = containerProc_instanceUp
    cmndParamsMandatory = containerProc_instanceUp.cmndParamsMandatory
    cmndParamsOptional = containerProc_instanceUp.cmndParamsOptional
    cmndArgsLen = containerProc_instanceUp.cmndArgsLen


class containerProc_composeDown(_DeprecatedNameMixin, cs.Cmnd):
    """Deprecated name of containerProc_instanceDown."""
    _target = containerProc_instanceDown
    cmndParamsMandatory = containerProc_instanceDown.cmndParamsMandatory
    cmndParamsOptional = containerProc_instanceDown.cmndParamsOptional
    cmndArgsLen = containerProc_instanceDown.cmndArgsLen


class containerProc_run(_DeprecatedNameMixin, cs.Cmnd):
    """Deprecated name of containerProc_instanceUp."""
    _target = containerProc_instanceUp
    cmndParamsMandatory = containerProc_instanceUp.cmndParamsMandatory
    cmndParamsOptional = containerProc_instanceUp.cmndParamsOptional
    cmndArgsLen = containerProc_instanceUp.cmndArgsLen


class containerProc_verify(_DeprecatedNameMixin, cs.Cmnd):
    """Deprecated name of containerProc_instanceVerify."""
    _target = containerProc_instanceVerify
    cmndParamsMandatory = containerProc_instanceVerify.cmndParamsMandatory
    cmndParamsOptional = containerProc_instanceVerify.cmndParamsOptional
    cmndArgsLen = containerProc_instanceVerify.cmndArgsLen


class containerProc_status(_DeprecatedNameMixin, cs.Cmnd):
    """Deprecated name of containerProc_instanceStatus."""
    _target = containerProc_instanceStatus
    cmndParamsMandatory = containerProc_instanceStatus.cmndParamsMandatory
    cmndParamsOptional = containerProc_instanceStatus.cmndParamsOptional
    cmndArgsLen = containerProc_instanceStatus.cmndArgsLen


class containerProc_clean(_DeprecatedNameMixin, cs.Cmnd):
    """Deprecated name of containerProc_fullClean."""
    _target = containerProc_fullClean
    cmndParamsMandatory = containerProc_fullClean.cmndParamsMandatory
    cmndParamsOptional = containerProc_fullClean.cmndParamsOptional
    cmndArgsLen = containerProc_fullClean.cmndArgsLen


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

        cs.examples.menuSection('/Podman Backup + Restore --- commit, save/load, export/import, volume backup/')
        literal("# See Blee panel: /bisos/panels/bisos-core/virtualization/docker/backupAndRestore/")
        literal("# ")
        literal("# Commit --- snapshot a running container's writable layer as a new image layer.")
        literal("# Does NOT capture volumes. Use for one-off checkpoints, not reproducible builds.")
        literal(f"podman commit {oneContainerId} myimage:snapshot-$(date +%Y%m%d)")
        literal(f"podman commit -m 'checkpoint' -a 'me <me@ex>' {oneContainerId} myimage:snapshot")
        literal("# ")
        literal("# Image save + load --- portable image transfer (all layers, metadata).")
        literal("# RECOMMENDED for image transfer between hosts.")
        literal(f"podman save {oneImageId} -o /bisos/var/dockerProc/backups/${{USER}}/<imageName>/<imageName>-$(date +%Y%m%d-%H%M%S).tar")
        literal(f"podman save --format oci-archive {oneImageId} -o backup.oci  # OCI format alternative")
        literal("podman load -i backup.tar                         # restore on receiving host")
        literal("# ")
        literal("# Container export + import --- flat filesystem, no layer history.")
        literal(f"podman export {oneContainerId} -o fs.tar")
        literal("podman import fs.tar newimage:imported")
        literal("# ")
        literal("# Volume backup --- podman has a native command as well.")
        literal("podman volume ls")
        literal("podman volume export myvol -o myvol.tar             # native, preferred")
        literal("podman volume import myvol myvol.tar                # native restore")
        literal("# Or the helper-container idiom (works with both docker and podman):")
        literal("podman run --rm -v myvol:/data -v $(pwd):/backup alpine tar czf /backup/myvol.tgz /data")
        literal("# ")
        literal("# BISOS convention: backup tarballs live at")
        literal("#   /bisos/var/dockerProc/backups/<user>/<imageName>/<imageName>-<timestamp>.tar")
        literal("# The containerProc_imageSave Cmnd (see .spcs -i examples) automates this path.")

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
    """Examples menu, filtered by p.engine and p.profile.

    Reads params from the planted path so the menu shows only commands and
    options relevant to *this* leaf: no docker-compose commands on rootless-sysd
    leaves, no podman run on docker leaves. (cgroup v2 hosts only.)

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

    cs.examples.menuChapter(
        f'*containerProc for {p.containerName}* '
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
        cmnd('containerProc_instanceUp',
             comment="# checks, then docker compose up -d --no-build")
        cmnd('containerProc_instanceDown', comment="# docker compose stop")
    elif isPodman:
        cmnd('containerProc_instanceUp', pars=od([('detach', 'true')]),
             comment="# checks, then podman run --systemd=always -d (or start)")
        cmnd('containerProc_instanceDown', comment="# podman stop")

    cmnd('containerProc_instanceRestart')
    cmnd('containerProc_instancePs', comment="# ps -a filtered to this leaf")
    cmnd('containerProc_instanceLogs')
    cmnd('containerProc_instanceLogs', pars=od([('follow', 'true')]),
         comment="# follow (tail -f)")
    cmnd('containerProc_instanceExec', comment="# interactive bash")
    cs.examples.execInsert(
        "./dockerProc.spcs -i containerProc_instanceExec -- uname -a"
    )
    cs.examples.execInsert(
        "./dockerProc.spcs -i containerProc_instanceExec -- cat /etc/debian_version"
    )
    cs.examples.execInsert(
        "./dockerProc.spcs -i containerProc_instanceExec -- ls -la /home/bystar/raw-bisos"
    )
    if isPodman:
        # Rootless-sysd exec-into is unreliable on old Podman; SSH is preferred
        cs.examples.execInsert(
            f"ssh -p {p.sshPort} bystar@localhost   # preferred for rootless-sysd"
        )

    cs.examples.menuSection('Install (one-shot inside container)')
    cmnd('containerProc_exec_installRawBisos',
         comment="# cd ~/raw-bisos && bash installRawBisos.sh")

    cmnd('containerProc_instanceDelete', comment="# stop + rm instance (keeps image)")

    cs.examples.menuSection('VNC Password (optional; no password is the default)')
    cmnd('containerProc_instanceVncPassword', args="set",
         comment="# asks for a password; VNC and noVNC then require it")
    cmnd('containerProc_instanceVncPassword', args="clear",
         comment="# back to no password")

    # -----------------------------------------------------------------
    # Verify + Status
    # -----------------------------------------------------------------
    cs.examples.menuSection('Verify + Status')
    cmnd('containerProc_instanceVerify')
    cmnd('containerProc_instanceStatus')

    # -----------------------------------------------------------------
    # Backup / Snapshot --- Scenarios A + B (see docker/backupAndRestore Blee panel)
    # -----------------------------------------------------------------
    cs.examples.menuSection('Backup / Snapshot')
    cmnd('containerProc_instanceCommit',
         comment=f"# snapshot the running {p.containerName} -> {p.leafName}:snapshot-<timestamp>")
    cmnd('containerProc_instanceCommit',
         pars=od([('tag', 'checkpoint')]),
         comment="# ... with an explicit tag")
    cmnd('containerProc_instanceCommit',
         pars=od([('tag', 'checkpoint'), ('message', 'before X'), ('author', 'me <me@ex>')]),
         comment="# ... with commit metadata")
    cmnd('containerProc_imageSave',
         comment=f"# save {p.imageName}:latest -> /bisos/var/dockerProc/backups/<user>/{p.imageName}/")
    cmnd('containerProc_imageSave',
         pars=od([('tag', 'snapshot-20260813-120000')]),
         comment="# save a specific tag (e.g. a prior commit snapshot)")
    cmnd('containerProc_imageSave',
         pars=od([('outPath', '/tmp/my-backup.tar')]),
         comment="# override the default backup path")
    cs.examples.execInsert(
        f"{p.engine.value} load -i /bisos/var/dockerProc/backups/$USER/{p.imageName}/{p.imageName}-latest-<timestamp>.tar"
        f"   # restore on this or another host (plain {p.engine.value} load)"
    )

    # -----------------------------------------------------------------
    # Staleness, and the FTO lifecycle verbs + gate (from bisos.fileObj)
    # -----------------------------------------------------------------
    cs.examples.menuSection('Staleness (read-only)')
    cmnd('containerProc_imageIsStale', comment="# image older than its base?")
    cmnd('containerProc_instanceIsStale', comment="# instance on an older image than its tag?")

    ftoLeaf_seedInfo.lifecycleExamplesMenu()

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
    cmnd('containerProc_instanceUp', pars=od([('detach', 'true')]))
    cmnd('containerProc_instanceDown')
    cmnd('containerProc_instanceRestart')
    cmnd('containerProc_instancePs')
    cmnd('containerProc_instanceLogs')
    cmnd('containerProc_instanceLogs', pars=od([('follow', 'true')]))
    cmnd('containerProc_instanceExec')
    cs.examples.execInsert("dockerProc.spcs -i containerProc_instanceExec -- uname -a")
    cmnd('containerProc_exec_installRawBisos')
    cmnd('containerProc_instanceDelete')
    cmnd('containerProc_instanceVncPassword', args="set")
    cmnd('containerProc_instanceVncPassword', args="clear")

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
