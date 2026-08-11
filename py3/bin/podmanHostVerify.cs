#!/bin/env python
# -*- coding: utf-8 -*-

""" #+begin_org
* ~[Summary]~ :: Check that this host can run rootless-sysd containers.
  HOST-scoped readiness check: rootless Podman + crun + cgroup v2 with
  controller delegation + working user systemd/D-Bus session + store on a
  local disk with free space. Inspects the host only; builds/runs nothing.
#+end_org """

####+BEGIN: b:py3:cs:file/dblockControls :classification "cs-mu"
""" #+begin_org
* [[elisp:(org-cycle)][| /Control Parameters Of This File/ |]] :: dblk ctrls classifications=cs-mu
#+BEGIN_SRC emacs-lisp
(setq-local b:dblockControls t) ; (setq-local b:dblockControls nil)
(put 'b:dblockControls 'py3:cs:Classification "cs-mu") ; one of cs-mu, cs-u, cs-lib, bpf-lib, pyLibPure
#+END_SRC
#+RESULTS:
: cs-mu
#+end_org """
####+END:

####+BEGIN: b:prog:file/proclamations :outLevel 1
""" #+begin_org
* *[[elisp:(org-cycle)][| Proclamations |]]* :: Libre-Halaal Software --- Part Of BISOS ---  Poly-COMEEGA Format.
** This is Libre-Halaal Software. © Neda Communications, Inc. Subject to AGPL.
** It is part of BISOS (ByStar Internet Services OS)
** Best read and edited  with Blee in Poly-COMEEGA (Polymode Colaborative Org-Mode Enhance Emacs Generalized Authorship)
#+end_org """
####+END:

####+BEGIN: b:prog:file/particulars :authors ("./inserts/authors-mb.org")
""" #+begin_org
* *[[elisp:(org-cycle)][| Particulars |]]* :: This File, Authors, version
** This File: /bxRepos/bisos-pip/dockerProc/py3/bin/podmanHostVerify.cs
** File True Name: /bisos/git/auth/bxRepos/bisos-pip/dockerProc/py3/bin/podmanHostVerify.cs
** Authors: Mohsen BANAN, http://mohsen.banan.1.byname.net/contact
#+end_org """
####+END:

####+BEGIN: b:py3:file/particulars-csInfo :status "inDev"
""" #+begin_org
* *[[elisp:(org-cycle)][| Particulars-csInfo |]]*
#+end_org """
import typing
csInfo: typing.Dict[str, typing.Any] = { 'moduleName': ['podmanHostVerify'], }
csInfo['version'] = '202608110001'
csInfo['status']  = 'inDev'
csInfo['panel'] = 'podmanHostVerify-Panel.org'
csInfo['groupingType'] = 'IcmGroupingType-pkged'
csInfo['cmndParts'] = 'IcmCmndParts[common] IcmCmndParts[param]'
####+END:

""" #+begin_org
* [[elisp:(org-cycle)][| ~Description~ |]] :: [[file:/bisos/git/auth/bxRepos/blee-binders/bisos-core/COMEEGA/_nodeBase_/fullUsagePanel-en.org][BISOS COMEEGA Panel]]
podmanHostVerify.cs: Standalone host readiness check for rootless-sysd containers.
Checks: non-root uid, podman installed, cgroup v2 (cgroup2fs), crun OCI runtime,
subuid/subgid ranges, XDG_RUNTIME_DIR + user systemd session, linger,
cgroup v2 controller delegation, graphroot on local disk with free space.
** Status: inDev
#+end_org """

####+BEGIN: b:prog:file/orgTopControls :outLevel 1
""" #+begin_org
* [[elisp:(org-cycle)][| Controls |]] :: [[elisp:(delete-other-windows)][(1)]] | [[elisp:(show-all)][Show-All]]  [[elisp:(org-shifttab)][Overview]]  [[elisp:(progn (org-shifttab) (org-content))][Content]] | [[file:Panel.org][Panel]] | [[elisp:(blee:ppmm:org-mode-toggle)][Nat]] | [[elisp:(bx:org:run-me)][Run]] | [[elisp:(bx:org:run-me-eml)][RunEml]] | [[elisp:(progn (save-buffer) (kill-buffer))][S&Q]]  [[elisp:(save-buffer)][Save]]  [[elisp:(kill-buffer)][Quit]] [[elisp:(org-cycle)][| ]]
** /Version Control/ ::  [[elisp:(call-interactively (quote cvs-update))][cvs-update]]  [[elisp:(vc-update)][vc-update]] | [[elisp:(bx:org:agenda:this-file-otherWin)][Agenda-List]]  [[elisp:(bx:org:todo:this-file-otherWin)][ToDo-List]]

#+end_org """
####+END:

