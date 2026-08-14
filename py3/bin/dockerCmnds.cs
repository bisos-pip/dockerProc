#!/bin/env python
# -*- coding: utf-8 -*-

""" #+begin_org
* ~[Summary]~ :: A =CmndSvc= for running the equivalent of facter in py and remotely with rpyc.
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
** This File: /bxRepos/bisos-pip/dockerProc/py3/bin/dockerCmnds.cs
** File True Name: /bisos/git/auth/bxRepos/bisos-pip/dockerProc/py3/bin/dockerCmnds.cs
** Authors: Mohsen BANAN, http://mohsen.banan.1.byname.net/contact
#+end_org """
####+END:

####+BEGIN: b:py3:file/particulars-csInfo :status "inUse"
""" #+begin_org
* *[[elisp:(org-cycle)][| Particulars-csInfo |]]*
#+end_org """
import typing
csInfo: typing.Dict[str, typing.Any] = { 'moduleName': ['facter'], }
csInfo['version'] = '202502215707'
csInfo['status']  = 'inUse'
csInfo['panel'] = 'facter-Panel.org'
csInfo['groupingType'] = 'IcmGroupingType-pkged'
csInfo['cmndParts'] = 'IcmCmndParts[common] IcmCmndParts[param]'
####+END:

""" #+begin_org
* [[elisp:(org-cycle)][| ~Description~ |]] :: [[file:/bisos/git/auth/bxRepos/blee-binders/bisos-core/PyFwrk/bisos-pip/bisos.cs/_nodeBase_/fullUsagePanel-en.org][BISOS CmndSvcs Panel]]   [[elisp:(org-cycle)][| ]]

This a =CmndSvc= for running the equivalent of facter in py and remotely with rpyc.
With BISOS, it is used in CMDB remotely.

** Status: In use with BISOS
** /[[elisp:(org-cycle)][| Planned Improvements |]]/ :
*** TODO Convert all ICMs to CSs
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
from bisos.common import csParam

import collections
####+END:

""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CsFrmWrk   [[elisp:(outline-show-subtree+toggle)][||]] ~csuList emacs-list Specifications~  [[elisp:(blee:org:code-block/above-run)][ /Eval Below/ ]] [[elisp:(org-cycle)][| ]]
#+BEGIN_SRC emacs-lisp
(setq  b:py:cs:csuList
  (list
   "bisos.b.cs.ro"
   "bisos.csPlayer.bleep"
   "bisos.common.commonCsParams"
   "plantedCsu"
 ))
#+END_SRC
#+RESULTS:
| bisos.b.cs.ro | bisos.csPlayer.bleep | bisos.common.commonCsParams | plantedCsu |
#+end_org """

####+BEGIN: b:py3:cs:framework/csuListProc :pyImports t :csuImports t :csuParams t :csmuParams nil
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CsFrmWrk   [[elisp:(outline-show-subtree+toggle)][||]] ~Process CSU List~ with /4/ in csuList pyImports=t csuImports=t csuParams=t
#+end_org """

from bisos.b.cs import ro
from bisos.csPlayer import bleep
from bisos.common import commonCsParams
from bisos.dockerProc import containerProc_csu as dockerProc_csu

csuList = [ 'bisos.b.cs.ro', 'bisos.csPlayer.bleep', 'bisos.common.commonCsParams', 'plantedCsu', ]

if b.cs.G.plantOfThisSeed is None:
    csuList.remove('plantedCsu')

g_importedCmndsModules = cs.csuList_importedModules(csuList)

def g_extraParams():
    csParams = cs.param.CmndParamDict()
    cs.csuList_commonParamsSpecify(csuList, csParams)
    cs.argsparseBasedOnCsParams(csParams)

####+END:

####+BEGIN: b:py3:cs:main/exposedSymbols :classes ()
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CsFrmWrk   [[elisp:(outline-show-subtree+toggle)][||]] ~CS Controls and Exposed Symbols List Specification~ with /0/ in Classes List
#+end_org """
####+END:

cs.invOutcomeReportControl(cmnd=True, ro=True)

####+BEGIN: b:py3:cs:main/exposedSymbols :classes ()
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CsFrmWrk   [[elisp:(outline-show-subtree+toggle)][||]] ~Exposed Symbols List Specification~ with /0/ in Classes List
#+end_org """
####+END:

####+BEGIN: blee:bxPanel:foldingSection :outLevel 0 :sep nil :title "CmndSvcs" :anchor ""  :extraInfo "Command Services Section"
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*     [[elisp:(outline-show-subtree+toggle)][| _CmndSvcs_: |]]  Command Services Section  [[elisp:(org-shifttab)][<)]] E|
#+end_org """
####+END:

####+BEGIN: b:py3:cs:cmnd/classHead :cmndName "examples" :extent "verify" :ro "noCli" :comment "FrameWrk: CS-Main-Examples" :parsMand "" :parsOpt "" :argsMin 0 :argsMax 0 :pyInv ""
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CmndSvc-   [[elisp:(outline-show-subtree+toggle)][||]] <<examples>>  *FrameWrk: CS-Main-Examples*  =verify= ro=noCli   [[elisp:(org-cycle)][| ]]
#+end_org """
class examples(cs.Cmnd):
    cmndParamsMandatory = [ ]
    cmndParamsOptional = [ ]
    cmndArgsLen = {'Min': 0, 'Max': 0,}
    rtInvConstraints = cs.rtInvoker.RtInvoker.new_noRo() # NO RO From CLI

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
        self.cmndDocStr(f""" #+begin_org
***** [[elisp:(org-cycle)][| *CmndDesc:* | ]]  Conventional top level example.
        #+end_org """)

        cs.examples.myName(cs.G.icmMyName(), cs.G.icmMyFullName())
        cs.examples.commonBrief()

        csXuName = cs.G.icmMyName()
        if "dockerCmnds" in csXuName:
            dockerDirectCmnds().pyCmnd()
        elif "podmanCmnds" in csXuName:
            dockerProc_csu.podmanDirectCmnds().pyCmnd()
        else:
            return failed(cmndOutcome)

        return(cmndOutcome)


####+BEGIN: b:py3:cs:cmnd/classHead :cmndName "dockerDirectCmnds" :comment "" :parsMand "" :parsOpt "perfName" :argsMin 0 :argsMax 0 :pyInv ""
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CmndSvc-   [[elisp:(outline-show-subtree+toggle)][||]] <<dockerDirectCmnds>>  =verify= parsOpt=perfName ro=cli   [[elisp:(org-cycle)][| ]]
#+end_org """
class dockerDirectCmnds(cs.Cmnd):
    cmndParamsMandatory = [ ]
    cmndParamsOptional = [ 'perfName', ]
    cmndArgsLen = {'Min': 0, 'Max': 0,}

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(self,
             rtInv: cs.RtInvoker,
             cmndOutcome: b.op.Outcome,
             perfName: typing.Optional[str]=None,  # Cs Optional Param
    ) -> b.op.Outcome:

        failed = b_io.eh.badOutcome
        callParamsDict = {'perfName': perfName, }
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, None).isProblematic():
            return failed(cmndOutcome)
        perfName = csParam.mappedValue('perfName', perfName)
