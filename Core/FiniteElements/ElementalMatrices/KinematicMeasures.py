import numpy as np


class KinematicMeasures(object):
	"""docstring for KinematicMeasures"""
	def __init__(self, F):
		super(KinematicMeasures, self).__init__()
		self.F = F

	def Compute(self,AnalysisType):

		# F = self.F
		self.J = np.linalg.det(self.F)
		self.I = np.eye(self.F.shape[0],self.F.shape[0],dtype=np.float64)

		self.b = np.dot(self.F,self.F.T)

		if AnalysisType=='Nonlinear':
			# self.C = np.dot(F.T,F)
			# self.b = np.dot(F,F.T)
			# self.E = 0.5*(self.C-self.I)
			# self.e = 0.5*(self.I-np.linalg.inv(self.b)) 

			# self.Gradu = self.F - self.I
			# self.strain = 0.5*(self.Gradu + self.Gradu.T)
			

			# Polyconvex measures
			self.H = self.J*np.linalg.inv(self.F).T
			# self.G = self.H.T*self.H
		elif AnalysisType=='Linear':
			# Linearised kinematics:
			# Material Gradient of Displacement
			self.Gradu = self.F - self.I
			# self.Gradu = self.I - np.linalg.inv(self.F)
			# Small strain tensor is defined as the linearised version of Green-Lagrange strain tensor
			self.strain = 0.5*(self.Gradu + self.Gradu.T)

		return self


