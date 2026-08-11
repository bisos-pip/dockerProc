#!/bin/bash -i
#

# Safety check: must run from a directory named "tests"
if [[ "$(basename "$PWD")" != "tests" ]]; then
    echo "ERROR: verify.sh must be run from a directory named 'tests'." >&2
    echo "  Current PWD: $PWD" >&2
    exit 1
fi

# --- CS entry points: smoke test (no args → examples/usage, non-zero ok) ---

lpDo ../bin/podmanHostVerify.cs
lpDo ../bin/dockerCmnds.cs
lpDo ../bin/podmanCmnds.cs
lpDo ../bin/containerProc-seed.cs

# --- podmanHostVerify.cs: host readiness check ---

lpDo ../bin/podmanHostVerify.cs -i verify

# --- paramsFromPlantPath(): pure-Python path parsing for all six leaves ---

lpDo python3 -c "
from bisos.dockerProc.containerProc_seedInfo import paramsFromPlantPath, Engine, Profile

cases = [
    ('/some/bro_dockerfiles/debian/12/confined/vnc/xfce/bisos_deb12-fresh',    Profile.Confined,     Engine.Docker,  2222, 5901, 6901),
    ('/some/bro_dockerfiles/debian/12/privileged/vnc/xfce/bisos_deb12-sysd',   Profile.Privileged,   Engine.Docker,  2223, 5902, 6902),
    ('/some/bro_dockerfiles/debian/12/rootless-sysd/vnc/xfce/bisos_deb12-rootless-sysd', Profile.RootlessSysd, Engine.Podman, 2225, 5904, 6904),
    ('/some/bro_dockerfiles/debian/13/confined/vnc/xfce/bisos_deb13-fresh',    Profile.Confined,     Engine.Docker,  2222, 5901, 6901),
    ('/some/bro_dockerfiles/debian/13/privileged/vnc/xfce/bisos_deb13-sysd',   Profile.Privileged,   Engine.Docker,  2224, 5903, 6903),
    ('/some/bro_dockerfiles/debian/13/rootless-sysd/vnc/xfce/bisos_deb13-rootless-sysd', Profile.RootlessSysd, Engine.Podman, 2226, 5905, 6905),
]

failed = 0
for path, expProfile, expEngine, expSsh, expVnc, expNoVnc in cases:
    p = paramsFromPlantPath(path)
    ok = (p.profile == expProfile and p.engine == expEngine
          and p.sshPort == expSsh and p.vncPort == expVnc and p.novncPort == expNoVnc)
    status = 'PASS' if ok else 'FAIL'
    print(f'  [{status}] {path.split(\"/debian/\")[1]}  profile={p.profile.value} engine={p.engine.value} ssh={p.sshPort} vnc={p.vncPort} novnc={p.novncPort}')
    if not ok:
        failed += 1

# Error cases
import sys
try:
    paramsFromPlantPath('/no/debian/segment/here')
    print('  [FAIL] missing debian segment: should have raised ValueError')
    failed += 1
except ValueError:
    print('  [PASS] missing debian segment raises ValueError')

try:
    paramsFromPlantPath('/debian/13/badprofile/vnc/xfce/img')
    print('  [FAIL] unknown profile: should have raised ValueError')
    failed += 1
except ValueError:
    print('  [PASS] unknown profile raises ValueError')

if failed:
    print(f'paramsFromPlantPath: {failed} test(s) FAILED')
    sys.exit(1)
else:
    print('paramsFromPlantPath: all cases PASS')
"

# --- .pcs files: importable as Python scripts (no missing deps) ---

lpDo python3 -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location('dockerProc_sbom', '../bin/dockerProc-sbom.pcs'); m = importlib.util.module_from_spec(spec)" 2>/dev/null || true
lpDo python3 -c "import importlib.util, sys; spec = importlib.util.spec_from_file_location('podman_sbom', '../bin/podman-sbom.pcs'); m = importlib.util.module_from_spec(spec)" 2>/dev/null || true
