# -*- coding: utf-8 -*-

""" #+begin_org
* ~[Summary]~ :: SeedInfo for containerProc — path-derived parameters for Docker/Podman leaf images
#+end_org """

####+BEGIN: b:py3:cs:file/dblockControls :classification "cs-u"
""" #+begin_org
* [[elisp:(org-cycle)][| /Control Parameters Of This File/ |]] :: dblk ctrls classifications=cs-u
#+end_org """
####+END:

####+BEGIN: b:prog:file/proclamations :outLevel 1
""" #+begin_org
* *[[elisp:(org-cycle)][| Proclamations |]]* :: Libre-Halaal Software --- Part Of BISOS ---  Poly-COMEEGA Format.
** This is Libre-Halaal Software. © Neda Communications, Inc. Subject to AGPL.
** It is part of BISOS (ByStar Internet Services OS)
#+end_org """
####+END:

if 'csInfo' not in globals(): import typing ; csInfo: typing.Dict[str, typing.Any] = { 'moduleName': ['loadAs'], }
csInfo['version'] = '202608100001'
csInfo['status']  = 'inDev'

import typing
import enum
import pathlib
import re
from dataclasses import dataclass, field

from bisos.csSeed import seedsLib


###############################################################################
# Enums
###############################################################################

@enum.unique
class Engine(enum.Enum):
    Docker = "docker"
    Podman = "podman"


@enum.unique
class Profile(enum.Enum):
    Confined = "confined"
    Privileged = "privileged"
    RootlessSysd = "rootless-sysd"


@enum.unique
class CgroupVer(enum.Enum):
    V1 = "v1"
    V2 = "v2"


@enum.unique
class DesktopType(enum.Enum):
    VncXfce = "vnc/xfce"


###############################################################################
# Port assignments --- FALLBACK only. The leaf's own file is the source of truth:
# docker-compose.yml (docker) or the Quadlet *.container (podman), read by
# _leafFileFacts() below, exactly as the standalone containerManage.sh reads them.
# This table is used only when a leaf has no such file (e.g. a unit test path).
# Ports are host-side; container-side are always 22/5901/6901
###############################################################################

_PORT_TABLE: dict[tuple[str, Profile], dict[str, int]] = {
    ("12", Profile.Confined):      {"ssh": 2222, "vnc": 5901, "novnc": 6901},
    ("12", Profile.Privileged):    {"ssh": 2223, "vnc": 5902, "novnc": 6902},
    ("12", Profile.RootlessSysd):  {"ssh": 2225, "vnc": 5904, "novnc": 6904},
    ("13", Profile.Confined):      {"ssh": 2228, "vnc": 5907, "novnc": 6907},
    ("13", Profile.Privileged):    {"ssh": 2224, "vnc": 5903, "novnc": 6903},
    ("13", Profile.RootlessSysd):  {"ssh": 2226, "vnc": 5905, "novnc": 6905},
}

# Secondary instances (e.g. bisos_deb13-sysd-2: 2227 5906 6906) are not in this table;
# their ports come from their compose file.


_BASE_IMAGE_TABLE: dict[tuple[str, Profile], str] = {
    ("12", Profile.Confined):     "bisos_deb12-fresh:latest",
    ("12", Profile.Privileged):   "bisos_deb12-fresh:latest",
    ("12", Profile.RootlessSysd): "bisos_deb12-fresh:latest",
    ("13", Profile.Confined):     "bisos_deb13-fresh:latest",
    ("13", Profile.Privileged):   "bisos_deb13-fresh:latest",
    ("13", Profile.RootlessSysd): "bisos_deb13-fresh:latest",
}


###############################################################################
# ContainerParams — the full parameter set derived from the planted path
###############################################################################

@dataclass
class ContainerParams:
    distro: str = "debian"
    release: str = ""          # "12" or "13"
    profile: Profile | None = None
    desktopType: DesktopType = DesktopType.VncXfce
    imageName: str = ""        # e.g. "bisos_deb13-sysd" (a secondary leaf: its primary's)
    leafName: str = ""         # the leaf directory, e.g. "bisos_deb13-sysd-2"
    containerName: str = ""    # from the compose / Quadlet file; default the leaf name
    primaryLeaf: str = ""      # for a secondary leaf <primary>-<N>: "<primary>"; else ""

    # Derived
    engine: Engine | None = None
    sshPort: int = 0
    vncPort: int = 0
    novncPort: int = 0
    baseImage: str = ""
    cgroupVariants: list[CgroupVer] = field(default_factory=list)

    # The raw plant path (for diagnostics)
    plantPath: str = ""

    @property
    def isSecondary(self) -> bool:
        """A leaf named <primary>-<N> runs <primary>'s image and builds none of its own."""
        return bool(self.primaryLeaf)