####+BEGIN: b:py3:file/workbench :outLevel 1
""" #+begin_org
* [[elisp:(org-cycle)][| Workbench |]] :: [[elisp:(python-check (format "/bisos/venv/py3/bisos3/bin/python -m pyclbr %s" (bx:buf-fname))))][pyclbr]] || [[elisp:(python-check (format "/bisos/venv/py3/bisos3/bin/python -m pydoc ./%s" (bx:buf-fname))))][pydoc]] || [[elisp:(python-check (format "/bisos/pipx/bin/pyflakes %s" (bx:buf-fname)))][pyflakes]] | [[elisp:(python-check (format "/bisos/pipx/bin/pychecker %s" (bx:buf-fname))))][pychecker (executes)]] | [[elisp:(python-check (format "/bisos/pipx/bin/pycodestyle %s" (bx:buf-fname))))][pycodestyle]] | [[elisp:(python-check (format "/bisos/pipx/bin/flake8 %s" (bx:buf-fname))))][flake8]] | [[elisp:(python-check (format "/bisos/pipx/bin/pylint %s" (bx:buf-fname))))][pylint]]  [[elisp:(org-cycle)][| ]]
#+end_org """
####+END:

####+BEGIN: b:py3:cs:framework/imports :basedOn "classification"
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CsFrmWrk   [[elisp:(outline-show-subtree+toggle)][||]] *Imports* =Based on Classification=cs-mu=
#+end_org """
from bisos import b
from bisos.b import cs
from bisos.b import b_io

import collections
import typing
####+END:

""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CsFrmWrk   [[elisp:(outline-show-subtree+toggle)][||]] ~csuList emacs-list Specifications~  [[elisp:(blee:org:code-block/above-run)][ /Eval Below/ ]] [[elisp:(org-cycle)][| ]]
#+BEGIN_SRC emacs-lisp
(setq  b:py:cs:csuList
  (list
 ))
#+END_SRC
#+RESULTS:
|  |
#+end_org """

####+BEGIN: b:py3:cs:framework/csuListProc :pyImports t :csuImports t :csuParams t :csmuParams nil
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CsFrmWrk   [[elisp:(outline-show-subtree+toggle)][||]] ~Process CSU List~ with /0/ in csuList pyImports=t csuImports=t csuParams=t
#+end_org """

csuList = []

g_importedCmndsModules = cs.csuList_importedModules(csuList)

def g_extraParams():
    csParams = cs.param.CmndParamDict()
    cs.csuList_commonParamsSpecify(csuList, csParams)
    cs.argsparseBasedOnCsParams(csParams)

####+END:

cs.invOutcomeReportControl(cmnd=True, ro=True)

####+BEGIN: blee:bxPanel:foldingSection :outLevel 0 :sep nil :title "CmndSvcs" :anchor ""  :extraInfo "Command Services Section"
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*     [[elisp:(outline-show-subtree+toggle)][| _CmndSvcs_: |]]  Command Services Section  [[elisp:(org-shifttab)][<)]] E|
#+end_org """
####+END:

####+BEGIN: b:py3:cs:cmnd/classHead :cmndName "verify" :extent "verify" :comment "Check host readiness for rootless-sysd containers" :parsMand "" :parsOpt "" :argsMin 0 :argsMax 0 :pyInv ""
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CmndSvc-   [[elisp:(outline-show-subtree+toggle)][||]] <<verify>>  *Check host readiness for rootless-sysd containers*  =verify= ro=cli   [[elisp:(org-cycle)][| ]]
#+end_org """
class verify(cs.Cmnd):
    cmndParamsMandatory = [ ]
    cmndParamsOptional = [ ]
    cmndArgsLen = {'Min': 0, 'Max': 0,}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(self,
             rtInv: cs.RtInvoker,
             cmndOutcome: b.op.Outcome,
    ) -> b.op.Outcome:
        """Check host readiness for rootless-sysd containers"""
        failed = b_io.eh.badOutcome
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, None).isProblematic():
            return failed(cmndOutcome)
####+END:

        self.cmndDocStr(f""" #+begin_org
** [[elisp:(org-cycle)][| *CmndDesc:* | ]]  Run all host readiness checks for rootless-sysd Podman containers.
        #+end_org """)

        b.subProc.WOpW(invedBy=None, log=1).bash(_VERIFY_SCRIPT)

        return cmndOutcome.set(
            opError=b.op.OpError.Success,
            opResults=None,
        )


_VERIFY_SCRIPT = r"""
set -u

PASS=0
FAIL=0
WARN=0

green() { printf '\033[32m%s\033[0m' "$1"; }
red()   { printf '\033[31m%s\033[0m' "$1"; }
yellow(){ printf '\033[33m%s\033[0m' "$1"; }

ok()   { printf '  [%s] %s\n' "$(green PASS)" "$1"; PASS=$((PASS+1)); }
bad()  { printf '  [%s] %s\n' "$(red FAIL)" "$1";  FAIL=$((FAIL+1)); }
warn() { printf '  [%s] %s\n' "$(yellow WARN)" "$1"; WARN=$((WARN+1)); }

echo "== Host readiness for rootless-sysd containers =="

# 1. Not running as root.
if [ "$(id -u)" -eq 0 ]; then
  warn "running as root (uid 0); rootless-sysd is meant to run as a normal user"
else
  ok "running as non-root user ($(id -un), uid $(id -u))"
fi

# 2. Podman installed.
if command -v podman >/dev/null 2>&1; then
  ok "podman installed ($(podman --version 2>/dev/null))"
  HAVE_PODMAN=1
else
  bad "podman NOT installed --- install: podman crun uidmap fuse-overlayfs dbus-user-session slirp4netns passt"
  HAVE_PODMAN=0
fi

# 3. cgroup v2 (unified hierarchy).
CG=$(stat -fc %T /sys/fs/cgroup 2>/dev/null)
if [ "$CG" = "cgroup2fs" ]; then
  ok "cgroup v2 (cgroup2fs) --- rootless delegation is possible"
else
  bad "cgroup is '$CG' (need cgroup2fs). This host is on cgroup v1/hybrid; rootless-sysd cannot work here."
fi

# 4. OCI runtime is crun.
if [ "${HAVE_PODMAN:-0}" -eq 1 ]; then
  OCI=$(podman info --format '{{.Host.OCIRuntime.Name}}' 2>/dev/null)
  if [ "$OCI" = "crun" ]; then
    ok "OCI runtime is crun"
  else
    warn "OCI runtime is '${OCI:-unknown}' (crun recommended for rootless systemd)"
  fi
fi

# 5. subuid / subgid ranges.
if grep -q "^$(id -un):" /etc/subuid 2>/dev/null && grep -q "^$(id -un):" /etc/subgid 2>/dev/null; then
  ok "subuid/subgid ranges present for $(id -un)"
else
  bad "no subuid/subgid range for $(id -un) --- run: sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 $(id -un)"
fi

# 6. Working user session (XDG_RUNTIME_DIR + user systemd/D-Bus).
CGMGR=""
if [ "${HAVE_PODMAN:-0}" -eq 1 ]; then
  CGMGR=$(podman info --format '{{.Host.CgroupManager}}' 2>/dev/null)
fi

if [ -n "${XDG_RUNTIME_DIR:-}" ] && [ -d "${XDG_RUNTIME_DIR:-/nonexistent}" ]; then
  ok "XDG_RUNTIME_DIR set ($XDG_RUNTIME_DIR)"
elif [ "$CGMGR" = "systemd" ]; then
  bad "XDG_RUNTIME_DIR unset/missing --- no user session. With the systemd cgroup manager, podman build/run fail (sd-bus I/O error). Log in as this user directly (not su)."
else
  warn "XDG_RUNTIME_DIR unset/missing (cgroup manager '${CGMGR:-?}' may tolerate it)"
fi

if systemctl --user show-environment >/dev/null 2>&1; then
  ok "user systemd/D-Bus session reachable (systemctl --user works)"
elif [ "$CGMGR" = "systemd" ]; then
  bad "no user systemd/D-Bus session --- systemd cgroup manager will fail. Fix: log in directly (not su) + 'loginctl enable-linger $(id -un)'; or build with 'podman --cgroup-manager=cgroupfs ...'"
else
  warn "no user systemd/D-Bus session (cgroup manager '${CGMGR:-?}')"
fi

LINGER=$(loginctl show-user "$(id -un)" 2>/dev/null | sed -n 's/^Linger=//p')
if [ "$LINGER" = "yes" ]; then
  ok "linger enabled (user services persist without an active login)"
else
  warn "linger not enabled --- needed for the Quadlet per-engineer model (loginctl enable-linger $(id -un))"
fi

# 7. cgroup v2 controller delegation.
DELEG_FILE="/sys/fs/cgroup/user.slice/user-$(id -u).slice/user@$(id -u).service/cgroup.controllers"
if [ -r "$DELEG_FILE" ]; then
  CONTROLLERS=$(cat "$DELEG_FILE" 2>/dev/null)
  MISSING=""
  for c in cpu io memory pids; do
    case " $CONTROLLERS " in *" $c "*) : ;; *) MISSING="$MISSING $c" ;; esac
  done
  if [ -z "$MISSING" ]; then
    ok "controller delegation OK (cpu io memory pids)"
  else
    warn "delegated controllers = '$CONTROLLERS'; missing:$MISSING --- add a Delegate= drop-in on user@.service"
  fi
else
  warn "cannot read $DELEG_FILE (no delegated user cgroup?) --- systemd resource control inside may be limited"
fi

# 8. Podman store (graphroot): must be on a local disk with room to spare.
if [ "${HAVE_PODMAN:-0}" -eq 1 ]; then
  GRAPHROOT=$(podman info --format '{{.Store.GraphRoot}}' 2>/dev/null)
  if [ -n "$GRAPHROOT" ]; then
    FSTYPE=$(stat -f -c %T "$GRAPHROOT" 2>/dev/null)
    USEPCT=$(df -P "$GRAPHROOT" 2>/dev/null | awk 'NR==2{gsub("%","",$5); print $5}')
    AVAILK=$(df -Pk "$GRAPHROOT" 2>/dev/null | awk 'NR==2{print $4}')
    AVAILG=$(( ${AVAILK:-0} / 1024 / 1024 ))

    case "$FSTYPE" in
      nfs|nfs4)
        bad "graphroot on NFS ($GRAPHROOT, fstype=$FSTYPE) --- overlay driver is unreliable on NFS; move it to a local disk (storage.conf graphroot=)" ;;
      "")
        warn "could not determine graphroot fstype ($GRAPHROOT)" ;;
      *)
        ok "graphroot on local fs ($FSTYPE): $GRAPHROOT" ;;
    esac

    if [ -n "$USEPCT" ]; then
      if [ "$USEPCT" -ge 95 ] || [ "${AVAILG:-0}" -lt 3 ]; then
        bad "graphroot filesystem ${USEPCT}% full (~${AVAILG}G free) --- image builds will fail with 'no space left on device'"
      elif [ "$USEPCT" -ge 90 ]; then
        warn "graphroot filesystem ${USEPCT}% full (~${AVAILG}G free) --- low headroom for image builds"
      else
        ok "graphroot free space OK (${USEPCT}% used, ~${AVAILG}G free)"
      fi
    else
      warn "could not determine graphroot free space for $GRAPHROOT"
    fi
  else
    warn "could not determine graphroot (podman info)"
  fi
fi

echo "== $PASS passed, $WARN warnings, $FAIL failed =="
if [ "$FAIL" -eq 0 ]; then
  echo "GO: hard requirements met (review any WARNs above)."
else
  echo "NO-GO: $FAIL blocking requirement(s) unmet. rootless-sysd will not run here as-is."
fi
[ "$FAIL" -eq 0 ]
"""


