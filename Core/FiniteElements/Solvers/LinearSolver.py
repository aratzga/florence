from time import time
import numpy as np
import numpy.linalg as la
# from scipy.sparse.linalg import spsolve, cg, cgs, bicg, bicgstab, gmres, lgmres, minres
from scipy.sparse.linalg import spsolve, bicgstab 

from Core.FiniteElements.Assembly import *
from Core.FiniteElements.PostProcess import * 
from Core.FiniteElements.ApplyDirichletBoundaryConditions import *

def LinearSolver(Increment,MainData,K,F,M,NodalForces,Residual,ResidualNorm,nmesh,TotalDisp,Eulerx,
			columns_in,columns_out,AppliedDirichletInc):

	# GET THE REDUCED ELEMENTAL MATRICES 
	# print Residual + F 
	# K_b, F_b, _, _ = ApplyLinearDirichletBoundaryConditions(K,F,columns_in,columns_out,AppliedDirichletInc,MainData.Analysis,M)
	# print np.linalg.norm(Residual)
	K_b, F_b= ApplyLinearDirichletBoundaryConditions(K,Residual,columns_in,columns_out,AppliedDirichletInc,MainData.Analysis,M)[:2]

	
	# SOLVE THE SYSTEM
	if MainData.solve.type == 'direct':
		# CHECK FOR THE CONDITION NUMBER OF THE SYSTEM
		# MainData.solve.condA = np.linalg.cond(K_b.todense()) # REMOVE THIS
		sol = spsolve(K_b,-F_b)
	else:
		sol = bicgstab(K_b,-F_b,tol=MainData.solve.tol)[0]
	
	# GET THE TOTAL SOLUTION AND ITS COMPONENTS SUCH AS UX, UY, UZ, PHI ETC
	dU = PostProcess().TotalComponentSol(MainData,sol,columns_in,columns_out,AppliedDirichletInc,0,F.shape[0]) 

	# UPDATE THE FIELDS
	TotalDisp[:,:,Increment] += dU

	if MainData.Prestress:
		# UPDATE THE GEOMETRY
		Eulerx = nmesh.points + TotalDisp[:,:MainData.ndim,Increment]			
		# RE-ASSEMBLE - COMPUTE INTERNAL TRACTION FORCES (BE CAREFUL ABOUT THE -1 INDEX IN HERE)
		K, TractionForces = Assembly(MainData,nmesh,Eulerx,TotalDisp[:,MainData.nvar-1,Increment].reshape(TotalDisp.shape[0],1))[:2]
		# print np.linalg.norm(TractionForces)
		# FIND THE RESIDUAL
		Residual[columns_in] = TractionForces[columns_in] - NodalForces[columns_in]

	print 'Load increment', Increment, 'for incrementally linearised elastic problem'

	return TotalDisp