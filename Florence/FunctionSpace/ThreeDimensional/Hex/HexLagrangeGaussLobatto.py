import numpy as np
from Florence.FunctionSpace.OneDimensional import Line as OneD
from Florence.MeshGeneration.NodeArrangement import NodeArrangementHex

def LagrangeGaussLobatto(C,zeta,eta,beta,arrange=1):
    """This routine computes stable higher order Lagrangian bases with Gauss-Lobatto-Legendre points
        Refer to: Spencer's Spectral hp elements for details"""

    Neta = np.zeros((C+2,1));   Nzeta = np.zeros((C+2,1)); Nbeta = np.zeros((C+2,1))

    Nzeta[:,0] = OneD.LagrangeGaussLobatto(C,zeta)[0]
    Neta[:,0] =  OneD.LagrangeGaussLobatto(C,eta)[0]
    Nbeta[:,0] =  OneD.LagrangeGaussLobatto(C,beta)[0]


    if arrange==1:
        # Bases = np.zeros(((C+2)**3,1))
        # # Arrange in counterclockwise
        # zeta_index, eta_index = GetCounterClockwiseIndices(C)
        # TBases = np.dot(Nzeta,Neta.T)
        # counter=0
        # for j in range(0,C+2):
        #     for i in range(0,(C+2)**2):
        #         Bases[counter] = Nbeta[j]*TBases[zeta_index[i],eta_index[i]]
        #         counter+=1

        node_arranger = NodeArrangementHex(C)[2]
        Bases = np.einsum('i,j,k', Nbeta[:,0], Neta[:,0], Nzeta[:,0]).flatten()
        Bases = Bases[node_arranger]
        Bases = Bases[:,None]

    elif arrange==0:
        Bases = np.zeros((C+2,C+2,C+2))
        for i in range(0,C+2):
            Bases[:,:,i] = Nbeta[i]*np.dot(Nzeta,Neta.T)
        Bases = Bases.reshape((C+2)**3,1)

    return Bases

def GradLagrangeGaussLobatto(C,zeta,eta,beta,arrange=1):
    """This routine computes stable higher order Lagrangian bases with Gauss-Lobatto-Legendre points
        Refer to: Spencer's Spectral hp elements for details"""

    gBases = np.zeros(((C+2)**3,3))
    Nzeta = np.zeros((C+2,1));  Neta = np.zeros((C+2,1));   Nbeta = np.zeros((C+2,1))
    gNzeta = np.zeros((C+2,1)); gNeta = np.zeros((C+2,1));  gNbeta = np.zeros((C+2,1))
    # Compute each from one-dimensional bases
    Nzeta[:,0] = OneD.LagrangeGaussLobatto(C,zeta)[0]
    Neta[:,0] = OneD.LagrangeGaussLobatto(C,eta)[0]
    Nbeta[:,0] = OneD.LagrangeGaussLobatto(C,beta)[0]
    gNzeta[:,0] = OneD.LagrangeGaussLobatto(C,zeta)[1]
    gNeta[:,0] = OneD.LagrangeGaussLobatto(C,eta)[1]
    gNbeta[:,0] = OneD.LagrangeGaussLobatto(C,beta)[1]

    # Ternsorial product
    if arrange==1:
        # # Arrange in counterclockwise
        # zeta_index, eta_index = GetCounterClockwiseIndices(C)
        # gBases1 = np.dot(gNzeta,Neta.T)
        # gBases2 = np.dot(Nzeta,gNeta.T)
        # gBases3 = np.dot(Nzeta,Neta.T)
        # counter=0
        # for j in range(0,C+2):
        #     for i in range(0,(C+2)**2):
        #         gBases[counter,0] = Nbeta[j]*gBases1[zeta_index[i],eta_index[i]]
        #         gBases[counter,1] = Nbeta[j]*gBases2[zeta_index[i],eta_index[i]]
        #         gBases[counter,2] = gNbeta[j]*gBases3[zeta_index[i],eta_index[i]]
                # counter+=1

        node_arranger = NodeArrangementHex(C)[2]
        # g0 = np.einsum('i,j,k', gNbeta[:,0], Neta[:,0], Nzeta[:,0]).flatten()
        # g1 = np.einsum('i,j,k', Nbeta[:,0], gNeta[:,0], Nzeta[:,0]).flatten()
        # g2 = np.einsum('i,j,k', Nbeta[:,0], Neta[:,0], gNzeta[:,0]).flatten()
        g0 = np.einsum('i,j,k', Nbeta[:,0], Neta[:,0], gNzeta[:,0]).flatten()
        g1 = np.einsum('i,j,k', Nbeta[:,0], gNeta[:,0], Nzeta[:,0]).flatten()
        g2 = np.einsum('i,j,k', gNbeta[:,0], Neta[:,0], Nzeta[:,0]).flatten()
        gBases[:,0] = g0[node_arranger]
        gBases[:,1] = g1[node_arranger]
        gBases[:,2] = g2[node_arranger]

    elif arrange==0:
        gBases1 = np.zeros((C+2,C+2,C+2)); gBases2 = np.zeros((C+2,C+2,C+2)); gBases3 = np.zeros((C+2,C+2,C+2))
        for i in range(0,C+2):
            gBases1[:,:,i] = Nbeta[i]*np.dot(gNzeta,Neta.T)
            gBases2[:,:,i] = Nbeta[i]*np.dot(Nzeta,gNeta.T)
            gBases3[:,:,i] = gNbeta[i]*np.dot(Nzeta,Neta.T)
        gBases1 = gBases1.reshape((C+2)**3,1)
        gBases2 = gBases2.reshape((C+2)**3,1)
        gBases3 = gBases3.reshape((C+2)**3,1)
        gBases[:,0]=gBases1
        gBases[:,1]=gBases2
        gBases[:,2]=gBases3


    return gBases