def examples_csu() -> b.op.Outcome:
    """Common Usage Examples for this Command-Service Unit"""
    cmnd = cs.examples.cmndEnter
    cmndOutcome = b.op.Outcome()

    cs.examples.menuChapter('*podmanHostVerify Examples*')
    cmnd('verify', comment=" # Check this host for rootless-sysd readiness")

    cs.examples.menuChapter('*End-Of podmanHostVerify Examples*')
    return cmndOutcome


####+BEGIN: b:py3:cs:cmnd/classHead :cmndName "examples" :extent "verify" :ro "noCli" :comment "FrameWrk: CS-Main-Examples" :parsMand "" :parsOpt "" :argsMin 0 :argsMax 0 :pyInv ""
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CmndSvc-   [[elisp:(outline-show-subtree+toggle)][||]] <<examples>>  *FrameWrk: CS-Main-Examples*  =verify= ro=noCli   [[elisp:(org-cycle)][| ]]
#+end_org """
class examples(cs.Cmnd):
    cmndParamsMandatory = [ ]
    cmndParamsOptional = [ ]
    cmndArgsLen = {'Min': 0, 'Max': 0,}
    rtInvConstraints = cs.rtInvoker.RtInvoker.new_noRo()

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(self,
             rtInv: cs.RtInvoker,
             cmndOutcome: b.op.Outcome,
    ) -> b.op.Outcome:
        """FrameWrk: CS-Main-Examples"""
        failed = b_io.eh.badOutcome
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, None).isProblematic():
            return failed(cmndOutcome)
####+END:

        cs.examples.myName(cs.G.icmMyName(), cs.G.icmMyFullName())
        cs.examples.commonBrief()
        examples_csu()

        return cmndOutcome


####+BEGIN: b:py3:cs:framework/main :csMainEntry "podmanHostVerify" :noCmndEntry "examples"
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CsFrmWrk   [[elisp:(outline-show-subtree+toggle)][||]] *Main Entry* =csMainEntry=podmanHostVerify=
#+end_org """
if __name__ == '__main__':
    cs.main.g_csMain(
        csInfo=csInfo,
        noCmndEntry=examples,
        extraParamsHook=g_extraParams,
        ignoreUnknownParams=False,
        importedCmndsModules=g_importedCmndsModules,
    )
####+END:

####+BEGIN: b:py3:cs:framework/endOfFile
""" #+begin_org
* [[elisp:(org-cycle)][| End-Of-File |]]
#+end_org """
### local variables:
### no-byte-compile: t
### end:
####+END:
