import numpy as np
from Core.Supplementary.Tensors.Tensors import *

#####################################################################################################
										# NeoHookean Material Model 2
#####################################################################################################


class NeoHookean_2(object):
	"""Material model for neo-Hookean with the following internal energy:

		W(C) = mu/2*(C:I)-mu*lnJ+lamba/2*(J-1)**2

		"""
	def __init__(self, ndim):
		super(NeoHookean_2, self).__init__()
		self.ndim = ndim

	def Get(self):
		self.nvar = self.ndim
		self.modelname = 'NeoHookean_2'
		return self.nvar, self.modelname

	def Hessian(self,MaterialArgs,ndim,StrainTensors,ElectricFieldx=0,elem=0,gcounter=0):
		mu = MaterialArgs.mu
		lamb = MaterialArgs.lamb
		I = StrainTensors['I']
		detF = StrainTensors['J'][gcounter]

		mu2 = mu/detF- lamb*(detF-1.0)
		lamb2 = lamb*(2*detF-1.0) 

		# d = np.einsum
		# C = lamb2*d('ij,kl',I,I)+mu2*(d('ik,jl',I,I) + d('il,jk',I,I))
		# C_Voigt = Voigt( C ,1)
		C_Voigt = lamb2*MaterialArgs.IijIkl+mu2*MaterialArgs.IikIjl

		MaterialArgs.H_VoigtSize = C_Voigt.shape[0]

		return C_Voigt

	def CauchyStress(self,MaterialArgs,StrainTensors,ElectricFieldx,elem=0,gcounter=0):

		I = StrainTensors['I']
		J = StrainTensors['J'][gcounter]
		b = StrainTensors['b'][gcounter]

		mu = MaterialArgs.mu
		lamb = MaterialArgs.lamb


		# if elem==0 and gcounter==0:
			# print 1.0*mu/J*b + (lamb*(J-1.0)-mu/J)*I
			
		return 1.0*mu/J*b + (lamb*(J-1.0)-mu/J)*I

