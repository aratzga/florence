import numpy as np
<<<<<<< HEAD
from Florence.Tensor import trace

#####################################################################################################
                                        # NeoHookean Material Model 2
#####################################################################################################


class NeoHookean_1(object):
=======
from .MaterialBase import Material
from Florence.Tensor import trace


class NeoHookean_1(Material):
>>>>>>> upstream/master
    """NeoHookean model with the following energy

        W(C) = u/2*C:I -u*J + lambda *(J-1)**2

        """
<<<<<<< HEAD
    def __init__(self, ndim, MaterialArgs=None):
        super(NeoHookean_1, self).__init__()
        self.ndim = ndim
        self.nvar = self.ndim
=======
    def __init__(self, ndim, **kwargs):
        mtype = type(self).__name__
        super(NeoHookean_1, self).__init__(mtype, ndim, **kwargs)
>>>>>>> upstream/master

        self.is_transversely_isotropic = False
        self.energy_type = "internal_energy"
        self.nature = "nonlinear"
<<<<<<< HEAD
        self.fields = "mechanics"
=======
        self.fields = "mechanics"  
>>>>>>> upstream/master

        if self.ndim==3:
            self.H_VoigtSize = 6
        elif self.ndim==2:
            self.H_VoigtSize = 3

        # LOW LEVEL DISPATCHER
<<<<<<< HEAD
        self.has_low_level_dispatcher = False 


    def Hessian(self,MaterialArgs,StrainTensors,ElectricFieldx=0,elem=0,gcounter=0):
        mu = MaterialArgs.mu
        lamb = MaterialArgs.lamb
=======
        self.has_low_level_dispatcher = False


    def Hessian(self,StrainTensors,ElectricFieldx=0,elem=0,gcounter=0):
        mu = self.mu
        lamb = self.lamb
>>>>>>> upstream/master
        I = StrainTensors['I']
        detF = StrainTensors['J'][gcounter]

        mu2 = mu - lamb*(detF-1.0)
        lamb2 = lamb*(2*detF-1.0) - mu

<<<<<<< HEAD

        C_Voigt = lamb2*MaterialArgs.vIijIkl+mu2*MaterialArgs.vIikIjl

        MaterialArgs.H_VoigtSize = C_Voigt.shape[0]
=======
        C_Voigt = lamb2*self.vIijIkl+mu2*self.vIikIjl

        self.H_VoigtSize = C_Voigt.shape[0]
>>>>>>> upstream/master

        return C_Voigt


<<<<<<< HEAD
    def CauchyStress(self,MaterialArgs,StrainTensors,ElectricFieldx,elem=0,gcounter=0):
=======
    def CauchyStress(self,StrainTensors,ElectricFieldx,elem=0,gcounter=0):
>>>>>>> upstream/master

        I = StrainTensors['I']
        J = StrainTensors['J'][gcounter]
        b = StrainTensors['b'][gcounter]

<<<<<<< HEAD
        mu = MaterialArgs.mu
        lamb = MaterialArgs.lamb
=======
        mu = self.mu
        lamb = self.lamb
>>>>>>> upstream/master

        return (lamb*(J-1.0)-mu)*I+1.0*mu/J*b


