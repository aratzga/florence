from time import time
import numpy as np
from Florence.FiniteElements.Solvers.NewtonRaphsonStatic import *


# def StaticSolver(MainData,LoadIncrement,K,DirichletForces,NeumannForces,
#     NodalForces,Residual,ResidualNorm,mesh,TotalDisp,Eulerx, material, boundary_condition): #

# def StaticSolver(MainData,LoadIncrement,K,NodalForces,Residual,ResidualNorm,
    # mesh,TotalDisp,Eulerx, material, boundary_condition):

def StaticSolver(function_spaces, formulation, solver, fem_solver, LoadIncrement,K,
            DirichletForces,NeumannForces,NodalForces,Residual,
            ResidualNorm,mesh,TotalDisp,Eulerx,material, boundary_condition):
    
    LoadFactor = 1./LoadIncrement
    AppliedDirichletInc = np.zeros(boundary_condition.applied_dirichlet.shape[0],dtype=np.float32)
    
    for Increment in range(LoadIncrement):

        DeltaF = LoadFactor*NeumannForces
        # DeltaF = LoadFactor*boundary_condition.neumann_forces
        NodalForces += DeltaF
        # RESIDUAL FORCES CONTAIN CONTRIBUTION FROM BOTH NEUMANN AND DIRICHLET
        Residual -= (DeltaF + LoadFactor*DirichletForces)
        # Residual -= (DeltaF + LoadFactor*boundary_condition.dirichlet_forces)
        AppliedDirichletInc += LoadFactor*boundary_condition.applied_dirichlet


        # CALL THE LINEAR/NONLINEAR SOLVER
        if fem_solver.analysis_nature == 'nonlinear':
            t_increment = time()

            # LET NORM OF THE FIRST RESIDUAL BE THE NORM WITH RESPECT TO WHICH WE
            # HAVE TO CHECK THE CONVERGENCE OF NEWTON RAPHSON. TYPICALLY THIS IS 
            # NORM OF NODAL FORCES
            if Increment==0:
                fem_solver.NormForces = np.linalg.norm(Residual[boundary_condition.columns_out])

            TotalDisp = NewtonRaphson(function_spaces, formulation, solver, fem_solver, 
                Increment,K,NodalForces,Residual,ResidualNorm,mesh,TotalDisp,Eulerx,
                material,boundary_condition,AppliedDirichletInc)


            print '\nFinished Load increment', Increment, 'in', time()-t_increment, 'sec'
            try:
                print 'Norm of Residual is', np.abs(la.norm(Residual[boundary_condition.columns_in])/fem_solver.NormForces), '\n'
            except RuntimeWarning:
                print("Invalid value encountered in norm of Newton-Raphson residual")

            # STORE THE INFORMATION IF NEWTON-RAPHSON FAILS
            # if MainData.AssemblyParameters.FailedToConverge == True:
            if fem_solver.newton_raphson_failed_to_converge:
                solver.condA = np.NAN
                solver.scaledA = np.NAN
                solver.scaledAFF = np.NAN
                solver.scaledAHH = np.NAN
                break

    return TotalDisp