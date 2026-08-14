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
# Port assignments — derived from release + profile
# Ports are host-side; container-side are always 22/5901/6901
###############################################################################

_PORT_TABLE: dict[tuple[str, Profile], dict[str, int]] = {
    ("12", Profile.Confined):      {"ssh": 2222, "vnc": 5901, "novnc": 6901},
    ("12", Profile.Privileged):    {"ssh": 2223, "vnc": 5902, "novnc": 6902},
    ("12", Profile.RootlessSysd):  {"ssh": 2225, "vnc": 5904, "novnc": 6904},
    ("13", Profile.Confined):      {"ssh": 2222, "vnc": 5901, "novnc": 6901},
    ("13", Profile.Privileged):    {"ssh": 2224, "vnc": 5903, "novnc": 6903},
    ("13", Profile.RootlessSysd):  {"ssh": 2226, "vnc": 5905, "novnc": 6905},
}

_BASE_IMAGE_TABLE: dict[tuple[str, Profile], str] = {
    ("12", Profile.Confined):     "bisos/deb12-fresh-vnc-xfce:1.21",
    ("12", Profile.Privileged):   "bisos/deb12-fresh-vnc-xfce:1.21",
    ("12", Profile.RootlessSysd): "bisos/deb12-fresh-vnc-xfce:1.21",
    ("13", Profile.Confined):     "bisos/deb13-fresh-vnc-xfce:4",
    ("13", Profile.Privileged):   "bisos/deb13-fresh-vnc-xfce:4",
    ("13", Profile.RootlessSysd): "bisos/deb13-fresh-vnc-xfce:4",
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
    imageName: str = ""        # e.g. "bisos_deb13-sysd"

    # Derived
    engine: Engine | None = None
    sshPort: int = 0
    vncPort: int = 0
    novncPort: int = 0
    baseImage: str = ""
    cgroupVariants: list[CgroupVer] = field(default_factory=list)

    # The raw plant path (for diagnostics)
    plantPath: str = ""


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
        imageName = parts[anchor + 5]        # "bisos_deb13-sysd"
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

    # Ports
    portKey = (release, profile)
    if portKey not in _PORT_TABLE:
        raise ValueError(
            f"No port mapping for release={release}, profile={profile}: {plantPath}"
        )
    ports = _PORT_TABLE[portKey]

    # Base image
    baseImage = _BASE_IMAGE_TABLE.get(portKey, "")

    # cgroup variants supported
    cgroupVariants: list[CgroupVer] = []
    if profile == Profile.Confined:
        cgroupVariants = [CgroupVer.V1, CgroupVer.V2]
    elif profile == Profile.Privileged:
        cgroupVariants = [CgroupVer.V1, CgroupVer.V2]
    elif profile == Profile.RootlessSysd:
        cgroupVariants = [CgroupVer.V2]   # v1 does not support rootless delegation

    return ContainerParams(
        distro="debian",
        release=release,
        profile=profile,
        desktopType=DesktopType.VncXfce,
        imageName=imageName,
        engine=engine,
        sshPort=ports["ssh"],
        vncPort=ports["vnc"],
        novncPort=ports["novnc"],
        baseImage=baseImage,
        cgroupVariants=cgroupVariants,
        plantPath=plantPath,
    )


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

    # Ordered by lifecycle stage. Tags allow future filtering
    # (e.g. read-only vs destructive).
    return [
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
    ]


###############################################################################
# End
###############################################################################

### local variables:
### no-byte-compile: t
### end:
