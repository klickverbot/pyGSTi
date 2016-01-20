"""
Functions for creating and converting between matrix bases.

There are three different bases that GST can use and convert between:
  - The Standard ("std") basis: 
     State space is the tensor product of [0,1] for each qubit, e.g. for two qubits: ``[00,01,10,11] = [ |0>|0>, |0>|1>, ... ]``
     the gate space is thus the tensor product of two qubit spaces, so identical in form to state space
     for twice qubits, but interpret as ket/bra states.  E.g. for a *one* qubit gate, std basis is: = ``[ |0><0|, |0><1|, ... ]``

  - The Pauli-product ("pp") basis:
     Not used for state space - just for gates.  Basis consists of tensor products of the 4 pauli matrices (normalized by sqrt(2)).
     Examples:

     - 1-qubit gate basis is [ I, X, Y, Z ]  (in std basis, each is a pauli mx / sqrt(2))
     - 2-qubit gate basis is [ IxI, IxX, IxY, IxZ, XxI, ... ] (16 of them. In std basis, each is the tensor product of two pauli/sqrt(2) mxs) 
     
  - The Gell-Mann ("gm") basis:
     Not used for state space - just for gates.  Basis consists of the Gell-Mann matrices of the given dimension (useful for dimensions that are not a power of 2)
     Examples:

     - 1-qubit gate basis is [ I, X, Y, Z ]  (in std basis, each is a pauli mx / sqrt(2)) -- SAME as Pauli-product!
     - 2-qubit gate basis is the 16 Gell-Mann matrices of dimension 4. In std basis, each is as given by Wikipedia page up to normalization.

Notes:
  - The elements of each basis are normalized so that Tr(Bi Bj) = delta_ij
  - since density matrices are Hermitian and all Gell-Mann and Pauli-product matrices are Hermitian too, 
    gate parameterization by Gell-Mann or Pauli-product matrices have *real* coefficients, whereas
    in the standard basis gate matrices can have complex elements but these elements are additionally 
    constrained.  This makes gate matrix parameterization and optimization much more convenient
    in the "gm" or "pp" bases.
"""
import numpy as _np
import itertools as _itertools
import MatrixOps as _MOps



## Pauli basis matrices
sqrt2 = _np.sqrt(2)
id2x2 = _np.array([[1,0],[0,1]])
sigmax = _np.array([[0,1],[1,0]])
sigmay = _np.array([[0,-1.0j],[1.0j,0]])
sigmaz = _np.array([[1,0],[0,-1]])

sigmaii = _np.kron(id2x2,id2x2)
sigmaix = _np.kron(id2x2,sigmax)
sigmaiy = _np.kron(id2x2,sigmay)
sigmaiz = _np.kron(id2x2,sigmaz)
sigmaxi = _np.kron(sigmax,id2x2)
sigmaxx = _np.kron(sigmax,sigmax)
sigmaxy = _np.kron(sigmax,sigmay)
sigmaxz = _np.kron(sigmax,sigmaz)
sigmayi = _np.kron(sigmay,id2x2)
sigmayx = _np.kron(sigmay,sigmax)
sigmayy = _np.kron(sigmay,sigmay)
sigmayz = _np.kron(sigmay,sigmaz)
sigmazi = _np.kron(sigmaz,id2x2)
sigmazx = _np.kron(sigmaz,sigmax)
sigmazy = _np.kron(sigmaz,sigmay)
sigmazz = _np.kron(sigmaz,sigmaz)

#sigmaVec = (id2x2/sqrt2, sigmax/sqrt2, sigmay/sqrt2, sigmaz/sqrt2)

#sigmaVec_2Q = [ ]
#for s in range(4):
#    for t in range(4):
#        sigmaVec_2Q.append( _np.kron(sigmaVec[s], sigmaVec[t]) )

#mx to convert std basis to *normalized* Pauli basis (sigma mxs vectorized as columns)
#PauliToStd = _np.array( [[ 1, 0,   0,  1 ],
#                           [ 0, 1,  1j,  0 ],
#                           [ 0, 1, -1j,  0 ],  
#                           [ 1, 0,   0, -1 ] ] )
#StdToPauli = _np.linalg.inv(PauliToStd)
#
#PauliToStd_2Q = _np.empty( (16,16), 'complex' )
#for col in range(16):
#    for s1 in range(4):
#        for s2 in range(4):
#            row = 4*s1 + s2  #break row index into s1 and s2 for easy index into 4x4 sigmaVec_2Q elements
#            PauliToStd_2Q[row,col] = sigmaVec_2Q[col][s1,s2] * 2.0 # 2 cancels the normalizing 1/sqrt(2) factors in sigmaVec_2Q
#StdToPauli_2Q = _np.linalg.inv(PauliToStd_2Q)


##Matrix unit basis
def _mut(i,j,N):
    mx = _np.zeros( (N,N), 'd'); mx[i,j] = 1.0
    return mx
mxUnitVec = ( _mut(0,0,2), _mut(0,1,2), _mut(1,0,2), _mut(1,1,2) )
mxUnitVec_2Q = ( _mut(0,0,4), _mut(0,1,4), _mut(0,2,4), _mut(0,3,4),
                 _mut(1,0,4), _mut(1,1,4), _mut(1,2,4), _mut(1,3,4),
                 _mut(2,0,4), _mut(2,1,4), _mut(2,2,4), _mut(2,3,4),
                 _mut(3,0,4), _mut(3,1,4), _mut(3,2,4), _mut(3,3,4)  )



def _processBlockDims(dimOrBlockDims):
    """
    Performs basic processing on the dimensions
      of a direct-sum space.
    
    Parameters
    ----------
    dimOrBlockDims : int or list of ints
        Structure of the density-matrix space.
        A list of integers designates the space is
          the direct sum of spaces with the square of the given
          matrix-block dimensions.  Matrices in this space are
          represented in the standard basis by a block-diagonal
          matrix with blocks of the given dimensions.
        A single integer is equivalent to a list with a single 
          element, and so designates the space of matrices with
          the given dimension, and thus a space of the dimension^2.

    Returns
    -------
    dmDim : int
        The (matrix) dimension of the overall density matrix 
        within which the block-diagonal density matrix described by
        dimOrBlockDims is embedded, equal to the sum of the 
        individual block dimensions. (The overall density matrix
        is a dmDim x dmDim matrix, and is contained in a space 
        of dimension dmDim**2).
    gateDim : int
        The (matrix) dimension of the "gate-space" corresponding 
        to the density matrix space, equal to the dimension
        of the density matrix space, sum( ith-block_dimension^2 ).
        Gate matrices are thus gateDim x gateDim dimensions.
    blockDims : list of ints
        Dimensions of the individual matrix-blocks.  The direct sum
        of the matrix spaces (of dim matrix-block-dim^2) forms the 
        density matrix space.  Equals:
        [ dimOrBlockDims ] : if dimOrBlockDims is a single int
          dimOrBlockDims   : otherwise
    """
    if type(dimOrBlockDims) in (list,tuple):  #treat as state space dimensions
        dmDim  = sum( [ blockDim    for blockDim in dimOrBlockDims] )  # *full* density matrix is dmDim x dmDim
        gateDim = sum( [ blockDim**2 for blockDim in dimOrBlockDims] )  # gate matrices will be vecDim x vecDim
        blockDims = dimOrBlockDims
    elif type(dimOrBlockDims) == int:
        dmDim = dimOrBlockDims
        gateDim = dimOrBlockDims**2 
        blockDims = [ dimOrBlockDims ]
    else:
        raise ValueError("Invalid dimOrBlockDims = %s" % str(dimOrBlockDims))

    return dmDim, gateDim, blockDims

#    dim = 0
#    dmDim = 0 # dimension of density matrix
#    dmiToVi = {} # density matrix index (2-tuple) to vectorized density matrix index (integer) mapping
#
#    for blockDim in stateSpaceDims:
#        
#        dmDim += blockDim
#
#    for k,blockDim in enumerate(stateSpaceDims):
#        for i in range(dmDim,dmDim+blockDim):
#            for j in range(dmDim,dmDim+blockDim):
#                dmiToVi[ (i,j) ] = dim
#                dim += 1
#        dmDim += blockDim
#        # Note: above loop performs dim += blockDim**2  -- the gate basis has a matrix unit
#        # for each element of each tensor-product-block of the density matrix
#
#    #return dmiToVi, dmDim, dim  #Note dim == len(dmiToVi)
#    return dmDim, dim


def GetMatrixUnitMatrices(dimOrBlockDims):
    """ 
    Get the elements of the matrix unit, or "standard", basis
    spanning the density-matrix space given by dimOrBlockDims.
    
    The returned matrices are given in the standard basis of the 
    "embedding" density matrix space, that is, the space which
    embeds the block-diagonal matrix structure stipulated in
    dimOrBlockDims. These matrices form an orthonormal basis under
    the trace inner product, i.e. Tr( dot(Mi,Mj) ) == delta_ij.

    Parameters
    ----------
    dimOrBlockDims : int or list of ints
        Structure of the density-matrix space.
        
    Returns
    -------
    list
        A list of N numpy arrays each of shape (dmDim, dmDim),
        where dmDim is the matrix-dimension of the overall 
        "embedding" density matrix (the sum of dimOrBlockDims)
        and N is the dimension of the density-matrix space, 
        equal to sum( block_dim_i^2 ).

    Notes
    -----
    Each element is a matrix containing
    a single "1" entry amidst a background of zeros, and there
    are never "1"s in positions outside the block-diagonal structure.
    """
    dmDim, gateDim, blockDims = _processBlockDims(dimOrBlockDims)

    mxList = []; start = 0
    for blockDim in blockDims:
        for i in range(start,start+blockDim):
            for j in range(start,start+blockDim):
                mxList.append( _mut( i, j, dmDim ) )
        start += blockDim

    assert(len(mxList) == gateDim and start == dmDim)
    return mxList


def expandFromStdDirectSumMx(mxInStdBasis, dimOrBlockDims):
    """
    Convert a gate matrix in the standard basis of a "direct-sum" 
    space to a matrix in the standard basis of the embedding space.

    Parameters
    ----------
    mxInStdBasis : numpy array
        Matrix of size N x N, where N is the dimension
        of the density matrix space, i.e. sum( dimOrBlockDims_i^2 )

    dimOrBlockDims : int or list of ints
        Structure of the density-matrix space.
    
    Returns
    -------
    numpy array
        A M x M matrix, where M is the dimension of the
        embedding density matrix space, i.e.
        sum( dimOrBlockDims_i )^2
    """
    if dimOrBlockDims is None:
        return mxInStdBasis
    elif type(dimOrBlockDims) == int:
        assert(mxInStdBasis.shape == (dimOrBlockDims,dimOrBlockDims) )
        return mxInStdBasis
    else:
        dmDim, gateDim, blockDims = _processBlockDims(dimOrBlockDims)
        
        N = dmDim**2 #dimension of space in which density matrix is not restricted (the "embedding" density matrix space)
        mx = _np.zeros( (N,N), 'complex') #zeros since all added basis elements are coherences which get completely collapsed
        indxMap = [] # maps gate row/col indices onto indices of un-restricted "expanded" matrix

        start = 0
        for blockDim in blockDims:
            for i in range(start,start+blockDim):
                for j in range(start,start+blockDim):
                    indxMap.append( dmDim*i + j ) # index of (i,j) element when vectorized in the un-restricted gate mx
            start += blockDim

        for i,fi in enumerate(indxMap):
            for j,fj in enumerate(indxMap):
                mx[fi,fj] = mxInStdBasis[i,j]
    
        return mx

    
def contractToStdDirectSumMx(mxInStdBasis, dimOrBlockDims):
    """
    Convert a gate matrix in the standard basis of the
    embedding space to a matrix in the standard basis
    of the "direct-sum" space.

    Parameters
    ----------
    mxInStdBasis : numpy array
        Matrix of size M x M, where M is the dimension of the
        embedding density matrix space, i.e.
        sum( dimOrBlockDims_i )^2

    dimOrBlockDims : int or list of ints
        Structure of the density-matrix space.
    
    Returns
    -------
    numpy array
        A N x N matrix, where where N is the dimension
        of the density matrix space, i.e. sum( dimOrBlockDims_i^2 )
    """

    # TODO: should we check if the dimensions being projected out are the identity?
    if dimOrBlockDims is None:
        return mxInStdBasis
    elif type(dimOrBlockDims) == int:
        assert(mxInStdBasis.shape == (dimOrBlockDims,dimOrBlockDims) )
        return mxInStdBasis
    else:
        dmDim, gateDim, blockDims = _processBlockDims(dimOrBlockDims)

        mx = _np.empty((gateDim,gateDim), 'complex')
        indxMap = [] # maps gate row/col indices onto indices of un-restricted "expanded" matrix

        start = 0
        for blockDim in blockDims:
            for i in range(start,start+blockDim):
                for j in range(start,start+blockDim):
                    indxMap.append( dmDim*i + j ) # index of (i,j) element when vectorized in the un-restricted gate mx
            start += blockDim

        for i,fi in enumerate(indxMap):
            for j,fj in enumerate(indxMap):
                mx[i,j] = mxInStdBasis[fi,fj]
        
        return mx
    


def _GetGellMannNonIdentityDiagMxs(dimension):
    d = dimension
    listOfMxs = []
    if d > 2: 
        dm1_listOfMxs = _GetGellMannNonIdentityDiagMxs(d-1)
        for dm1_mx in dm1_listOfMxs:
            mx = _np.zeros( (d,d), 'complex' )
            mx[0:d-1,0:d-1] = dm1_mx
            listOfMxs.append(mx)
    if d > 1:
        mx = _np.identity( d, 'complex' )
        mx[d-1,d-1] = 1-d
        mx *= _np.sqrt( 2.0 / (d*(d-1)) )
        listOfMxs.append(mx)

    return listOfMxs

def GetGellMannMatrices(dimOrBlockDims):
    """ 
    Get the elements of the generalized Gell-Mann 
    basis spanning the density-matrix space given by dimOrBlockDims.

    The returned matrices are given in the standard basis of the 
    "embedding" density matrix space, that is, the space which
    embeds the block-diagonal matrix structure stipulated in
    dimOrBlockDims. These matrices form an orthogonal but not
    orthonormal basis under the trace inner product.

    Parameters
    ----------
    dimOrBlockDims : int or list of ints
        Structure of the density-matrix space.
        
    Returns
    -------
    list
        A list of N numpy arrays each of shape (dmDim, dmDim),
        where dmDim is the matrix-dimension of the overall 
        "embedding" density matrix (the sum of dimOrBlockDims)
        and N is the dimension of the density-matrix space, 
        equal to sum( block_dim_i^2 ).
    """
    if type(dimOrBlockDims) == int:
        d = dimOrBlockDims

        #Identity Mx
        listOfMxs = [ _np.identity(d, 'complex') ]
        
        #Non-diagonal matrices -- only take those whose non-zero elements are not "frozen" in cssb case
        for k in range(d):
            for j in range(k+1,d):
                mx = _np.zeros( (d,d), 'complex' )
                mx[k,j] = mx[j,k] = 1.0
                listOfMxs.append( mx )
        
        for k in range(d):
            for j in range(k+1,d):
                mx = _np.zeros( (d,d), 'complex' )
                mx[k,j] = -1.0j; mx[j,k] = 1.0j
                listOfMxs.append( mx )
        
        #Non-Id Diagonal matrices
        listOfMxs.extend( _GetGellMannNonIdentityDiagMxs(d) )

        assert(len(listOfMxs) == d**2)
        return listOfMxs

    elif type(dimOrBlockDims) in (list,tuple):
        dmDim, gateDim, blockDims = _processBlockDims(dimOrBlockDims)        

        listOfMxs = []; start = 0
        for blockDim in blockDims:
            for blockMx in GetGellMannMatrices(blockDim):
                mx = _np.zeros( (dmDim, dmDim), 'complex' )
                mx[start:start+blockDim, start:start+blockDim] = blockMx
                listOfMxs.append( mx )
            start += blockDim
        assert(len(listOfMxs) == gateDim)
        return listOfMxs
    
    else:
        raise ValueError("Invalid dimOrBlockDims = %s" % str(dimOrBlockDims))


def GetNormalizedGellMannMatrices(dimOrBlockDims):
    """ 
    Get the normalized elements of the generalized Gell-Mann 
    basis spanning the density-matrix space given by dimOrBlockDims.

    The returned matrices are given in the standard basis of the 
    "embedding" density matrix space, that is, the space which
    embeds the block-diagonal matrix structure stipulated in
    dimOrBlockDims. These matrices form an orthonormal basis
    under the trace inner product, i.e. Tr( dot(Mi,Mj) ) == delta_ij.

    Parameters
    ----------
    dimOrBlockDims : int or list of ints
        Structure of the density-matrix space.
        
    Returns
    -------
    list
        A list of N numpy arrays each of shape (dmDim, dmDim),
        where dmDim is the matrix-dimension of the overall 
        "embedding" density matrix (the sum of dimOrBlockDims)
        and N is the dimension of the density-matrix space, 
        equal to sum( block_dim_i^2 ).
    """
    mxs = GetGellMannMatrices(dimOrBlockDims)
    mxs[0] *= 1/_np.sqrt( mxs[0].shape[0] ) #identity mx
    for mx in mxs[1:]:
        mx *= 1/sqrt2
    return mxs

def GetGellMannToStdBasisTransformMatrix(dimOrBlockDims):
    """
    Construct the matrix which transforms a gate matrix in
    the Gell-Mann basis for a density matrix space to the 
    Standard basis (for the same space).

    Parameters
    ----------
    dimOrBlockDims : int or list of ints
        Structure of the density-matrix space.

    Returns
    -------
    numpy array
        An array of shape (N,N), where N is the dimension
        of the density matrix space, i.e. sum( dimOrBlockDims_i^2 ).

    Notes
    -----
        The returned matrix is block diagonal with one block
        per term in the direct sum of the the density matrix space.
        Each block is the transformation matrix for the corresponding
        part of density matrix space, consisting of flattened Gell-Mann
        basis matrices along it's columns.
    """
    #vectorize Gell Mann mxs and place appropriate elements into columns of a matrix
    dmDim, gateDim, blockDims = _processBlockDims(dimOrBlockDims)
    gmToStd = _np.zeros( (gateDim,gateDim), 'complex' )

    #Since a multi-block basis is just the direct sum of the individual block bases,
    # transform mx is just the transfrom matrices of the individual blocks along the 
    # diagonal of the total basis transform matrix

    start = 0
    for blockDim in blockDims:
        mxs = GetNormalizedGellMannMatrices(blockDim)
        assert( len(mxs) == blockDim**2 )

        for j,mx in enumerate(mxs):
            gmToStd[start:start+blockDim**2,start+j] = mx.flatten()

        start += blockDim**2

    assert(start == gateDim)        
    return gmToStd

def basisChg_StdToGellMann(mxInStdBasis, dimOrBlockDims=None):
    """ 
    Convert a gate matrix in the Standard basis of a
    density matrix space to the Gell-Mann basis (of the same space).

    Parameters
    ----------
    mxInStdBasis : numpy array
        The gate matrix, (a 2D square array)

    dimOrBlockDims : int or list of ints, optional
        Structure of the density-matrix space. If None, then assume
        mxInStdBasis operates on a single-block density matrix space,
        i.e. on K x K density matrices with K == sqrt( mxInStdBasis.shape[0] ).

    Returns
    -------
    numpy array
        The given gate matrix converted to the Gell-Mann basis.
        Array size is the same as mxInStdBasis.
    """
    if dimOrBlockDims is None: 
        dimOrBlockDims = int(round(_np.sqrt(mxInStdBasis.shape[0])))
        assert( dimOrBlockDims**2 == mxInStdBasis.shape[0] )
    
    gmToStd = GetGellMannToStdBasisTransformMatrix(dimOrBlockDims)
    stdToGM = _np.linalg.inv(gmToStd)

    if len(mxInStdBasis.shape) == 2 and mxInStdBasis.shape[0] == mxInStdBasis.shape[1]:
        gm = _np.dot( stdToGM, _np.dot( mxInStdBasis, gmToStd ) )
        if _np.linalg.norm(_np.imag(gm)) > 1e-8:
            raise ValueError("Gell-Mann matrix has non-zero imaginary part (%g)!" % 
                             _np.linalg.norm(_np.imag(gm)))
            #For debug, comment out exception above and uncomment this:
            #print "Warning: Gell-Mann matrix has non-zero imaginary part (%g)!" % \
            #    _np.linalg.norm(_np.imag(gm))
            #return gm
        return _np.real(gm)

    elif len(mxInStdBasis.shape) == 1 or \
         (len(mxInStdBasis.shape) == 2 and mxInStdBasis.shape[1] == 1): # (really vecInStdBasis)
        gm = _np.dot( stdToGM, mxInStdBasis )
        if _np.linalg.norm(_np.imag(gm)) > 1e-8: 
            raise ValueError("Gell-Mann vector has non-zero imaginary part (%g)!" % 
                             _np.linalg.norm(_np.imag(gm)))
            #For debug, comment out exception above and uncomment this:
            #print "Warning: Gell-Mann vector has non-zero imaginary part (%g)!" % \
            #                 _np.linalg.norm(_np.imag(gm))
            #return gm
        return _np.real(gm)

    else: raise ValueError("Invalid dimension of object - must be 1 or 2, i.e. a vector or matrix")


def basisChg_GellMannToStd(mxInGellMannBasis, dimOrBlockDims=None):
    """ 
    Convert a gate matrix in the Gell-Mann basis of a
    density matrix space to the Standard basis (of the same space).

    Parameters
    ----------
    mxInGellMannBasis : numpy array
        The gate matrix, (a 2D square array)

    dimOrBlockDims : int or list of ints, optional
        Structure of the density-matrix space. If None, then assume
        mxInGellMannBasis operates on a single-block density matrix space,
        i.e. on K x K density matrices with K == sqrt( mxInGellMannBasis.shape[0] ).

    Returns
    -------
    numpy array
        The given gate matrix converted to the Standard basis.
        Array size is the same as mxInGellMannBasis.
    """

    if dimOrBlockDims is None: 
        dimOrBlockDims = int(round(_np.sqrt(mxInGellMannBasis.shape[0])))
        assert( dimOrBlockDims**2 == mxInGellMannBasis.shape[0] )

    gmToStd = GetGellMannToStdBasisTransformMatrix(dimOrBlockDims)
    stdToGM = _np.linalg.inv(gmToStd)

    if len(mxInGellMannBasis.shape) == 2 and mxInGellMannBasis.shape[0] == mxInGellMannBasis.shape[1]:
        return _np.dot( gmToStd, _np.dot( mxInGellMannBasis, stdToGM ) )

    elif len(mxInGellMannBasis.shape) == 1 or \
         (len(mxInGellMannBasis.shape) == 2 and mxInGellMannBasis.shape[1] == 1): # (really vecInStdBasis)
        return _np.dot( gmToStd, mxInGellMannBasis )

    else: raise ValueError("Invalid dimension of object - must be 1 or 2, i.e. a vector or matrix")


def GetPauliProdMatrices(dim):
    """ 
    Get the elements of the Pauil-product basis
    spanning the space of dim x dim density matricies
    (matrix-dimension dim, space dimension dim^2).
    
    The returned matrices are given in the standard basis of the 
    density matrix space, and are thus kronecker products of
    the standard representation of the Pauli matrices, (i.e. where
    sigma_y == [[ 0, -i ], [i, 0]] ) normalized so that the 
    resulting basis is orthonormal under the trace inner product,
    i.e. Tr( dot(Mi,Mj) ) == delta_ij.

    Parameters
    ----------
    dim : int
        Matrix-dimension of the density-matrix space.  Must be
        a power of 2.
        
    Returns
    -------
    list
        A list of N numpy arrays each of shape (dim, dim),
        where N == dim^2, the dimension of the density-matrix space.

    Notes
    -----
    Matrices are ordered with first qubit being most significant, 
    e.g., for 2 qubits: II, IX, IY, IZ, XI, XX, XY, XZ, YI, ... ZZ
    """

    sigmaVec = (id2x2/sqrt2, sigmax/sqrt2, sigmay/sqrt2, sigmaz/sqrt2)

    def isInteger(x):
        return bool( abs(x - round(x)) < 1e-6 )

    if type(dim) != int:
        raise ValueError("Dimension for Pauli tensor product matrices must be an *integer* power of 2")

    nQubits = _np.log2(dim)
    if not isInteger(nQubits):
        raise ValueError("Dimension for Pauli tensor product matrices must be an integer *power of 2*")

    if nQubits == 0: #special case: return single 1x1 identity mx
        return [ _np.identity(1,'complex') ]

    matrices = []
    nQubits = int(round(nQubits))
    basisIndList = [ [0,1,2,3] ]*nQubits
    for k,sigmaInds in enumerate(_itertools.product(*basisIndList)): # each b == indices of tensor product basis element
        M = _np.identity(1,'complex')
        for i in sigmaInds:
            M = _np.kron(M,sigmaVec[i])
        matrices.append(M)

    return matrices


def GetPauliProdToStdBasisTransformMatrix(dimOrBlockDims):
    """
    Construct the matrix which transforms a gate matrix in
    the Pauil-product basis for a density matrix space to the 
    Standard basis (for the same space).

    Parameters
    ----------
    dimOrBlockDims : int or list of ints
        Structure of the density-matrix space.

    Returns
    -------
    numpy array
        An array of shape (N,N), where N is the dimension
        of the density matrix space, i.e. sum( dimOrBlockDims_i^2 ).

    Notes
    -----
        The returned matrix is block diagonal with one block
        per term in the direct sum of the the density matrix space.
        Each block is the transformation matrix for the corresponding
        part of density matrix space, consisting of flattened Pauli-product
        basis matrices along it's columns.
    """

    #vectorize tensor products of Pauli mxs and place them as columns into a matrix
    dmDim, gateDim, blockDims = _processBlockDims(dimOrBlockDims)
    ppToStd = _np.zeros( (gateDim,gateDim), 'complex' )

    #Since a multi-block basis is just the direct sum of the individual block bases,
    # transform mx is just the transfrom matrices of the individual blocks along the 
    # diagonal of the total basis transform matrix

    start = 0
    for blockDim in blockDims: 
        mxs = GetPauliProdMatrices(blockDim)
        assert( len(mxs) == blockDim**2 )

        for j,mx in enumerate(mxs):
            ppToStd[start:start+blockDim**2,start+j] = mx.flatten()

        start += blockDim**2

    assert(start == gateDim)        
    return ppToStd


def basisChg_StdToPauliProd(mxInStdBasis, dimOrBlockDims=None):
    """ 
    Convert a gate matrix in the Standard basis of a
    density matrix space to the Pauil-product basis (of the same space).

    Parameters
    ----------
    mxInStdBasis : numpy array
        The gate matrix, (a 2D square array)

    dimOrBlockDims : int or list of ints, optional
        Structure of the density-matrix space. If None, then assume
        mxInStdBasis operates on a single-block density matrix space,
        i.e. on K x K density matrices with K == sqrt( mxInStdBasis.shape[0] ).

    Returns
    -------
    numpy array
        The given gate matrix converted to the Pauil-product basis.
        Array size is the same as mxInStdBasis.
    """

    if dimOrBlockDims is None: 
        dimOrBlockDims = int(round(_np.sqrt(mxInStdBasis.shape[0])))
        assert( dimOrBlockDims**2 == mxInStdBasis.shape[0] )

    ppToStd = GetPauliProdToStdBasisTransformMatrix(dimOrBlockDims)
    stdToPP = _np.linalg.inv(ppToStd)

    if len(mxInStdBasis.shape) == 2 and mxInStdBasis.shape[0] == mxInStdBasis.shape[1]:
        pp = _np.dot( stdToPP, _np.dot( mxInStdBasis, ppToStd ) )
        if _np.linalg.norm(_np.imag(pp)) > 1e-8:
            raise ValueError("Pauil-product matrix has non-zero imaginary part (%g)!" % 
                             _np.linalg.norm(_np.imag(pp)))
            #For debug, comment out exception above and uncomment this:
            #print "Warning: Pauli-product matrix has non-zero imaginary part (%g)!" % \
            #    _np.linalg.norm(_np.imag(pp))
            #return pp
        return _np.real(pp)

    elif len(mxInStdBasis.shape) == 1 or \
         (len(mxInStdBasis.shape) == 2 and mxInStdBasis.shape[1] == 1): # (really vecInStdBasis)
        pp = _np.dot( stdToPP, mxInStdBasis )
        if _np.linalg.norm(_np.imag(pp)) > 1e-8:
            raise ValueError("Pauil-product vector has non-zero imaginary part (%g)!" % 
                             _np.linalg.norm(_np.imag(pp)))
            #For debug, comment out exception above and uncomment this:
            #print "Warning: Pauli-product vector has non-zero imaginary part (%g)!" % \
            #    _np.linalg.norm(_np.imag(pp))
            #return pp
        return _np.real(pp)


    else: raise ValueError("Invalid dimension of object - must be 1 or 2, i.e. a vector or matrix")


def basisChg_PauliProdToStd(mxInPauliProdBasis, dimOrBlockDims=None):
    """ 
    Convert a gate matrix in the Pauli-product basis of a
    density matrix space to the Standard basis (of the same space).

    Parameters
    ----------
    mxInPauliProdBasis : numpy array
        The gate matrix, (a 2D square array)

    dimOrBlockDims : int or list of ints, optional
        Structure of the density-matrix space. If None, then assume
        mxInPauliProdBasis operates on a single-block density matrix space,
        i.e. on K x K density matrices with K == sqrt( mxInPauliProdBasis.shape[0] ).

    Returns
    -------
    numpy array
        The given gate matrix converted to the Standard basis.
        Array size is the same as mxInPauliProdBasis.
    """

    if dimOrBlockDims is None: 
        dimOrBlockDims = int(round(_np.sqrt(mxInPauliProdBasis.shape[0])))
        assert( dimOrBlockDims**2 == mxInPauliProdBasis.shape[0] )

    ppToStd = GetPauliProdToStdBasisTransformMatrix(dimOrBlockDims)
    stdToPP = _np.linalg.inv(ppToStd)

    if len(mxInPauliProdBasis.shape) == 2 and mxInPauliProdBasis.shape[0] == mxInPauliProdBasis.shape[1]:
        return _np.dot( ppToStd, _np.dot( mxInPauliProdBasis, stdToPP ) )

    elif len(mxInPauliProdBasis.shape) == 1 or \
         (len(mxInPauliProdBasis.shape) == 2 and mxInPauliProdBasis.shape[1] == 1): # (really vecInPauilProdBasis)
        return _np.dot( ppToStd, mxInPauliProdBasis )

    else: raise ValueError("Invalid dimension of object - must be 1 or 2, i.e. a vector or matrix")


def basisChg_GellMannToPauliProd(mxInGellMannBasis, dimOrBlockDims=None):
    """ 
    Convert a gate matrix in the Gell-Mann basis of a
    density matrix space to the Pauil-product basis (of the same space).

    Parameters
    ----------
    mxInGellMannBasis : numpy array
        The gate matrix, (a 2D square array)

    dimOrBlockDims : int or list of ints, optional
        Structure of the density-matrix space. If None, then assume
        mxInPauliProdBasis operates on a single-block density matrix space,
        i.e. on K x K density matrices with K == sqrt( mxInGellMannBasis.shape[0] ).

    Returns
    -------
    numpy array
        The given gate matrix converted to the Pauli-product basis.
        Array size is the same as mxInGellMannBasis.
    """
    return basisChg_StdToPauliProd(basisChg_GellMannToStd(mxInGellMannBasis, dimOrBlockDims), dimOrBlockDims)

def basisChg_PauliProdtoGellMann(mxInPauliProdBasis, dimOrBlockDims=None):
    """ 
    Convert a gate matrix in the Pauli-product basis of a
    density matrix space to the Gell-Mann basis (of the same space).

    Parameters
    ----------
    mxInPauliProdBasis : numpy array
        The gate matrix, (a 2D square array)

    dimOrBlockDims : int or list of ints, optional
        Structure of the density-matrix space. If None, then assume
        mxInPauliProdBasis operates on a single-block density matrix space,
        i.e. on K x K density matrices with K == sqrt( mxInPauliProdBasis.shape[0] ).

    Returns
    -------
    numpy array
        The given gate matrix converted to the Gell-Mann basis.
        Array size is the same as mxInPauliProdBasis.
    """
    return basisChg_StdToGellMann(basisChg_PauliProdToStd(mxInPauliProdBasis, dimOrBlockDims), dimOrBlockDims)






#TODO: maybe make these more general than for 1 or 2 qubits??
#############################################################################

def stateToPauliDensityVec(state_vec):
    """
    Convert a single qubit state vector into a density matrix.

    Parameters
    ----------
    state_vec : list or tuple
       State vector in the sigma-z basis, len(state_vec) == 2

    Returns
    -------
    numpy array
        The 2x2 density matrix of the pure state given by state_vec, given
        as a 4x1 column vector in the Pauli basis.
    """
    assert( len(state_vec) == 2 )  
    st_vec = _np.array( [ [state_vec[0]], [state_vec[1]] ] )
    dm_mx = _np.kron( _np.conjugate(_np.transpose(st_vec)), st_vec ) #density matrix in sigmaz basis
    return matrixInStdBasisToPauliProdVector(dm_mx)


def stateUnitaryToPauliDensityMxOp(U):
    """
    Get the linear operator on (vectorized) density
    matrices corresponding to a 1-qubit unitary 
    operator on states.

    Parameters
    ----------
    U : numpy array
        A 2x2 array giving the action of the unitary
        on a state in the sigma-z basis.

    Returns
    -------
    numpy array
        The operator on density matrices that have been
        vectorized as length-4 vectors in the Pauli basis.
        Array has shape == (4,4).
    """
    assert( U.shape == (2,2) )
    op_mx = _np.empty( (4,4) ) #, 'complex' )
    Udag = _np.conjugate(_np.transpose(U))

    sigmaVec = GetPauliProdMatrices(2)

    for i in (0,1,2,3):
        for j in (0,1,2,3):
            op_mx[i,j] = _np.real(_MOps.trace(_np.dot(sigmaVec[i],_np.dot(U,_np.dot(sigmaVec[j],Udag)))))
        # in clearer notation: op_mx[i,j] = _MOps.trace( sigma[i] * U * sigma[j] * Udag )
    return op_mx

# single qubit density matrix in 2-qubit pauli basis (16x16 matrix)
# U must be a 4x4 matrix
def stateUnitaryToPauliDensityMxOp_2Q(U):
    """
    Get the linear operator on (vectorized) density
    matrices corresponding to a 2-qubit unitary 
    operator on states.

    Parameters
    ----------
    U : numpy array
        A 4x4 array giving the action of the unitary
        on a state in the sigma-z basis.

    Returns
    -------
    numpy array
        The operator on density matrices that have been
        vectorized as length-16 vectors in the Pauli-product basis.
        Array has shape == (16,16).
    """

    assert( U.shape == (4,4) )
    op_mx = _np.empty( (16,16), 'd') #, 'complex' )
    Udag = _np.conjugate(_np.transpose(U))

    sigmaVec_2Q = GetPauliProdMatrices(4)

    for i in range(16):
        for j in range(16):
            op_mx[i,j] = _np.real(_MOps.trace(_np.dot(sigmaVec_2Q[i],_np.dot(U,_np.dot(sigmaVec_2Q[j],Udag)))))
        # in clearer notation: op_mx[i,j] = trace( sigma[i] * U * sigma[j] * Udag )
    return op_mx


def pauliProdVectorToMatrixInStdBasis(v):
    """
    Convert a vector in the Pauli basis to a matrix
     in the standard basis.

    Parameters
    ----------
    v : numpy array
        The vector, length 4 (1Q) or 16 (2Q)

    Returns
    -------
    numpy array
        The matrix, shape (2,2) or (4,4) respectively.
    """

    # nQubits = _np.log2(len(v)) / 2  ( n qubits = 2^n x 2^n mx ; len(v) = 2^2n -> n = log2(len(v))/2 )
    dim = int(_np.sqrt( len(v) )) # len(v) = dim^2, where dim is matrix dimension of Pauli-prod mxs
    ppMxs    = GetPauliProdMatrices(dim)

    ret = _np.zeros( (dim,dim), 'complex' )
    for i,ppMx in enumerate(ppMxs):
        ret += v[i]*ppMx
    return ret


def gellMannVectorToMatrixInStdBasis(v):
    """
    Convert a vector in the Gell-Mann basis to a matrix
     in the standard basis.

    Parameters
    ----------
    v : numpy array
        The vector (length must be a perfect square, e.g. 4, 9, 16, ...)

    Returns
    -------
    numpy array
        The matrix, shape (2,2) or (4,4) respectively.
    """

    dim = int(_np.sqrt( len(v) )) # len(v) = dim^2, where dim is matrix dimension of Pauli-prod mxs
    gmMxs = GetNormalizedGellMannMatrices(dim)

    ret = _np.zeros( (dim,dim), 'complex' )
    for i,gmMx in enumerate(gmMxs):
        ret += v[i]*gmMx
    return ret


def matrixInStdBasisToPauliProdVector(m):
    """
    Convert a matrix in the standard basis to
     a vector in the Pauli basis.

    Parameters
    ----------
    m : numpy array
        The matrix, shape 2x2 (1Q) or 4x4 (2Q)

    Returns
    -------
    numpy array
        The vector, length 4 or 16 respectively.
    """

    assert(len(m.shape) == 2 and m.shape[0] == m.shape[1])
    dim = m.shape[0]
    ppMxs = GetPauliProdMatrices(dim)

    v = _np.empty((dim**2,1))
    for i,ppMx in enumerate(ppMxs):
        v[i,0] = _np.real(_MOps.trace(_np.dot(ppMx,m)))

    return v

def matrixInStdBasisToGellMannVector(m):
    """
    Convert a matrix in the standard basis to
     a vector in the Gell-Mann basis.

    Parameters
    ----------
    m : numpy array
        The matrix, must be square.

    Returns
    -------
    numpy array
        The vector, length == number of elements in m
    """

    assert(len(m.shape) == 2 and m.shape[0] == m.shape[1])
    dim = m.shape[0]
    gmMxs = GetNormalizedGellMannMatrices(dim)

    v = _np.empty((dim**2,1))
    for i,gmMx in enumerate(gmMxs):
        v[i,0] = _np.real(_MOps.trace(_np.dot(gmMx,m)))

    return v