###############################################################################
# _leafFileFacts --- container name and host ports from the leaf's own file.
# Same rules as bro_dockerfiles' containerManage.sh (simple line matching, no
# YAML library: PyYAML is not a declared dependency of this package).
###############################################################################

_CONTAINER_PORT_KEYS = {"22": "ssh", "5901": "vnc", "6901": "novnc"}


def _leafFileFacts(leafDir: pathlib.Path, engine: "Engine") -> dict[str, typing.Any]:
    """{'containerName': str|None, 'image': str|None, 'ports': {'ssh': N, ...}, 'source': path|None}.

    docker: docker-compose.yml --- container_name:, image:, port lines "- \"2224:22\"".
    podman: the one *.container (Quadlet) --- ContainerName=, PublishPort=2226:22.
    """
    facts: dict[str, typing.Any] = {'containerName': None, 'image': None, 'ports': {}, 'source': None}
    if engine == Engine.Docker:
        source = leafDir / "docker-compose.yml"
        if not source.is_file():
            return facts
        text = source.read_text()
        m = re.search(r'^\s*container_name:\s*"?([^"\s#]+)', text, re.M)
        facts['containerName'] = m.group(1) if m else None
        m = re.search(r'^\s*image:\s*"?([^"\s#]+)', text, re.M)
        facts['image'] = m.group(1) if m else None
        pairs = re.findall(r'^\s*-\s*"?(\d+):(\d+)', text, re.M)
    else:
        quadlets = sorted(leafDir.glob("*.container"))
        if len(quadlets) != 1:
            return facts
        source = quadlets[0]
        text = source.read_text()
        m = re.search(r'^ContainerName=\s*(\S+)', text, re.M)
        facts['containerName'] = m.group(1) if m else None
        pairs = re.findall(r'^PublishPort=\s*(\d+):(\d+)', text, re.M)
    facts['source'] = source
    for hostPort, containerPort in pairs:
        key = _CONTAINER_PORT_KEYS.get(containerPort)
        if key is not None:
            facts['ports'][key] = int(hostPort)
    return facts


###############################################################################
# paramsFromPlantPath — pure function, no side effects
###############################################################################

def paramsFromPlantPath(plantPath: str | None = None) -> ContainerParams:
    """Derive ContainerParams by anchoring on the 'debian' segment in plantPath.

    Expected structure: …/debian/<release>/<profile>/vnc/xfce/<imageName>/…

    Raises ValueError on unexpected path structure so mis-planted files fail loudly.
    """
    if plantPath is None:
        plantPath = seedsLib.seededCsxuInfo.plantOfThisSeed

    if plantPath is None:
        raise ValueError("plantPath is None and plantOfThisSeed is not set")

    # Resolve to absolute path — plantOfThisSeed may arrive as "./dockerProc.spcs"
    # when invoked from its leaf directory. Anchor on segments of the directory
    # containing the planted file, not the file itself. Also normalise
    # plantPath itself to the resolved absolute form so downstream consumers
    # can do Path(p.plantPath).parent / .parents[N] without hitting IndexError
    # from a bare "." relative path.
    resolvedFile = pathlib.Path(plantPath).resolve()
    if resolvedFile.is_file():
        resolvedDir = resolvedFile.parent
    else:
        resolvedDir = resolvedFile
    plantPath = str(resolvedFile)
    parts = resolvedDir.parts

    try:
        anchor = parts.index("debian")
    except ValueError:
        raise ValueError(f"Expected 'debian' segment in plant path: {plantPath}")

    try:
        release = parts[anchor + 1]          # "12" or "13"
        profileStr = parts[anchor + 2]       # "confined" / "privileged" / "rootless-sysd"
        desktopPart1 = parts[anchor + 3]     # "vnc"
        desktopPart2 = parts[anchor + 4]     # "xfce"
        leafName = parts[anchor + 5]         # "bisos_deb13-sysd" or "bisos_deb13-sysd-2"
    except IndexError as exc:
        raise ValueError(
            f"Plant path too short after 'debian' segment: {plantPath}"
        ) from exc

    # Validate desktop
    desktopStr = f"{desktopPart1}/{desktopPart2}"
    if desktopStr != "vnc/xfce":
        raise ValueError(
            f"Unexpected desktop segments '{desktopStr}' in path: {plantPath}"
        )

    # Map profile string to enum
    profileMap = {
        "confined":      Profile.Confined,
        "privileged":    Profile.Privileged,
        "rootless-sysd": Profile.RootlessSysd,
    }
    if profileStr not in profileMap:
        raise ValueError(
            f"Unknown profile '{profileStr}' in path: {plantPath}. "
            f"Expected one of {list(profileMap.keys())}"
        )
    profile = profileMap[profileStr]

    # Derive engine from profile
    engineMap = {
        Profile.Confined:     Engine.Docker,
        Profile.Privileged:   Engine.Docker,
        Profile.RootlessSysd: Engine.Podman,
    }
    engine = engineMap[profile]

    # A numeric suffix means a secondary instance: <primary>-<N> runs <primary>'s image.
    m = re.fullmatch(r'(.+)-(\d+)', leafName)
    primaryLeaf = m.group(1) if m else ""
    imageName = primaryLeaf or leafName

    # Container name and host ports: the leaf's own compose / Quadlet file first.
    portKey = (release, profile)
    facts = _leafFileFacts(resolvedDir, engine)
    if facts['source'] is not None and len(facts['ports']) == 3:
        ports = facts['ports']
    elif portKey in _PORT_TABLE and not primaryLeaf:
        ports = _PORT_TABLE[portKey]
    else:
        raise ValueError(
            f"No host ports for {leafName}: its docker-compose.yml / *.container does not "
            f"publish 22, 5901 and 6901, and it has no fallback entry: {plantPath}"
        )
    containerName = facts['containerName'] or leafName

    # Base image
    baseImage = _BASE_IMAGE_TABLE.get(portKey, "")

    # cgroup variants supported by bisos.dockerProc: v2 only, for every profile.
    # cgroup v1 is obsolete here (the containerProc_* commands refuse a v1 host);
    # the leaves' standalone scripts still run privileged leaves on v1 through
    # docker-compose.cgv1.yml.
    cgroupVariants: list[CgroupVer] = [CgroupVer.V2]

    return ContainerParams(
        distro="debian",
        release=release,
        profile=profile,
        desktopType=DesktopType.VncXfce,
        imageName=imageName,
        leafName=leafName,
        containerName=containerName,
        primaryLeaf=primaryLeaf,
        engine=engine,
        sshPort=ports["ssh"],
        vncPort=ports["vnc"],
        novncPort=ports["novnc"],
        baseImage=baseImage,
        cgroupVariants=cgroupVariants,
        plantPath=plantPath,
    )


###############################################################################
# Gate and status log: provided by bisos.fileObj (ftoLeaf_seedInfo), with the
# generic lifecycle verbs. The files are <leaf>/dockerProc.control / .status
# (podmanProc.* in rootless-sysd leaves), git-ignored in bro_dockerfiles.
###############################################################################

###############################################################################
# ContainerProcSeedInfo — seed-level setup (examplesFuncsList plumbing)
###############################################################################

@dataclass
class ContainerProcSeedInfo:
    seedType: str | None = None
    examplesFuncsList: list[typing.Callable] | None = None

    def __post_init__(self):
        if self.seedType is None:
            self.seedType = self.__class__.__name__

    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance


containerProcSeedInfo = ContainerProcSeedInfo()


def setup(
        examplesFuncsList: list[typing.Callable] | None = None,
) -> None:
    if examplesFuncsList is not None:
        containerProcSeedInfo.examplesFuncsList = examplesFuncsList


###############################################################################
# leafProcessorNames --- filenames whose presence in a directory indicates
# that the directory is a *leaf* in a walkable FTO tree.
#
# The branch's .spcs passes this list to
# ftoBranch_seedInfo.setup(leafProcessors=...) so the walker can detect
# leaves definitionally (by presence of the leaf's own planted .spcs)
# instead of requiring a per-leaf =_tree_=leaf= marker file.
###############################################################################

def leafProcessorNames() -> list[str]:
    """Filenames that identify a containerProc leaf directory.

    A directory is a leaf if it contains any of these files. The =_treeProc_=
    for that leaf is the matched filename itself.
    """
    return ['dockerProc.spcs', 'podmanProc.spcs']


###############################################################################
# walkExamples --- the list of containerProc verbs that make sense to run
# across a branch of leaves via fto_forwardToLeaves.
#
# This is the "source of truth" for what a branch .spcs (e.g. one planted
# at bro_dockerfiles/debian/12/confined/) should expose in its walk-examples
# menu chapter. The branch .spcs imports this function and passes the result
# to bisos.fileObj.ftoBranch_seedInfo.setup(leafExamples=...).
#
# Adding a new containerProc_* Cmnd? Add it here once; every branch under
# bro_dockerfiles automatically picks it up on the next examples-menu render.
###############################################################################

def walkExamples() -> list:
    """Return the list of WalkExampleSpec entries for containerProc leaves.

    Import type lazily to avoid a hard dependency on =bisos.fileObj= at
    module-load time (the seedInfo is used in contexts without fileObj too).
    """
    from bisos.fileObj.ftoBranch_seedInfo import WalkExampleSpec
    from bisos.fileObj import ftoLeaf_seedInfo

    # Ordered by lifecycle stage. Tags allow future filtering
    # (e.g. read-only vs destructive).
    # The generic lifecycle verbs and gate commands (bisos.fileObj) first; at a branch
    # the same names also work directly: ./ftoBranchProc.spcs -i fto_prepare.
    return ftoLeaf_seedInfo.lifecycleWalkExamples() + [
        # -- Staleness (read-only; what fto_reMaterialize would re-create) ----
        WalkExampleSpec(
            cmndName='containerProc_instanceIsStale',
            comment="# which instances run an older image than their tag",
            tags=frozenset({'read-only'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_imageIsStale',
            comment="# which images are older than their base",
            tags=frozenset({'read-only'}),
        ),
        # -- Read-only (safe to walk everywhere) ------------------------------
        WalkExampleSpec(
            cmndName='containerProc_instancePs',
            comment="# engine ps -a filtered to each leaf's container",
            tags=frozenset({'read-only'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_instanceStatus',
            comment="# engine inspect + SSH systemd summary",
            tags=frozenset({'read-only'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_instanceLogs',
            comment="# engine logs at each leaf",
            tags=frozenset({'read-only'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_instanceVerify',
            comment="# port + noVNC + SSH-based service checks at each leaf",
            tags=frozenset({'read-only'}),
        ),
        # -- Image lifecycle --------------------------------------------------
        WalkExampleSpec(
            cmndName='containerProc_imageBuild',
            comment="# build every leaf's image (long-running)",
            tags=frozenset({'destructive', 'build'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_imageBuild',
            pars={'noCache': 'true'},
            comment="# --no-cache build",
            tags=frozenset({'destructive', 'build'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_imageDelete',
            comment="# rmi every leaf's image (leaves instances alone)",
            tags=frozenset({'destructive'}),
        ),
        # -- Instance lifecycle -----------------------------------------------
        WalkExampleSpec(
            cmndName='containerProc_instanceUp',
            comment="# up (docker compose up / podman run --systemd=always)",
            tags=frozenset({'destructive'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_instanceDown',
            comment="# down / stop",
            tags=frozenset({'destructive'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_instanceRestart',
            comment="# stop + start",
            tags=frozenset({'destructive'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_instanceDelete',
            comment="# stop + rm (keeps image)",
            tags=frozenset({'destructive'}),
        ),
        # -- Snapshot / backup (Scenarios A + B from the backup panel) --------
        WalkExampleSpec(
            cmndName='containerProc_instanceCommit',
            comment="# snapshot the running container -> new image tag",
            tags=frozenset({'destructive', 'backup'}),
        ),
        WalkExampleSpec(
            cmndName='containerProc_imageSave',
            comment="# save image -> /bisos/var/dockerProc/backups/<user>/<img>/",
            tags=frozenset({'backup'}),
        ),
        # -- Combined cleanup -------------------------------------------------
        WalkExampleSpec(
            cmndName='containerProc_fullClean',
            comment="# instanceDelete + imageDelete",
            tags=frozenset({'destructive'}),
        ),
        # -- Install (one-shot inside container) ------------------------------
        WalkExampleSpec(
            cmndName='containerProc_exec_installRawBisos',
            comment="# cd ~/raw-bisos && bash installRawBisos.sh",
            tags=frozenset({'destructive', 'install'}),
        ),
    ]


###############################################################################
# End
###############################################################################

### local variables:
### no-byte-compile: t
### end:
