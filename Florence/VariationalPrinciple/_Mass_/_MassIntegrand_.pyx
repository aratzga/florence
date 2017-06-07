#cython: profile=False
#cython: infer_types=True
#cython: boundscheck=False
#cython: wraparound=False
#cython: nonecheck=False

import numpy as np
cimport numpy as np

ctypedef double Real

cdef extern from "_MassIntegrand_.h":
    
    inline void _MassIntegrand_Filler_(Real *mass,
        const Real* bases,
        const Real* detJ,
        int ngauss, 
        int noderpelem, 
        int ndim, 
        int nvar,
        Real rho) nogil


def __MassIntegrand__(Real rho, 
    np.ndarray[Real, ndim=2, mode='c'] bases, 
    np.ndarray[Real, ndim=1] detJ, 
    int ndim, int nvar):

    cdef int ngauss = detJ.shape[0]
    cdef int nodeperelem = bases.shape[0]
    cdef int local_size = nvar*nodeperelem

    cdef np.ndarray[Real, ndim=2, mode='c'] mass = np.zeros((local_size,
        local_size),dtype=np.float64)

    _MassIntegrand_Filler_(&mass[0,0],
        &bases[0,0], 
        &detJ[0],
        ngauss,
        nodeperelem,
        ndim,
        nvar,
        rho)

    return mass