#!/bin/env python
# -*- coding: utf-8 -*-

import typing ; csInfo: typing.Dict[str, typing.Any] = {'category': 'csxu', 'name': 'containerProc-seed.cs', 'features': ['direct', 'seeded']}

csInfo['summary'] = """ #+begin_org
* ~[Summary]~ :: Seed CS for container image lifecycle — build, run, verify, composeUp/Down, status, clean.
  Planted as dockerProc.spcs (docker leaves) or podmanProc.spcs (rootless-sysd leaves).
  All operating parameters are derived from the planted file's directory path.
#+end_org """

####+BEGIN: b:py3:cs:file/dblockControls :classification "cs-u"
""" #+begin_org
* [[elisp:(org-cycle)][| /Control Parameters Of This File/ |]] :: dblk ctrls classifications=cs-u
#+end_org """
####+END:

if 'csInfo' not in globals(): import typing ; csInfo: typing.Dict[str, typing.Any] = { 'moduleName': ['loadAs'], }
csInfo['version'] = '202608100001'
csInfo['status']  = 'inDev'
csInfo['panel'] = 'containerProc-seed-Panel.org'
csInfo['groupingType'] = 'IcmGroupingType-pkged'
csInfo['cmndParts'] = 'IcmCmndParts[common] IcmCmndParts[param]'

####+BEGIN: b:py3:cs:framework/imports :basedOn "classification"
""" #+begin_org
*  _[[elisp:(org-cycle)][| ±]]_ _[[elisp:(org-cycle)][| Ξ]]_  CsFrmWrk  *Imports*
#+end_org """
from bisos import b
from bisos.b import cs
from bisos.b import b_io

import collections
####+END:

####+BEGIN: b:py3:cs:framework/exceptionImports :comment "BISOS Enhanced Exceptions"
""" #+begin_org
*  _[[elisp:(org-cycle)][| ±]]_  CsFrmWrk  *Imports* BISOS Enhanced Exceptions
#+end_org """
from bisos.b import enhancedExceptions
####+END:

####+BEGIN: b:py3:cs:framework/csxuSeeded :comment "Import plantedCsu"
""" #+begin_org
*  _[[elisp:(org-cycle)][| ±]]_  CsFrmWrk  ~Seeded CSXU~ Import plantedCsu
#+end_org """
from bisos.csSeed import seedsLib
if seedsLib.seededCsxuInfo.plantOfThisSeed is not None:
    b.importFileAs('plantedCsu', seedsLib.seededCsxuInfo.plantOfThisSeed, __file__, __name__)
####+END:

import sys

""" #+begin_org
*  CsFrmWrk  ~csuList emacs-list Specifications~
#+BEGIN_SRC emacs-lisp
(setq  b:py:cs:csuList
  (list
   "bisos.csPlayer.csxuFps_csu"
   "bisos.dockerProc.containerProc_csu"
   "plantedCsu"
 ))
#+END_SRC
#+end_org """

####+BEGIN: b:py3:cs:framework/csuListImportPlus :pyImports t :csuImports t :csuParams t
""" #+begin_org
*  CsFrmWrk  ~Process CSU List~
#+end_org """

from bisos.csPlayer import csxuFps_csu
from bisos.dockerProc import containerProc_csu

csuList = [
    'bisos.csPlayer.csxuFps_csu',
    'bisos.dockerProc.containerProc_csu',
    'plantedCsu',
]

if seedsLib.seededCsxuInfo.plantOfThisSeed is None:
    csuList.remove('plantedCsu')

g_importedCmndsModules = cs.csuList_importedModules(csuList)

def g_extraParams():
    csParams = cs.param.CmndParamDict()
    cs.csuList_commonParamsSpecify(csuList, csParams)
    cs.argsparseBasedOnCsParams(csParams)

####+END:

####+BEGIN: b:py3:cs:main/exposedSymbols :classes ()
""" #+begin_org
*  CsFrmWrk  ~CS Controls and Exposed Symbols~
#+end_org """
####+END:

cs.invOutcomeReportControl(cmnd=True, ro=True)


###############################################################################
# examples
###############################################################################

class examples(cs.Cmnd):
    cmndParamsMandatory = []
    cmndParamsOptional = []
    cmndArgsLen = {'Min': 0, 'Max': 0}
    rtInvConstraints = cs.rtInvoker.RtInvoker.new_noRo()

    @cs.track(fnLoc=True, fnEntry=True, fnExit=True)
    def cmnd(self,
             rtInv: cs.RtInvoker,
             cmndOutcome: b.op.Outcome,
             argsList: typing.Optional[list[str]] = None,
    ) -> b.op.Outcome:
        """FrameWrk: CS-Main-Examples"""
        failed = b_io.eh.badOutcome
        callParamsDict = {}
        if self.invocationValidate(rtInv, cmndOutcome, callParamsDict, argsList).isProblematic():
            return failed(cmndOutcome)

        cs.examples.myName(cs.G.icmMyName(), cs.G.icmMyFullName())
        cs.examples.commonBrief()
        csxuFps_csu.playerMenuExamples().pyCmnd()
        containerProc_csu.examples_csu()

        if seedsLib.seededCsxuInfo.seedOfThisPlant is not None:
            seedsLib.plantedCsuExamplesRun()

        return cmndOutcome


###############################################################################
# Main
###############################################################################

if __name__ == '__main__':
    cs.main.g_csMain(
        csInfo=csInfo,
        noCmndEntry=examples,
        extraParamsHook=g_extraParams,
        ignoreUnknownParams=False,
        importedCmndsModules=g_importedCmndsModules,
    )

### local variables:
### no-byte-compile: t
### end:
