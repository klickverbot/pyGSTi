#*****************************************************************
#    pyGSTi 0.9:  Copyright 2015 Sandia Corporation              
#    This Software is released under the GPL license detailed    
#    in the file "license.txt" in the top-level pyGSTi directory 
#*****************************************************************
""" End-to-end functions for performing long-sequence GST """

import os as _os
import warnings as _warnings
import numpy as _np
import sys as _sys

from .. import report as _report
from .. import algorithms as _alg
from .. import construction as _construction
from .. import io as _io
from .. import objects as _objs
from .. import tools as _tools

def do_long_sequence_gst(dataFilenameOrSet, targetGateFilenameOrSet,
                         rhoStrsListOrFilename, EStrsListOrFilename,
                         germsListOrFilename, maxLengths, gateLabels=None, 
                         weightsDict=None, rhoEPairs=None, constrainToTP=True, 
                         gaugeOptToCPTP=False, gaugeOptRatio=0.001,
                         objective="logl", advancedOptions={}, lsgstLists=None,
                         truncScheme="whole germ powers"):
    """
    Perform end-to-end GST analysis using Ls and germs, with L as a maximum length.

    Constructs gate strings by repeating germ strings an integer number of times
    such that the length of the repeated germ is less than or equal to the
    maximum length set in maxLengths.  The LGST estimate of the gates is computed,
    gauge optimized, and then and used as the seed for either LSGST or MLEGST.

    LSGST is iterated len(maxLengths) times with successively larger sets of gate
    strings.  On the i-th iteration, the repeated germs sequences limited by
    maxLengths[i] are included in the growing set of strings used by LSGST.  The
    final iteration will use MLEGST when objective == "logl" to maximize the
    true log-likelihood instead of minimizing the chi-squared function.

    Once computed, the gate set estimates are gauge optimized to the
    CPTP space (if gaugeOptToCPTP == True) and then to the target gate set
    (using gaugeOptRatio). A Results object is returned, which encapsulates the
    input and outputs of this GST analysis, and can to generate final end-user
    output such as reports and presentations.    
    

    Parameters
    ----------
    dataFilenameOrSet : DataSet or string
        The data set object to use for the analysis, specified either directly
        or by the filename of a dataset file (in text format).

    targetGateFilenameOrSet : GateSet or string
        The target gate set, specified either directly or by the filename of a 
        gateset file (text format).

    rhoStrsListOrFilename : (list of GateStrings) or string
        The state preparation fiducial gate strings, specified either directly 
        or by the filename of a gate string list file (text format).

    EStrsListOrFilename : (list of GateStrings) or string or None
        The measurement fiducial gate strings, specified either directly 
        or by the filename of a gate string list file (text format).  If None,
        then use the same strings as specified by rhoStrsListOrFilename.

    germsListOrFilename : (list of GateStrings) or string
        The germ gate strings, specified either directly or by the filename of a
        gate string list file (text format).

    maxLengths : list of ints
        List of the integers, one per LGST iteration, which set truncation lengths
        for repeated germ strings.  The list of gate strings for the i-th LSGST
        iteration includes the repeated germs truncated to the L-values *up to* 
        and including the i-th one.

    gateLabels : list or tuple
        A list or tuple of the gate labels to use when generating the sets of
        gate strings used in LSGST iterations.  If None, then the gate labels
        of the target gateset will be used.  This option is useful if you 
        only want to include a *subset* of the available gates in the LSGST
        strings (e.g. leaving out the identity gate).

    weightsDict : dict, optional
        A dictionary with keys == gate strings and values == multiplicative scaling 
        factor for the corresponding gate string. The default is no weight scaling at all.

    rhoEPairs : list of 2-tuples, optional
        Specifies a subset of all rhoStr,EStr string pairs to be used in this
        analysis.  Each element of rhoEPairs is a (iRhoStr, iEStr) 2-tuple of integers,
        which index a string within the state preparation and measurement fiducial
        strings respectively.

    constrainToTP : bool, optional
        Whether to constrain GST to trace-preserving gatesets.

    gaugeOptToCPTP : bool, optional
        If True, resulting gate sets are first optimized to CPTP and then to the target.
        If False, gate sets are only optimized to the target gate set.
        
    gaugeOptRatio : float, optional
        The ratio spamWeight/gateWeight used for gauge optimizing to the target gate set.
    
    objective : {'chi2', 'logl'}, optional
        Specifies which final objective function is used: the chi-squared or
        the log-likelihood.
        
    advancedOptions : dict, optional
        Specifies advanced options most of which deal with numerical details of the
        objective function.   The 'verbosity' option is an integer specifying the level
        of detail printed to stdout during the GST calculation.

    lsgstLists : list of gate string lists, optional
        Provides explicit list of gate string lists to be used in analysis; to be given if
        the dataset uses "incomplete" or "reduced" sets of gate string.  Default is None.

    truncScheme : str, optional
        Truncation scheme used to interpret what the list of maximum lengths
        means. If unsure, leave as default. Allowed values are:
        
        - 'whole germ powers' -- germs are repeated an integer number of 
          times such that the length is less than or equal to the max.
        - 'truncated germ powers' -- repeated germ string is truncated
          to be exactly equal to the max (partial germ at end is ok).
        - 'length as exponent' -- max. length is instead interpreted
          as the germ exponent (the number of germ repetitions).

        
    Returns
    -------
    Results
    """
                    
    cwd = _os.getcwd()

    #Get target gateset
    if isinstance(targetGateFilenameOrSet, str):
        gs_target = _io.load_gateset(targetGateFilenameOrSet)
    else:
        gs_target = targetGateFilenameOrSet #assume a GateSet object

    #Get dataset
    if isinstance(dataFilenameOrSet, str):
        ds = _io.load_dataset(dataFilenameOrSet)
        default_dir = _os.path.dirname(dataFilenameOrSet) #default directory for reports, etc
        default_base = _os.path.splitext( _os.path.basename(dataFilenameOrSet) )[0]
    else:
        ds = dataFilenameOrSet #assume a Dataset object
        default_dir = default_base = None

    #Get gate strings and labels
    if gateLabels is None:
        gateLabels = gs_target.keys()

    if isinstance(rhoStrsListOrFilename, str):
        rhoStrs = _io.load_gatestring_list(rhoStrsListOrFilename)
    else: rhoStrs = rhoStrsListOrFilename

    if EStrsListOrFilename is None:
        EStrs = rhoStrs #use same strings for EStrs if EStrsListOrFilename is None
    else:
        if isinstance(EStrsListOrFilename, str):
            EStrs = _io.load_gatestring_list(EStrsListOrFilename)
        else: EStrs = EStrsListOrFilename

    if isinstance(germsListOrFilename, str):
        germs = _io.load_gatestring_list(germsListOrFilename)
    else: germs = germsListOrFilename
    if lsgstLists is None:
        lsgstLists = _construction.stdlists.make_lsgst_lists_asymmetric_fids(
            gateLabels, rhoStrs, EStrs, germs, maxLengths, rhoEPairs, truncScheme)

    #Starting Point = LGST
    gate_dim = gs_target.get_dimension()
    specs = _construction.build_spam_specs(rhoStrs=rhoStrs, EStrs=EStrs,
                                           EVecInds=gs_target.get_evec_indices())
    gs_lgst = _alg.do_lgst(ds, specs, gs_target, svdTruncateTo=gate_dim, verbosity=3)

    if constrainToTP: #gauge optimize (and contract if needed) to TP, then lock down first basis element as the identity
        firstElIdentityVec = _np.zeros( (gate_dim,1) )
        firstElIdentityVec[0] = gate_dim**0.25 # first basis el is assumed = sqrt(gate_dim)-dimensional identity density matrix 
        minPenalty, gaugeMx, gs_in_TP = _alg.optimize_gauge(gs_lgst, "TP",  returnAll=True, spamWeight=1.0, gateWeight=1.0, verbosity=3)
        if minPenalty > 0:
            gs_in_TP = _alg.contract(gs_in_TP, "TP")
            if minPenalty > 1e-5: 
                _warnings.warn("Could not gauge optimize to TP (penalty=%g), so contracted LGST gateset to TP" % minPenalty)

        gs_after_gauge_opt = _alg.optimize_gauge(gs_in_TP, "target", targetGateset=gs_target, constrainToTP=True, spamWeight=1.0, gateWeight=1.0)
        gs_after_gauge_opt.set_identity_vec( firstElIdentityVec ) # declare that this basis has the identity as its first element

    else: # no TP constraint
        gs_after_gauge_opt = _alg.optimize_gauge(gs_lgst, "target", targetGateset=gs_target, spamWeight=1.0, gateWeight=1.0)
        #OLD: gs_clgst = _alg.contract(gs_after_gauge_opt, "CPTP")
        #TODO: set identity vector, or leave as is, which assumes LGST had the right one and contraction doesn't change it ??

    #Run LSGST on data
    if objective == "chi2":
        gs_lsgst_list = _alg.do_iterative_mc2gst(ds, gs_after_gauge_opt, lsgstLists, 
                                              minProbClipForWeighting=advancedOptions.get('minProbClipForWeighting',1e-4),
                                              probClipInterval = advancedOptions.get('probClipInterval',(-1e6,1e6)),
                                              returnAll=True, opt_G0=(not constrainToTP), opt_SP0=(not constrainToTP),
                                              gatestringWeightsDict=weightsDict, verbosity=advancedOptions.get('verbosity',2),
                                              memLimit=advancedOptions.get('memoryLimitInBytes',None))
    elif objective == "logl":
        gs_lsgst_list = _alg.do_iterative_mlgst(ds, gs_after_gauge_opt, lsgstLists,
                                               minProbClip = advancedOptions.get('minProbClip',1e-4),
                                               probClipInterval = advancedOptions.get('probClipInterval',(-1e6,1e6)),
                                               radius=advancedOptions.get('radius',1e-4), 
                                               returnAll=True, opt_G0=(not constrainToTP), opt_SP0=(not constrainToTP),
                                               verbosity=advancedOptions.get('verbosity',2),
                                               memLimit=advancedOptions.get('memoryLimitInBytes',None))
    else:
        raise ValueError("Invalid longSequenceObjective: %s" % objective)

    #Run the gatesets through gauge optimization, first to CPTP then to target
    #   so fidelity and frobenius distance w/targets is more meaningful
    if gaugeOptToCPTP:
        print "\nGauge Optimizing to CPTP..."; _sys.stdout.flush()
        go_gs_lsgst_list = [_alg.optimize_gauge(gs,'CPTP', constrainToTP=constrainToTP) for gs in gs_lsgst_list]
    else:
        go_gs_lsgst_list = gs_lsgst_list
        
    for i,gs in enumerate(go_gs_lsgst_list):
        if gaugeOptToCPTP and _tools.sum_of_negative_choi_evals(gs) < 1e-8:  #if a gateset is in CP, then don't let it out (constrain = True)
            go_gs_lsgst_list[i] = _alg.optimize_gauge(gs,'target',targetGateset=gs_target,
                                                      constrainToTP=constrainToTP, constrainToCP=True,
                                                      gateWeight=1, spamWeight=gaugeOptRatio)
        
        else: #otherwise just optimize to the target and forget about CPTP...
            go_gs_lsgst_list[i] = _alg.optimize_gauge(gs,'target',targetGateset=gs_target,
                                                      constrainToTP=constrainToTP, 
                                                      gateWeight=1, spamWeight=gaugeOptRatio)

    truncFn = _construction.stdlists._getTruncFunction(truncScheme)

    ret = _report.Results()
    ret.init_Ls_and_germs(objective, gs_target, ds, 
                        gs_after_gauge_opt, maxLengths, germs,
                        go_gs_lsgst_list, lsgstLists, rhoStrs, EStrs,
                        truncFn,  constrainToTP, rhoEPairs, gs_lsgst_list)
    ret.set_additional_info(advancedOptions.get('minProbClip',1e-4),
                          advancedOptions.get('minProbClipForWeighting',1e-4),
                          advancedOptions.get('probClipInterval',(-1e6,1e6)),
                          advancedOptions.get('radius',1e-4), 
                          weightsDict, default_dir, default_base)

    assert( len(maxLengths) == len(lsgstLists) == len(go_gs_lsgst_list) )
    return ret