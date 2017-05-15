import numpy as np
cimport numpy as np
from scipy.sparse import csr_matrix, csc_matrix

ctypedef long long Integer
ctypedef unsigned long long UInteger
ctypedef double Real


cdef extern from "_LowLevelAssemblyDF_.h" nogil:
    void _GlobalAssemblyDF_(const Real *points, 
                            const UInteger* elements, 
                            const Real* Eulerx,
                            const Real* Eulerp,
                            const Real* Jm,
                            const Real* AllGauss,
                            Integer ndim,
                            Integer nvar,  
                            Integer ngauss, 
                            Integer nelem, 
                            Integer nodeperelem,
                            Integer nnode,
                            Integer H_VoigtSize,
                            Integer requires_geometry_update, 
                            Integer* local_rows_stiff,
                            Integer* local_cols_stiff,
                            int *I_stiff,
                            int *J_stiff,
                            Real *V_stiff,
                            Real *T,
                            Integer is_dynamic,
                            Integer* local_rows_mass,
                            Integer* local_cols_mass,
                            int *I_mass,
                            int *J_mass,
                            Real *V_mass,
                            Real mu,
                            Real mu1,
                            Real mu2,
                            Real mu3,
                            Real mue,
                            Real lamb,
                            Real eps_1,
                            Real eps_2,
                            Real eps_3,
                            Real eps_e,
                            const Real *anisotropic_orientations
                            )


def _LowLevelAssemblyDF_(fem_solver, function_space, formulation, mesh, material, Real[:,::1] Eulerx, Real[:] Eulerp):

    # GET VARIABLES FOR DISPATCHING TO C
    cdef Integer ndim                       = formulation.ndim
    cdef Integer nvar                       = formulation.nvar
    cdef Integer ngauss                     = function_space.AllGauss.shape[0]
    cdef Integer nelem                      = mesh.nelem
    cdef Integer nodeperelem                = mesh.elements.shape[1]
    cdef Integer nnode                      = mesh.points.shape[0]
    cdef Integer H_VoigtSize                = material.H_VoigtSize

    cdef np.ndarray[UInteger,ndim=2, mode='c'] elements = mesh.elements
    cdef np.ndarray[Real,ndim=2, mode='c'] points       = mesh.points
    cdef np.ndarray[Real,ndim=3, mode='c'] Jm           = function_space.Jm
    cdef np.ndarray[Real,ndim=1, mode='c'] AllGauss     = function_space.AllGauss.flatten()

    cdef Integer requires_geometry_update               = fem_solver.requires_geometry_update
    cdef Integer is_dynamic                             = not fem_solver.analysis_type

    cdef np.ndarray[Integer,ndim=1,mode='c'] local_rows_stiffness   = formulation.local_rows
    cdef np.ndarray[Integer,ndim=1,mode='c'] local_cols_stiffness   = formulation.local_columns

    cdef np.ndarray[Integer,ndim=1,mode='c'] local_rows_mass        = formulation.local_rows_mass
    cdef np.ndarray[Integer,ndim=1,mode='c'] local_cols_mass        = formulation.local_columns_mass

    # ALLOCATE VECTORS FOR SPARSE ASSEMBLY OF STIFFNESS MATRIX - CHANGE TYPES TO INT64 FOR DoF > 1e09
    cdef np.ndarray[int,ndim=1,mode='c'] I_stiffness    = np.zeros(int((nvar*nodeperelem)**2*nelem),dtype=np.int32)
    cdef np.ndarray[int,ndim=1,mode='c'] J_stiffness    = np.zeros(int((nvar*nodeperelem)**2*nelem),dtype=np.int32)
    cdef np.ndarray[Real,ndim=1,mode='c'] V_stiffness   = np.zeros(int((nvar*nodeperelem)**2*nelem),dtype=np.float64)

    cdef np.ndarray[int,ndim=1,mode='c'] I_mass         = np.zeros(1,np.int32)
    cdef np.ndarray[int,ndim=1,mode='c'] J_mass         = np.zeros(1,np.int32)
    cdef np.ndarray[Real,ndim=1,mode='c'] V_mass        = np.zeros(1,np.float64)

    if is_dynamic:
        I_mass          = np.zeros(int((nvar*nodeperelem)**2*nelem),dtype=np.int32)
        J_mass          = np.zeros(int((nvar*nodeperelem)**2*nelem),dtype=np.int32)
        V_mass          = np.zeros(int((nvar*nodeperelem)**2*nelem),dtype=np.float64)


    cdef np.ndarray[Real,ndim=1,mode='c'] T = np.zeros(mesh.points.shape[0]*nvar,np.float64)

    cdef np.ndarray[Real,ndim=2,mode='c'] anisotropic_orientations = np.zeros((1,1),np.float64)
    if material.is_transversely_isotropic:
        anisotropic_orientations = material.anisotropic_orientations

    cdef Real mu=0.,mu1=0.,mu2=0.,mu3=0.,mue=0.,lamb=0.,eps_1=0.,eps_2=0., eps_3=0., eps_e=0.

    mu1, mu2, lamb = material.mu1, material.mu2, material.lamb


    _GlobalAssemblyDF_(     &points[0,0],
                            &elements[0,0],
                            &Eulerx[0,0],
                            &Eulerp[0],
                            &Jm[0,0,0],
                            &AllGauss[0],
                            ndim,
                            nvar,
                            ngauss,
                            nelem,
                            nodeperelem,
                            nnode,
                            H_VoigtSize,
                            requires_geometry_update,
                            &local_rows_stiffness[0],
                            &local_cols_stiffness[0],
                            &I_stiffness[0],
                            &J_stiffness[0],
                            &V_stiffness[0],
                            &T[0],
                            is_dynamic,
                            &local_rows_mass[0],
                            &local_cols_mass[0],
                            &I_mass[0],
                            &J_mass[0],
                            &V_mass[0],
                            mu,
                            mu1,
                            mu2,
                            mu3,
                            mue,
                            lamb,
                            eps_1,
                            eps_2,
                            eps_3,
                            eps_e,
                            &anisotropic_orientations[0,0]
                            )


    stiffness = csc_matrix((V_stiffness,(I_stiffness,J_stiffness)),
        shape=((nvar*mesh.points.shape[0],nvar*mesh.points.shape[0])),dtype=np.float64)

    F, mass = [], []

    if is_dynamic:
            mass = csc_matrix((V_mass,(I_mass,J_mass)),
                shape=((nvar*mesh.points.shape[0],nvar*mesh.points.shape[0])),dtype=np.float64)

    return stiffness, T, F, mass