####+END:
        self.cmndDocStr(f""" #+begin_org
** [[elisp:(org-cycle)][| *CmndDesc:* | ]]  Provide direct examples of how to use vagrant.
        #+end_org """)

        # od = collections.OrderedDict
        # cmnd = cs.examples.cmndEnter
        literal = cs.examples.execInsert

        if b.subProc.Op(outcome=cmndOutcome, log=0).bash(
                f"""docker image ls -q | head -1""",
        ).isProblematic():  return(b_io.eh.badOutcome(cmndOutcome))
        oneImageId = cmndOutcome.stdout.strip()

        if b.subProc.Op(outcome=cmndOutcome, log=0).bash(
                f"""docker ps -q | head -1""",
        ).isProblematic():  return(b_io.eh.badOutcome(cmndOutcome))
        oneContainerId = cmndOutcome.stdout.strip() or "<containerId>"

        cs.examples.menuChapter('=Direct Docker Interface Commands=')

        cs.examples.menuSection('/Initializations and Setup/')

        literal("NOTYET -- PKG sbom")
        literal("sudo groupadd docker")
        literal("sudo usermod -aG docker $USER")

        literal("https://hub.docker.com")
        literal("docker search --help")

        cs.examples.menuSection('/BISOS Docker Base Dockerfiles/')

        literal("ls -ld /bisos/git/bxRepos/bxObjects/bro_dockerfiles/debian")
        literal("tree /bisos/git/bxRepos/bxObjects/bro_dockerfiles/debian/12")

        cs.examples.menuSection('/Docker:: Inpsetc, Examine/')

        literal("docker ps --help")
        literal("docker ps")
        literal("docker ps -a")

        literal("docker logs --help")
        literal(f"docker logs {oneContainerId}")

        cs.examples.menuSection('/Docker Images/')

        literal("docker image --help")
        literal("docker image ls")
        literal(f"docker image inspect {oneImageId}")
        literal("docker build -t debian-gnome-desktop .")
        literal("docker build --no-cache --progress=plain -t debian-12-novnc-gnome .")
        literal("docker image prune -a -f # Remove all unused images (dangling and unreferenced)-- forced")
        literal("docker images -f dangling=true -q # -q provides only image ids")
        literal("docker rmi $(docker images -f dangling=true -q) # Remove dangling images")

        cs.examples.menuSection('/Docker Run Interface -- Start A Container/')

        # -d: detached (background). Returns the container ID immediately.
        # -p <host>:<container>: publish a port. Repeatable.
        # --name mycontainer: stable name for later stop/start/rm/exec/logs
        #   reference (default is auto-generated two-word name).
        # bisos-image: image to instantiate (positional, after all flags).
        # Note: ports below are illustrative -- adjust host-side to match your image.
        literal("docker run -d -p 6901:6901 -p 5901:5901 -p 2222:22 --name mycontainer bisos-image")

        cs.examples.menuSection('/Docker Container Lifecycle -- stop, start, restart/')

        # docker stop: SIGTERM, wait <timeout>s, then SIGKILL. Preferred over kill.
        #   For systemd (privileged) containers use -t 30+ to let systemd shut down services.
        literal("docker stop mycontainer          # graceful stop (SIGTERM, 10s grace, then SIGKILL)")
        literal("docker stop -t 30 mycontainer   # longer grace for systemd containers")
        literal("docker kill mycontainer          # immediate SIGKILL -- avoid for systemd containers")
        # Container still exists after stop; start restarts it in place with the same config.
        literal("docker start mycontainer         # restart a stopped container (keeps state)")
        literal("docker restart mycontainer       # stop then start")
        literal("docker ps          # running containers only")
        literal("docker ps -a       # all containers including stopped")

        cs.examples.menuSection('/Docker Container Removal/')

        # A stopped container still exists on disk (config + writable layer). rm deletes it.
        # rm requires the container to be stopped first, unless -f is passed.
        literal("docker rm mycontainer       # remove a stopped container")
        literal("docker rm -f mycontainer    # force-remove even if running (stops + rm in one step)")
        literal("docker container prune     # remove all stopped containers (interactive)")

        cs.examples.menuSection('/Doocker Compose Interface/')

        literal("docker compose --help")
        literal("docker compose up -d  # Builds, (re)creates, starts, and attaches to containers for a service")
        literal("docker compose start   # useful only to restart existing containers, never creates new containers")
        literal("docker compose stop  # stop exisiting container")
        literal("docker compose down  # stop exisiting container")
        literal("docker compose config  # compile the yamel file")
        literal("docker compose run  #  similar to docker run -ti -- opens interactive terminal, returns exit status")
        literal("docker compose logs  #  or -f")


        cs.examples.menuSection('/Docker:: Execute a command in a running container/')

        literal("docker exec --help")
        literal("docker exec -it mycontainer bash")

        cs.examples.menuSection('/Docker Logs and Inspect/')

        literal("docker logs mycontainer         # print stdout/stderr of container")
        literal("docker logs -f mycontainer      # follow (like tail -f)")
        literal("docker inspect mycontainer      # full JSON: image, mounts, network, state")

        cs.examples.menuSection('/Docker Backup + Restore --- commit, save/load, export/import, volume backup/')

        literal("# See Blee panel: /bisos/panels/bisos-core/virtualization/docker/backupAndRestore/")
        literal("# ")
        literal("# Commit --- snapshot a running container's writable layer as a new image layer.")
        literal("# Does NOT capture volumes. Discouraged as a workflow; use for one-off checkpoints.")
        literal(f"docker commit {oneContainerId} myimage:snapshot-$(date +%Y%m%d)")
        literal(f"docker commit -m 'checkpoint before X' -a 'me <me@ex>' {oneContainerId} myimage:snapshot")
        literal("# ")
        literal("# Image save + load --- portable, lossless image transfer (all layers, metadata).")
        literal("# RECOMMENDED path for image transfer between hosts.")
        literal(f"docker save {oneImageId} -o /bisos/var/dockerProc/backups/${{USER}}/<imageName>/<imageName>-$(date +%Y%m%d-%H%M%S).tar")
        literal(f"docker save {oneImageId} | gzip > backup.tar.gz    # compressed variant")
        literal("docker load -i backup.tar                         # restore on receiving host")
        literal("gunzip -c backup.tar.gz | docker load")
        literal("# ")
        literal("# Container export + import --- flat filesystem, no layer history, single-layer image.")
        literal("# Faster than commit-save but loses image metadata (CMD, ENV, EXPOSE, volumes).")
        literal(f"docker export {oneContainerId} -o fs.tar")
        literal("docker import fs.tar newimage:imported")
        literal("# ")
        literal("# Volume backup --- named-volume contents to a tar via a helper container.")
        literal("# Neither commit nor export capture volume data --- always back up volumes separately.")
        literal("docker volume ls")
        literal("docker run --rm -v myvol:/data -v $(pwd):/backup alpine tar czf /backup/myvol.tgz /data")
        literal("docker run --rm -v myvol:/data -v $(pwd):/backup alpine tar xzf /backup/myvol.tgz -C /  # restore")
        literal("# ")
        literal("# BISOS convention: backup tarballs live at")
        literal("#   /bisos/var/dockerProc/backups/<user>/<imageName>/<imageName>-<timestamp>.tar")
        literal("# The containerProc_imageSave Cmnd (see .spcs -i examples) automates this path.")

        cs.examples.menuSection('/Docker Cleanups/')

        literal("docker image prune -a -f # Remove all unused images (dangling and unreferenced)-- forced")
        literal("docker system prune # DANGER:: Prune entire Docker system (containers, images, volumes, networks)")

        return(cmndOutcome)



####+BEGIN: blee:bxPanel:foldingSection :outLevel 0 :sep nil :title "Main" :anchor ""  :extraInfo "Framework DBlock"
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*     [[elisp:(outline-show-subtree+toggle)][| _Main_: |]]  Framework DBlock  [[elisp:(org-shifttab)][<)]] E|
#+end_org """
####+END:

####+BEGIN: b:py3:cs:framework/main :csInfo "csInfo" :noCmndEntry "examples" :extraParamsHook "g_extraParams" :importedCmndsModules "g_importedCmndsModules"
""" #+begin_org
*  _[[elisp:(blee:menu-sel:outline:popupMenu)][±]]_ _[[elisp:(blee:menu-sel:navigation:popupMenu)][Ξ]]_ [[elisp:(outline-show-branches+toggle)][|=]] [[elisp:(bx:orgm:indirectBufOther)][|>]] *[[elisp:(blee:ppmm:org-mode-toggle)][|N]]*  CsFrmWrk   [[elisp:(outline-show-subtree+toggle)][||]] =g_csMain= (csInfo, _examples_, g_extraParams, g_importedCmndsModules)
#+end_org """

if __name__ == '__main__':
    cs.main.g_csMain(
        csInfo=csInfo,
        noCmndEntry=examples,  # specify a Cmnd name
        extraParamsHook=g_extraParams,
        importedCmndsModules=g_importedCmndsModules,
    )

####+END:

####+BEGIN: b:py3:cs:framework/endOfFile :basedOn "classification"
""" #+begin_org
* [[elisp:(org-cycle)][| *End-Of-Editable-Text* |]] :: emacs and org variables and control parameters
#+end_org """

#+STARTUP: showall

### local variables:
### no-byte-compile: t
### end:
####+END:
