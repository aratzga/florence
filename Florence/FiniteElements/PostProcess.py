import numpy as np 
import numpy.linalg as la
import gc
from warnings import warn
from Florence import QuadratureRule, FunctionSpace
from Florence.Base import JacobianError, IllConditionedError

# import Florence.FunctionSpace.TwoDimensional.Quad.QuadLagrangeGaussLobatto as TwoD
# import Florence.FunctionSpace.ThreeDimensional.Hexahedral.HexLagrangeGaussLobatto as ThreeD
from Florence.FunctionSpace import QuadLagrangeGaussLobatto as TwoD
from Florence.FunctionSpace import HexLagrangeGaussLobatto as ThreeD
# Modal Bases
# import Core.FunctionSpace.TwoDimensional.Tri.hpModal as Tri 
# import Core.FunctionSpace.ThreeDimensional.Tetrahedral.hpModal as Tet 
# Nodal Bases
from Florence.FunctionSpace import Tri
from Florence.FunctionSpace import Tet

from ElementalMatrices.KinematicMeasures import *
from Florence.MeshGeneration import vtk_writer

class PostProcess(object):
    """Post-process class for finite element solvers"""

    def __init__(self,ndim,nvar):

        self.domain_bases = None
        self.postdomain_bases = None
        self.boundary_bases = None
        self.ndim = ndim
        self.nvar = nvar
        self.analysis_type = None
        self.analysis_nature = None
        self.material_type = None

        self.is_scaledjacobian_computed = False
        self.is_material_anisotropic = False
        self.directions = None

        self.mesh = None
        self.sol = None
        self.recovered_fields = None


    def SetBases(self,domain=None,postdomain=None,boundary=None):
        """Sets bases for all integration points for 'domain', 'postdomain' or 'boundary'
        """

        if domain is None and postdomain is None and boundary is None:
            warn("Nothing to be set") 

        self.domain_bases = domain
        self.postdomain_bases = postdomain
        self.boundary_bases = boundary

    def SetMesh(self,mesh):
        """Set initial (undeformed) mesh"""
        self.mesh = mesh

    def SetSolution(self,sol):
        self.sol = sol

    def SetAnalysis(self,analysis_type=None, analysis_nature=None):
        self.analysis_type = analysis_type
        self.analysis_nature = analysis_nature

    def SetFormulation(self,formulation):
        self.formulation = formulation

    def SetMaterial(self,material):
        self.material = material

    def SetFEMSolver(self,fem_solver):
        self.fem_solver = fem_solver

    def SetAnisotropicOrientations(self,Directions):
        self.directions = Directions


    def TotalComponentSol(self, sol, ColumnsIn, ColumnsOut, AppliedDirichletInc, Iter, fsize):

        nvar = self.nvar
        ndim = self.ndim
        TotalSol = np.zeros((fsize,1))

        # GET TOTAL SOLUTION
        if self.analysis_nature == 'nonlinear':
            if self.analysis_type =='static':
                TotalSol[ColumnsIn,0] = sol
                if Iter==0:
                    TotalSol[ColumnsOut,0] = AppliedDirichletInc
            if self.analysis_type !='static':
                TotalSol = np.copy(sol)
                TotalSol[ColumnsOut,0] = AppliedDirichletInc

        elif self.analysis_nature == 'linear':
                TotalSol[ColumnsIn,0] = sol
                TotalSol[ColumnsOut,0] = AppliedDirichletInc
                
        # RE-ORDER SOLUTION COMPONENTS
        dU = TotalSol.reshape(TotalSol.shape[0]/nvar,nvar)

        return dU


    def StressRecovery(self):

        if self.mesh is None:
            raise ValueError("Mesh not set for post-processing")
        if self.sol is None:
            raise ValueError("Solution not set for post-processing")

        mesh = self.mesh

        # GET THE UNDERLYING LINEAR MESH
        # lmesh = mesh.GetLinearMesh()
        C = mesh.InferPolynomialDegree() - 1
        ndim = mesh.InferSpatialDimension()


         # GET QUADRATURE
        norder = 2*C
        if norder == 0:
            norder=1
        Domain = FunctionSpace(mesh, p=C+1, evaluate_at_nodes=True)
        w = Domain.AllGauss[:,0]

        fem_solver = self.fem_solver
        formulation = self.formulation
        material = self.material


        elements = mesh.elements
        points = mesh.points
        nelem = elements.shape[0]; npoint = points.shape[0]
        nodeperelem = elements.shape[1]
        LoadIncrement = fem_solver.number_of_load_increments
        requires_geometry_update = fem_solver.requires_geometry_update
        TotalDisp = self.sol[:mesh.nnode,:]


        F = np.zeros((nelem,nodeperelem,ndim,ndim))
        strain = np.zeros((nelem,nodeperelem,ndim,ndim))
        ElectricFieldx = np.zeros((nelem,nodeperelem,ndim,1))
        CauchyStressTensor = np.zeros((nelem,nodeperelem,ndim,ndim))
        ElectricDisplacementx = np.zeros((nelem,nodeperelem,ndim,1))


        det = np.linalg.det
        inv = np.linalg.inv
        Jm = Domain.Jm
        AllGauss = Domain.AllGauss

        for Increment in range(LoadIncrement):
            # LOOP OVER ELEMENTS
            for elem in range(0,elements.shape[0]):
                # GET THE FIELDS AT THE ELEMENT LEVEL
                Eulerx = points + TotalDisp[:,:,Increment]
                LagrangeElemCoords = points[elements[elem,:],:]
                EulerELemCoords = Eulerx[elements[elem,:],:]
                if self.formulation.fields == 'electro-mechanics':
                    ElectricPotentialElem =  TotalPot[elements[elem,:],:,Increment]


                # GAUSS LOOP IN VECTORISED FORM
                ParentGradientX = np.einsum('ijk,jl->kil', Jm, LagrangeElemCoords)
                # MATERIAL GRADIENT TENSOR IN PHYSICAL ELEMENT [\nabla_0 (N)]
                MaterialGradient = np.einsum('ijk,kli->ijl', inv(ParentGradientX), Jm)
                # DEFORMATION GRADIENT TENSOR [\vec{x} \otimes \nabla_0 (N)]
                F[elem,:,:,:] = np.einsum('ij,kli->kjl', EulerELemCoords, MaterialGradient)
                # COMPUTE REMAINING KINEMATIC MEASURES
                StrainTensors = KinematicMeasures(F[elem,:,:,:], fem_solver.analysis_nature)

                # UPDATE/NO-UPDATE GEOMETRY
                if fem_solver.requires_geometry_update:
                    # MAPPING TENSOR [\partial\vec{X}/ \partial\vec{\varepsilon} (ndim x ndim)]
                    ParentGradientx = np.einsum('ijk,jl->kil',Jm,EulerELemCoords)
                    # SPATIAL GRADIENT TENSOR IN PHYSICAL ELEMENT [\nabla (N)]
                    SpatialGradient = np.einsum('ijk,kli->ilj',inv(ParentGradientx),Jm)
                    # COMPUTE ONCE detJ (GOOD SPEEDUP COMPARED TO COMPUTING TWICE)
                    detJ = np.einsum('i,i,i->i',AllGauss[:,0],np.abs(det(ParentGradientX)),
                        np.abs(StrainTensors['J']))
                else:
                    # SPATIAL GRADIENT AND MATERIAL GRADIENT TENSORS ARE EQUAL
                    SpatialGradient = np.einsum('ikj',MaterialGradient)
                    # COMPUTE ONCE detJ
                    detJ = np.einsum('i,i->i',AllGauss[:,0],np.abs(det(ParentGradientX)))


                # LOOP OVER GAUSS POINTS
                for counter in range(AllGauss.shape[0]):

                    if self.formulation.fields == 'electro-mechanics':
                        # GET ELECTRIC FILED
                        ElectricFieldx[elem,counter,:,:] = - np.dot(SpatialGradient[counter,:,:].T,
                            ElectricPotentialElem)

                        # COMPUTE ELECTRIC DISPLACEMENT
                        ElectricDisplacementx[elem,counter,:,:] = material.ElectricDisplacementx(StrainTensors, 
                            ElectricFieldx, elem, counter)
                    else:
                        ElectricFieldx, ElectricDisplacementx = None, None

                    # COMPUTE CAUCHY STRESS TENSOR
                    if fem_solver.requires_geometry_update:
                        CauchyStressTensor[elem,counter,:,:] = material.CauchyStress(StrainTensors,
                            ElectricFieldx,elem,counter)
            

        MainDict = {}
        MainDict['F'] = np.zeros((LoadIncrement,npoint,ndim,ndim))
        # MainDict['strain'] = np.zeros((LoadIncrement,npoint,ndim,ndim))
        MainDict['CauchyStress'] = np.zeros((LoadIncrement,npoint,ndim,ndim))
        MainDict['ElectricFieldx'] = np.zeros((LoadIncrement,npoint,ndim,ndim))
        MainDict['ElectricDisplacementx'] = np.zeros((LoadIncrement,npoint,ndim,ndim))

        for Increment in range(LoadIncrement):
            for inode in np.unique(elements):
                Els, Pos = np.where(elements==inode)
                ncommon_nodes = Els.shape[0]
                for uelem in range(ncommon_nodes):
                    MainDict['F'][Increment,inode,:,:] += F[Els[uelem],Pos[uelem],:,:]
                    if formulation.fields == "electro-mechanics":
                        MainDict['ElectricFieldx'][Increment,inode,:,:] += ElectricFieldx[Els[uelem],Pos[uelem],:,:]
                        MainDict['ElectricDisplacementx'][Increment,inode,:,:] += ElectricDisplacementx[Els[uelem],Pos[uelem],:,:]
                    MainDict['CauchyStress'][Increment,inode,:,:] += CauchyStressTensor[Els[uelem],Pos[uelem],:,:]

                # AVERAGE OUT
                MainDict['F'][Increment,inode,:,:] /= ncommon_nodes
                if formulation.fields == "electro-mechanics":
                    MainDict['ElectricFieldx'][Increment,inode,:,:] /= ncommon_nodes
                    MainDict['ElectricDisplacementx'][Increment,inode,:,:] /= ncommon_nodes
                MainDict['CauchyStress'][Increment,inode,:,:] /= ncommon_nodes


        self.recovered_fields = MainDict
        return




    def WriteVTK(self,filename=None, quantity=0, compute_recovered_fields=True):
        """Writes results to a VTK file for Paraview"""

        if compute_recovered_fields == True:
            self.StressRecovery()
        if filename is None:
            warn("file name not specified. I am going to write in the current directory")
        elif filename is not None :
            if isinstance(filename,str) is False:
                raise ValueError("file name should be a string")

        MainDict = self.recovered_fields
        LoadIncrement = self.sol.shape[2]

        # GET LINEAR MESH
        lmesh = self.mesh.GetLinearMesh()
        sol = self.sol[:lmesh.nnode,:,:]
        if compute_recovered_fields:
            F = MainDict['F'][:,:lmesh.nnode,:,:]
            CauchyStress = MainDict['CauchyStress'][:,:lmesh.nnode,:,:]
            if self.formulation.fields == "electro-mechanics":
                ElectricFieldx = MainDict['ElectricFieldx'][:,:lmesh.nnode,:,:]
                ElectricDisplacementx = MainDict['ElectricDisplacementx'][:,:lmesh.nnode,:,:]

        if lmesh.element_type =='tri':
            cellflag = 5
        elif lmesh.element_type =='quad':
            cellflag = 9
        if lmesh.element_type =='tet':
            cellflag = 10
        elif lmesh.element_type == 'hex':
            cellflag = 12


        # COMPONENTS OF F, Cauchy
        mm = 1
        nn = 1
        # COMPONENTS OF E, D
        rr = 0

        for Increment in range(LoadIncrement):
            vtk_writer.write_vtu(Verts=lmesh.points+sol[:,:,Increment], 
                    Cells={cellflag:lmesh.elements}, pdata=sol[:,quantity,Increment],
                    fname=filename+'_Sol_'+str(Increment)+'.vtu')

        if compute_recovered_fields:
            for Increment in range(LoadIncrement):
                vtk_writer.write_vtu(Verts=lmesh.points+sol[:,:,Increment], 
                    Cells={cellflag:lmesh.elements}, pdata=F[Increment,:,mm,nn],
                    fname=filename+'_F_'+str(Increment)+'.vtu')
                vtk_writer.write_vtu(Verts=lmesh.points+sol[:,:,Increment], 
                    Cells={cellflag:lmesh.elements}, pdata=CauchyStress[Increment,:,mm,nn],
                    fname=filename+'_Cauchy_'+str(Increment)+'.vtu')
                if self.formulation.fields == "electro-mechanics":
                    vtk_writer.write_vtu(Verts=lmesh.points+sol[:,:,Increment], 
                        Cells={cellflag:lmesh.elements}, pdata=ElectricFieldx[Increment,:,rr,0],
                    fname=filename+'_E_'+str(Increment)+'.vtu')
                    vtk_writer.write_vtu(Verts=lmesh.points+sol[:,:,Increment], 
                        Cells={cellflag:lmesh.elements}, pdata=ElectricDisplacementx[Increment,:,rr,0],
                        fname=filename+'_D_'+str(Increment)+'.vtu')

        return


    def WriteHDF5(self, filename=None, compute_recovered_fields=True):
        """Writes the solution data to a HDF5 file. Give the extension name while providing filename"""

        if compute_recovered_fields == True:
            self.StressRecovery()
        if filename is None:
            warn("file name not specified. I am going to write in the current directory")
        elif filename is not None :
            if isinstance(filename,str) is False:
                raise ValueError("file name should be a string")

        if compute_recovered_fields is False:
            MainDict = {}
            MainDict['Solution'] = self.sol
            io.savemat(filename,MainDict,do_compression=True)
        else:
            MainDict = self.recovered_fields
            MainDict['Solution'] = self.sol
            io.savemat(filename,MainDict,do_compression=True)
        



    def PlotNewtonRaphsonConvergence(self):

        # KEEP THE IMPORTS LOCAL AS MATPLOTLIB IMPORT IS SLOW
        import matplotlib.pyplot as plt
        from scipy import io 
        # NEWTON-RAPHSON CONVERGENCE PLOT
        if MainData.nrplot[0]:
            if MainData.nrplot[1] == 'first':
                # First increment convergence
                plt.semilogy(MainData.NRConvergence['Increment_0'],'-ko')       
            elif MainData.nrplot[1] == 'last':
                # Last increment convergence
                plt.plot(np.log10(MainData.NRConvergence['Increment_'+str(len(MainData.NRConvergence)-1)]),'-ko')   
            else:
                # Arbitrary increment convergence
                plt.plot(np.log10(MainData.NRConvergence['Increment_'+str(MainData.nrplot[1])]),'-ko')  

            axis_font = {'size':'18'}
            plt.xlabel(r'$No\, of\, Iteration$', **axis_font)
            plt.ylabel(r'$log_{10}|Residual|$', **axis_font)
            # Save plot
            # plt.savefig(MainData.Path.ProblemResults+MainData.Path.Analysis+\
            #   MainData.Path.MaterialModel+'/NR_convergence_'+MaterialArgs.Type+'.eps',
            #   format='eps', dpi=1000)
            # Display plot
            plt.show()



    def Plot(self, figure=None, quantity=0, configuration="original", 
        colorbar=True, axis_type=None, plot_points=False, point_radius=0.5):


        if self.mesh is None:
            raise ValueError("Mesh not set for post-processing")
        if self.sol is None:
            raise ValueError("Solution not set for post-processing")

        from copy import deepcopy

        # GET LINEAR MESH
        mesh = self.mesh.GetLinearMesh()
        # GET LINEAR SOLUTION 
        sol = np.copy(self.sol[:mesh.nnode,:])

        if self.mesh.element_type == "tri":

            from Florence.QuadratureRules.FeketePointsTri import FeketePointsTri
            from Florence.QuadratureRules.EquallySpacedPoints import EquallySpacedPointsTri
            from Florence.QuadratureRules.NumericIntegrator import GaussLobattoQuadrature
            from Florence.QuadratureRules.NodeArrangement import NodeArrangementTri
            from Florence.FunctionSpace import Tri 
            from Florence.FunctionSpace.OneDimensional.BasisFunctions import LagrangeGaussLobatto, Lagrange
            from Florence.FunctionSpace.GetBases import GetBases

            
            from scipy.spatial import Delaunay
            from mpl_toolkits.mplot3d import Axes3D
            from matplotlib.colors import LightSource
            import matplotlib as mpl
            import matplotlib.pyplot as plt
            import matplotlib.tri as mtri
            import matplotlib.cm as cm
            from mpl_toolkits.axes_grid1 import make_axes_locatable
            
            fig = plt.figure()
            if configuration == "original":
                plt.triplot(mesh.points[:,0],mesh.points[:,1], mesh.elements[:,:3],color='k')
            elif configuration == "deformed":
                plt.triplot(mesh.points[:,0]+sol[:,0,-1], mesh.points[:,1]+sol[:,1,-1], mesh.elements[:,:3],color='k')
            else:
                raise ValueError("configuration can only be 'original' or 'deformed'")

            if configuration == "original":
                # plt.tricontourf(mesh.points[:,0], mesh.points[:,1], mesh.elements, sol[:,quantity,-1],cmap=cm.viridis)
                triang = mtri.Triangulation(mesh.points[:,0], mesh.points[:,1], mesh.elements)
                plt.tripcolor(triang, sol[:,quantity,-1], shading='gouraud', cmap=cm.viridis)
                if plot_points:
                    plt.plot(self.mesh.points[:,0], self.mesh.points[:,1],'ko')
            else:
                triang = mtri.Triangulation(mesh.points[:,0]+sol[:,0,-1], 
                    mesh.points[:,1]+sol[:,1,-1], mesh.elements)
                plt.tripcolor(triang, sol[:,quantity,-1], shading='gouraud', cmap=cm.viridis)
                if plot_points:
                    plt.plot(self.mesh.points[:,0]+self.sol[:,0,-1], self.mesh.points[:,1]+self.sol[:,1,-1],'ko')

            if axis_type == "equal":
                plt.axis(axis_type)
            plt.colorbar()
            plt.show()



        elif self.mesh.element_type == "tet":

            import os
            os.environ['ETS_TOOLKIT'] = 'qt4'
            from mayavi import mlab
            from matplotlib.colors import ColorConverter
            import matplotlib.cm as cm

            if figure is None:
                figure = mlab.figure(bgcolor=(1,1,1),fgcolor=(0,0,0),size=(800,600))
            
            if configuration == "original":
                trimesh_h = mlab.triangular_mesh(mesh.points[:,0], mesh.points[:,1], mesh.points[:,2], 
                    mesh.faces, scalars=self.sol[:,0,-1])

                mlab.triangular_mesh(mesh.points[:,0], mesh.points[:,1], mesh.points[:,2], 
                    mesh.faces, representation="mesh", color=(0,0,0))

                if plot_points:
                    mlab.points3d(self.mesh.points[:,0],self.mesh.points[:,1],
                        self.mesh.points[:,2],color=(0,0,0),mode='sphere',scale_factor=point_radius)

            elif configuration == "deformed":
                trimesh_h = mlab.triangular_mesh(mesh.points[:,0]+sol[:,0,-1], 
                    mesh.points[:,1]+sol[:,1,-1], mesh.points[:,2]+sol[:,2,-1], 
                    mesh.faces, scalars=sol[:,quantity,-1])

                mlab.triangular_mesh(mesh.points[:,0]+sol[:,0,-1], 
                    mesh.points[:,1]+sol[:,1,-1], mesh.points[:,2]+sol[:,2,-1], 
                    mesh.faces, representation="mesh", color=(0,0,0))

                if plot_points:
                    mlab.points3d(self.mesh.points[:,0]+self.sol[:,0,-1],self.mesh.points[:,1]+self.sol[:,1,-1],
                        self.mesh.points[:,2]+self.sol[:,2,-1],color=(0,0,0),mode='sphere',scale_factor=point_radius)


            # CHANGE LIGHTING OPTION
            trimesh_h.actor.property.interpolation = 'phong'
            trimesh_h.actor.property.specular = 0.1
            trimesh_h.actor.property.specular_power = 5

            # MAYAVI MLAB DOES NOT HAVE VIRIDIS AS OF NOW SO 
            # GET VIRIDIS COLORMAP FROM MATPLOTLIB
            color_func = ColorConverter()
            rgba_lower = color_func.to_rgba_array(cm.viridis.colors)
            # rgba_lower = color_func.to_rgba_array(cm.viridis_r.colors)
            RGBA_higher = np.round(rgba_lower*255).astype(np.int64)
            # UPDATE LUT OF THE COLORMAP
            trimesh_h.module_manager.scalar_lut_manager.lut.table = RGBA_higher


            if colorbar:
                cbar = mlab.colorbar(object=trimesh_h, orientation="vertical",label_fmt="%9.2f")

            mlab.draw()
            mlab.show()



    def Animate(self, figure=None, quantity=0, configuration="original", 
        colorbar=True, axis_type=None, plot_points=False, point_radius=0.5):

        """
            quantity=0 - ux
            quantity=0 - uy
            quantity=0 - uz if 2D, phi if 3D
        """


        if self.mesh is None:
            raise ValueError("Mesh not set for post-processing")
        if self.sol is None:
            raise ValueError("Solution not set for post-processing")

        from copy import deepcopy

        # GET LINEAR MESH
        mesh = deepcopy(self.mesh)
        if mesh.element_type == "tri":
            mesh.elements = mesh.elements[:,:3]
        elif mesh.element_type == "tet":
            mesh.elements = mesh.elements[:,:4]
            mesh.faces = mesh.faces[:,:3]
        mesh.nnode = int(np.max(mesh.elements)+1)
        mesh.points = mesh.points[:mesh.nnode,:]
        # GET LINEAR SOLUTION - [MODIFIES THE SOLUTION]
        sol = np.copy(self.sol[:mesh.nnode,:])

        if self.mesh.element_type == "tri":

            from Florence.QuadratureRules.FeketePointsTri import FeketePointsTri
            from Florence.QuadratureRules.EquallySpacedPoints import EquallySpacedPointsTri
            from Florence.QuadratureRules.NumericIntegrator import GaussLobattoQuadrature
            from Florence.QuadratureRules.NodeArrangement import NodeArrangementTri
            from Florence.FunctionSpace import Tri 
            from Florence.FunctionSpace.OneDimensional.BasisFunctions import LagrangeGaussLobatto, Lagrange
            from Florence.FunctionSpace.GetBases import GetBases
            from Florence import Mesh

            from copy import deepcopy
            from scipy.spatial import Delaunay
            from mpl_toolkits.mplot3d import Axes3D
            from matplotlib.colors import LightSource
            import matplotlib as mpl
            import matplotlib.pyplot as plt
            import matplotlib.tri as mtri
            import matplotlib.cm as cm
            from mpl_toolkits.axes_grid1 import make_axes_locatable
            import matplotlib.animation as animation
            
            # fig = plt.figure()
            fig, ax = plt.subplots()
            self.configuration = configuration

            def animator(incr):
                configuration = self.configuration
                # GET LINEAR SOLUTION - [MODIFIES THE SOLUTION]
                sol = self.sol[:mesh.nnode,:]

                ax.clear()
                if configuration == "deformed":
                    triang = mtri.Triangulation(mesh.points[:,0]+sol[:,0,incr], 
                        mesh.points[:,1]+sol[:,1,incr], mesh.elements)
                    ax.triplot(mesh.points[:,0]+sol[:,0,incr], mesh.points[:,1]+sol[:,1,incr], 
                        mesh.elements[:,:3],color='k')
                    tri_h = ax.tripcolor(triang, sol[:,quantity,incr], shading='gouraud', cmap=cm.viridis)
                    if plot_points:
                        ax.plot(self.mesh.points[:,0]+sol[:,0,incr], 
                            self.mesh.points[:,1]+self.sol[:,1,incr],'o',markersize=5  ,color='k')
                elif configuration == "original":
                    plt.triplot(mesh.points[:,0],mesh.points[:,1], mesh.elements[:,:3],color='k')
                    # plt.tricontourf(mesh.points[:,0], mesh.points[:,1], mesh.elements, 
                    #     sol[:,quantity,incr],cmap=cm.viridis)
                    triang = mtri.Triangulation(mesh.points[:,0], mesh.points[:,1], mesh.elements)
                    tri_h = ax.tripcolor(triang, sol[:,quantity,incr], shading='gouraud', cmap=cm.viridis)
                    if plot_points:
                        ax.plot(self.mesh.points[:,0],self.mesh.points[:,1],
                            'o',markersize=5  ,color='k')

                    # return tri_h
 
            interval = 2 #in seconds
            ani = animation.FuncAnimation(fig,animator,self.sol.shape[2],interval=interval, repeat=True)

            # if colorbar is True:
                # fig.colorbar()
                # fig.colorbar(mappable=tri_h,cmap=cm.viridis)
                # plt.colorbar()
            
            if axis_type == "equal":
                plt.axis(axis_type)
            plt.show()

        elif self.mesh.element_type == "tet":

            import os
            os.environ['ETS_TOOLKIT'] = 'qt4'
            from mayavi import mlab
            from matplotlib.colors import ColorConverter
            import matplotlib.cm as cm

            if figure is None:
                figure = mlab.figure(bgcolor=(1,1,1),fgcolor=(0,0,0),size=(800,600))
            
            if configuration == "original":
                trimesh_h = mlab.triangular_mesh(mesh.points[:,0], mesh.points[:,1], mesh.points[:,2], 
                    mesh.faces, scalars=self.sol[:,quantity,0])

                wire_h = mlab.triangular_mesh(mesh.points[:,0], mesh.points[:,1], mesh.points[:,2], 
                    mesh.faces, representation="mesh", color=(0,0,0))

                points_h = mlab.points3d(self.mesh.points[:,0],self.mesh.points[:,1],
                    self.mesh.points[:,2],color=(0,0,0),mode='sphere',scale_factor=point_radius)

            elif configuration == "deformed":
                trimesh_h = mlab.triangular_mesh(mesh.points[:,0]+sol[:,0,0], 
                    mesh.points[:,1]+sol[:,1,0], mesh.points[:,2]+sol[:,2,0], 
                    mesh.faces, scalars=sol[:,quantity,0])

                wire_h = mlab.triangular_mesh(mesh.points[:,0]+sol[:,0,0], 
                    mesh.points[:,1]+sol[:,1,0], mesh.points[:,2]+sol[:,2,0], 
                    mesh.faces, representation="mesh", color=(0,0,0))

                points_h = mlab.points3d(self.mesh.points[:,0]+self.sol[:,0,0],self.mesh.points[:,1]+self.sol[:,1,0],
                    self.mesh.points[:,2]+self.sol[:,2,0],color=(0,0,0),mode='sphere',scale_factor=point_radius)


            # CHANGE LIGHTING OPTION
            trimesh_h.actor.property.interpolation = 'phong'
            trimesh_h.actor.property.specular = 0.1
            trimesh_h.actor.property.specular_power = 5

            # MAYAVI MLAB DOES NOT HAVE VIRIDIS AS OF NOW SO 
            # GET VIRIDIS COLORMAP FROM MATPLOTLIB
            color_func = ColorConverter()
            rgba_lower = color_func.to_rgba_array(cm.viridis.colors)
            # rgba_lower = color_func.to_rgba_array(cm.viridis_r.colors)
            RGBA_higher = np.round(rgba_lower*255).astype(np.int64)
            # UPDATE LUT OF THE COLORMAP
            trimesh_h.module_manager.scalar_lut_manager.lut.table = RGBA_higher


            if colorbar:
                cbar = mlab.colorbar(object=trimesh_h, orientation="vertical",label_fmt="%9.2f")


            @mlab.animate(delay=1000) 
            def animator():
                fig = mlab.gcf()
                m_trimesh = trimesh_h.mlab_source
                m_wire = wire_h.mlab_source
                m_points = points_h.mlab_source
                for i in range(1,sol.shape[2]):
                    m_trimesh.reset(x=mesh.points[:,0]+sol[:,0,i], y=mesh.points[:,1]+sol[:,1,i],
                        z=mesh.points[:,2]+sol[:,2,i], scalars=sol[:,quantity,i])

                    m_wire.reset(x=mesh.points[:,0]+sol[:,0,i], y=mesh.points[:,1]+sol[:,1,i],
                        z=mesh.points[:,2]+sol[:,2,i])

                    m_points.reset(x=mesh.points[:,0]+sol[:,0,i], y=mesh.points[:,1]+sol[:,1,i],
                        z=mesh.points[:,2]+sol[:,2,i])

                    fig.scene.reset_zoom()
                    yield

            animator()
            mlab.show()



    
    def MeshQualityMeasures(self, mesh, TotalDisp, plot=True, show_plot=True):
        """Computes mesh quality measures, Q_1, Q_2, Q_3

            input:
                mesh:                   [Mesh] an instance of class mesh can be any mesh type

        """

        if self.is_scaledjacobian_computed is None:
            self.is_scaledjacobian_computed = False
        if self.is_material_anisotropic is None:
            self.is_material_anisotropic = False

        if self.is_scaledjacobian_computed is True:
            raise AssertionError('Scaled Jacobian seems to be already computed. Re-Computing it may return incorrect results')

        PostDomain = self.postdomain_bases

        vpoints = mesh.points
        if TotalDisp.ndim == 3:
            vpoints = vpoints + TotalDisp[:,:,-1]
        elif TotalDisp.ndim == 2:
            vpoints = vpoints + TotalDisp
        else:
            raise AssertionError("mesh points and displacment arrays are incompatible")

        elements = mesh.elements

        ScaledJacobian = np.zeros(elements.shape[0])
        ScaledFF = np.zeros(elements.shape[0])
        ScaledHH = np.zeros(elements.shape[0])

        if self.is_material_anisotropic:
            ScaledFNFN = np.zeros(elements.shape[0])
            ScaledCNCN = np.zeros(elements.shape[0])

        JMax =[]; JMin=[]
        for elem in range(mesh.nelem):
            LagrangeElemCoords = mesh.points[elements[elem,:],:]
            EulerElemCoords = vpoints[elements[elem,:],:]

            # COMPUTE KINEMATIC MEASURES AT ALL INTEGRATION POINTS USING EINSUM (AVOIDING THE FOR LOOP)
            # MAPPING TENSOR [\partial\vec{X}/ \partial\vec{\varepsilon} (ndim x ndim)]
            ParentGradientX = np.einsum('ijk,jl->kil',PostDomain.Jm,LagrangeElemCoords)
            # MAPPING TENSOR [\partial\vec{x}/ \partial\vec{\varepsilon} (ndim x ndim)]
            ParentGradientx = np.einsum('ijk,jl->kil',PostDomain.Jm,EulerElemCoords)
            # MATERIAL GRADIENT TENSOR IN PHYSICAL ELEMENT [\nabla_0 (N)]
            MaterialGradient = np.einsum('ijk,kli->ijl',la.inv(ParentGradientX),PostDomain.Jm)
            # DEFORMATION GRADIENT TENSOR [\vec{x} \otimes \nabla_0 (N)]
            F = np.einsum('ij,kli->kjl',EulerElemCoords,MaterialGradient)
            # JACOBIAN OF DEFORMATION GRADIENT TENSOR
            detF = np.abs(np.linalg.det(F))
            # COFACTOR OF DEFORMATION GRADIENT TENSOR
            H = np.einsum('ijk,k->ijk',np.linalg.inv(F).T,detF)

            # FIND JACOBIAN OF SPATIAL GRADIENT
            # USING ISOPARAMETRIC
            Jacobian = np.abs(np.linalg.det(ParentGradientx))
            # USING DETERMINANT OF DEFORMATION GRADIENT TENSOR
            # THIS GIVES A RESULT MUCH CLOSER TO ONE
            Jacobian = detF
            # USING INVARIANT F:F
            Q1 = np.sqrt(np.einsum('kij,lij->kl',F,F)).diagonal()
            # USING INVARIANT H:H
            Q2 = np.sqrt(np.einsum('ijk,ijl->kl',H,H)).diagonal()

            if self.is_material_anisotropic:
                Q4 = np.einsum('ijk,k',F,self.directions[elem,:])
                Q4 = np.sqrt(np.dot(Q4,Q4.T)).diagonal()

                C = np.einsum('ikj,ikl->ijl',F,F)
                Q5 = np.einsum('ijk,k',C,self.directions[elem,:]) 
                Q5 = np.sqrt(np.dot(Q5,Q5.T)).diagonal()

            # FIND MIN AND MAX VALUES
            JMin = np.min(Jacobian); JMax = np.max(Jacobian)
            ScaledJacobian[elem] = 1.0*JMin/JMax
            ScaledFF[elem] = 1.0*np.min(Q1)/np.max(Q1)
            ScaledHH[elem] = 1.0*np.min(Q2)/np.max(Q2)
            # Jacobian[elem] = np.min(detF)
            # print(np.min(Jacobian), np.max(Jacobian))

            if self.is_material_anisotropic:
                ScaledFNFN[elem] = 1.0*np.min(Q4)/np.max(Q4)
                ScaledCNCN[elem] = 1.0*np.min(Q5)/np.max(Q5)

        if np.isnan(ScaledJacobian).any():
            warn("Jacobian of mapping is close to zero")

        print 'Minimum ScaledJacobian value is', ScaledJacobian.min(), \
        'corresponding to element', ScaledJacobian.argmin()

        print 'Minimum ScaledFF value is', ScaledFF.min(), \
        'corresponding to element', ScaledFF.argmin()

        print 'Minimum ScaledHH value is', ScaledHH.min(), \
        'corresponding to element', ScaledHH.argmin()

        if self.is_material_anisotropic:
            print 'Minimum ScaledFNFN value is', ScaledFNFN.min(), \
            'corresponding to element', ScaledFNFN.argmin()

            print 'Minimum ScaledCNCN value is', ScaledCNCN.min(), \
            'corresponding to element', ScaledCNCN.argmin()


        if plot:
            import matplotlib.pyplot as plt
            fig = plt.figure()
            plt.bar(np.linspace(0,elements.shape[0]-1,elements.shape[0]),ScaledJacobian,width=1.,alpha=0.4)
            plt.xlabel(r'$Elements$',fontsize=18)
            plt.ylabel(r'$Scaled\, Jacobian$',fontsize=18)
            if show_plot:
                plt.show()

        # SET COMPUTED TO TRUE
        self.is_scaledjacobian_computed = True

        if not self.is_material_anisotropic:
            return self.is_scaledjacobian_computed, ScaledFF, ScaledHH, ScaledJacobian
        else:
            return self.is_scaledjacobian_computed, ScaledFF, ScaledHH, ScaledJacobian, ScaledFNFN, ScaledCNCN




    def CurvilinearPlot(self,*args,**kwargs):
        """Curvilinear (or linear) plots for high order finite elements"""
        if len(args) == 0:
            if self.mesh is None:
                raise ValueError("Mesh not set for post-processing")
            else:
                mesh = self.mesh
        else:
            mesh = args[0]

        if len(args) > 1:
            TotalDisp = args[1]
        else:
            if self.sol is None:
                raise ValueError("Solution not set for post-processing")
            else:
                TotalDisp = self.sol

        if mesh.element_type == "tri":
            # self.CurvilinearPlotTri(*args,**kwargs)
            self.CurvilinearPlotTri(mesh,TotalDisp,**kwargs)
        elif mesh.element_type == "tet":
            # self.CurvilinearPlotTet(*args,**kwargs)
            self.CurvilinearPlotTet(mesh,TotalDisp,**kwargs)
        else:
            raise ValueError("Unknown mesh type")


    @staticmethod
    def CurvilinearPlotTri(mesh, TotalDisp, QuantityToPlot=None,
        ProjectionFlags=None, InterpolationDegree=40, EquallySpacedPoints=False,
        TriSurf=False, colorbar=False, PlotActualCurve=False, point_radius = 3, color="#C5F1C5",
        plot_points=False, plot_edges=True, save=False, filename=None, show_plot=True):

        """High order curved triangular mesh plots, based on high order nodal FEM.
            The equally spaced FEM points do not work as good as the Fekete points 
        """


        from Florence.QuadratureRules.FeketePointsTri import FeketePointsTri
        from Florence.QuadratureRules.EquallySpacedPoints import EquallySpacedPointsTri
        from Florence.QuadratureRules.NumericIntegrator import GaussLobattoQuadrature
        from Florence.QuadratureRules.NodeArrangement import NodeArrangementTri
        from Florence.FunctionSpace import Tri 
        from Florence.FunctionSpace.OneDimensional.BasisFunctions import LagrangeGaussLobatto, Lagrange
        from Florence.FunctionSpace.GetBases import GetBases

        from copy import deepcopy
        from scipy.spatial import Delaunay
        from mpl_toolkits.mplot3d import Axes3D
        from matplotlib.colors import LightSource
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        import matplotlib.tri as mtri
        import matplotlib.cm as cm
        from mpl_toolkits.axes_grid1 import make_axes_locatable
        
        # SINCE THIS IS A 2D PLOT
        ndim = 2

        C = InterpolationDegree
        p = C+1
        nsize = int((p+1)*(p+2)/2.)
        CActual = mesh.InferPolynomialDegree() - 1 
        nsize_2 = int((CActual+2)*(CActual+3)/2.)

        FeketePointsTri = FeketePointsTri(C)
        if EquallySpacedPoints is True:
            FeketePointsTri = EquallySpacedPointsTri(C)

        # BUILD DELAUNAY TRIANGULATION OF REFERENCE ELEMENTS
        TrianglesFunc = Delaunay(FeketePointsTri)
        Triangles = TrianglesFunc.simplices.copy()


        # GET EQUALLY-SPACED/GAUSS-LOBATTO POINTS FOR THE EDGES
        if EquallySpacedPoints is False:
            GaussLobattoPointsOneD = GaussLobattoQuadrature(C+2)[0]
        else:
            GaussLobattoPointsOneD = Lagrange(C,0)[-1]

        BasesTri = np.zeros((nsize_2,FeketePointsTri.shape[0]),dtype=np.float64)
        hpBases = Tri.hpNodal.hpBases
        for i in range(FeketePointsTri.shape[0]):
            BasesTri[:,i] = hpBases(CActual,FeketePointsTri[i,0],FeketePointsTri[i,1],
                EvalOpt=1,EquallySpacedPoints=EquallySpacedPoints,Transform=1)[0]

        BasesOneD = np.zeros((CActual+2,GaussLobattoPointsOneD.shape[0]),dtype=np.float64)
        for i in range(GaussLobattoPointsOneD.shape[0]):
            BasesOneD[:,i] = LagrangeGaussLobatto(CActual,GaussLobattoPointsOneD[i])[0]

        smesh = deepcopy(mesh)
        smesh.elements = mesh.elements[:,:ndim+1]
        nmax = np.max(smesh.elements)+1
        smesh.points = mesh.points[:nmax,:]
        smesh.GetEdgesTri()
        edge_elements = smesh.GetElementsEdgeNumberingTri()


        # GET EDGE ORDERING IN THE REFERENCE ELEMENT
        reference_edges = NodeArrangementTri(CActual)[0]
        reference_edges = np.concatenate((reference_edges,reference_edges[:,1,None]),axis=1)
        reference_edges = np.delete(reference_edges,1,1)

        # GET EULERIAN GEOMETRY
        if TotalDisp.ndim==3:
            vpoints = mesh.points + TotalDisp[:,:,-1]
        else:
            vpoints = mesh.points + TotalDisp

        # GET X & Y OF CURVED EDGES
        if plot_edges:
            x_edges = np.zeros((C+2,smesh.all_edges.shape[0]))
            y_edges = np.zeros((C+2,smesh.all_edges.shape[0]))

            for iedge in range(smesh.all_edges.shape[0]):
                ielem = edge_elements[iedge,0]
                edge = mesh.elements[ielem,reference_edges[edge_elements[iedge,1],:]]
                coord_edge = vpoints[edge,:]
                x_edges[:,iedge], y_edges[:,iedge] = np.dot(coord_edge.T,BasesOneD)


        # MAKE FIGURE
        fig = plt.figure()
        ls = LightSource(azdeg=315, altdeg=45)
        if TriSurf is True:
            ax = fig.add_subplot(111, projection='3d')
        else:
            ax = fig.add_subplot(111)

        if plot_edges:
            # PLOT CURVED EDGES
            ax.plot(x_edges,y_edges,'k')
        

        nnode = nsize*mesh.nelem
        nelem = Triangles.shape[0]*mesh.nelem

        Xplot = np.zeros((nnode,2),dtype=np.float64)
        Tplot = np.zeros((nelem,3),dtype=np.int64)
        Uplot = np.zeros(nnode,dtype=np.float64)

        if QuantityToPlot is None:
            quantity_to_plot = np.zeros(mesh.nelem)
        else:
            quantity_to_plot = QuantityToPlot

        # FOR CURVED ELEMENTS
        for ielem in range(mesh.nelem):
            Xplot[ielem*nsize:(ielem+1)*nsize,:] = np.dot(BasesTri.T, vpoints[mesh.elements[ielem,:],:])
            Tplot[ielem*TrianglesFunc.nsimplex:(ielem+1)*TrianglesFunc.nsimplex,:] = Triangles + ielem*nsize
            Uplot[ielem*nsize:(ielem+1)*nsize] = quantity_to_plot[ielem]

        # PLOT CURVED ELEMENTS
        if TriSurf is True:
            # ax.plot_trisurf(Tplot,Xplot[:,0], Xplot[:,1], Xplot[:,1]*0)
            triang = mtri.Triangulation(Xplot[:,0], Xplot[:,1],Tplot)
            ax.plot_trisurf(triang,Xplot[:,0]*0, edgecolor="none",facecolor="#ffddbb")
            ax.view_init(90,-90)
            ax.dist = 7
        else:
            # plt.tricontourf(Xplot[:,0], Xplot[:,1], Tplot, np.ones(Xplot.shape[0]), 100,alpha=0.8)
            # plt.tricontourf(Xplot[:,0], Xplot[:,1], Tplot, Uplot, 100,alpha=0.8)
            # plt.tricontourf(Xplot[:,0], Xplot[:,1], Tplot[:4,:], np.ones(Xplot.shape[0]),alpha=0.8,origin='lower')

            if QuantityToPlot is None:
                # plt.tricontourf(Xplot[:,0], Xplot[:,1], Tplot, Uplot, colors="#C5F1C5")
                triang = mtri.Triangulation(Xplot[:,0], Xplot[:,1],Tplot)
                plt.tripcolor(triang, Uplot, shading='gouraud', cmap=cm.viridis)
            else:
                plt.tricontourf(Xplot[:,0], Xplot[:,1], Tplot, Uplot, 100,alpha=0.8)

        # PLOT CURVED POINTS
        if plot_points:
            # plt.plot(vpoints[:,0],vpoints[:,1],'o',markersize=3,color='#F88379')
            plt.plot(vpoints[:,0],vpoints[:,1],'o',markersize=point_radius,color='k')

        if QuantityToPlot is not None:
            # plt.set_cmap('viridis')
            plt.set_cmap('viridis_r')
            plt.clim(0,1)
        

        if colorbar is True:
            ax_cbar = mpl.colorbar.make_axes(plt.gca(), shrink=1.0)[0]
            cbar = mpl.colorbar.ColorbarBase(ax_cbar, cmap=cm.viridis,
                               norm=mpl.colors.Normalize(vmin=-0, vmax=1))
            cbar.set_clim(0, 1)
            divider = make_axes_locatable(ax_cbar)
            cax = divider.append_axes("right", size="1%", pad=0.005)
        
        if PlotActualCurve is True:
            ActualCurve = getattr(MainData,'ActualCurve',None)
            if ActualCurve is not None:
                for i in range(len(MainData.ActualCurve)):
                    actual_curve_points = MainData.ActualCurve[i]
                    plt.plot(actual_curve_points[:,0],actual_curve_points[:,1],'-r',linewidth=3)
            else:
                raise KeyError("You have not computed the CAD curve points")

        plt.axis('equal')
        plt.axis('off')

        if save:
            if filename is None:
                raise ValueError("No filename given. Supply one with extension")
            else:
                plt.savefig(filename,format="eps",dpi=300, bbox_inches='tight')


        if show_plot:
            plt.show()







    @staticmethod
    def CurvilinearPlotTet(mesh,TotalDisp,QuantityToPlot=None,
        ProjectionFlags=None, InterpolationDegree=20, EquallySpacedPoints=False, PlotActualCurve=False,
        plot_points=False, plot_edges=True, plot_surfaces=True, point_radius=0.02, colorbar=False, color=None, figure=None,
        show_plot=True, save=False, filename=None):

        """High order curved tetrahedral surfaces mesh plots, based on high order nodal FEM.
            The equally spaced FEM points do not work as good as the Fekete points 
        """



        from Florence.QuadratureRules.FeketePointsTri import FeketePointsTri
        from Florence.QuadratureRules.EquallySpacedPoints import EquallySpacedPointsTri
        from Florence.QuadratureRules.NumericIntegrator import GaussLobattoQuadrature
        from Florence.QuadratureRules.NodeArrangement import NodeArrangementTri
        from Florence.FunctionSpace import Tri 
        from Florence.FunctionSpace.OneDimensional.BasisFunctions import LagrangeGaussLobatto, Lagrange
        from Florence.FunctionSpace.GetBases import GetBases
        from Florence import Mesh

        from copy import deepcopy
        from scipy.spatial import Delaunay
        from mpl_toolkits.mplot3d import Axes3D
        from matplotlib.colors import LightSource
        import matplotlib as mpl
        import matplotlib.pyplot as plt
        import matplotlib.tri as mtri
        import matplotlib.cm as cm
        from matplotlib.colors import ColorConverter
        from mpl_toolkits.axes_grid1 import make_axes_locatable

        import os
        os.environ['ETS_TOOLKIT'] = 'qt4'
        from mayavi import mlab

        # SINCE THIS IS A 3D PLOT
        ndim=3

        C = InterpolationDegree
        p = C+1
        nsize = int((p+1)*(p+2)/2.)
        CActual = mesh.InferPolynomialDegree() - 1
        nsize_2 = int((CActual+2)*(CActual+3)/2.)

        FeketePointsTri = FeketePointsTri(C)
        if EquallySpacedPoints is True:
            FeketePointsTri = EquallySpacedPointsTri(C)

        # BUILD DELAUNAY TRIANGULATION OF REFERENCE ELEMENTS
        TrianglesFunc = Delaunay(FeketePointsTri)
        Triangles = TrianglesFunc.simplices.copy()
        # plt.triplot(FeketePointsTri[:,0], FeketePointsTri[:,1], Triangles); plt.axis('off')


        # GET EQUALLY-SPACED/GAUSS-LOBATTO POINTS FOR THE EDGES
        if EquallySpacedPoints is False:
            GaussLobattoPointsOneD = GaussLobattoQuadrature(C+2)[0]
        else:
            GaussLobattoPointsOneD = Lagrange(C,0)[-1]

        BasesTri = np.zeros((nsize_2,FeketePointsTri.shape[0]),dtype=np.float64)
        hpBases = Tri.hpNodal.hpBases
        for i in range(FeketePointsTri.shape[0]):
            BasesTri[:,i] = hpBases(CActual,FeketePointsTri[i,0],FeketePointsTri[i,1],
                EvalOpt=1,EquallySpacedPoints=EquallySpacedPoints,Transform=1)[0]

        BasesOneD = np.zeros((CActual+2,GaussLobattoPointsOneD.shape[0]),dtype=np.float64)
        for i in range(GaussLobattoPointsOneD.shape[0]):
            BasesOneD[:,i] = LagrangeGaussLobatto(CActual,GaussLobattoPointsOneD[i])[0]


        # GET ONLY THE FACES WHICH NEED TO BE PLOTTED 
        if ProjectionFlags is None:
            faces_to_plot_flag = np.ones(mesh.faces.shape[0])
        else:
            faces_to_plot_flag = ProjectionFlags.flatten()

        # CHECK IF ALL FACES NEED TO BE PLOTTED OR ONLY BOUNDARY FACES
        if faces_to_plot_flag.shape[0] > mesh.faces.shape[0]:
            # ALL FACES
            corr_faces = mesh.all_faces
            # FOR MAPPING DATA E.G. SCALED JACOBIAN FROM ELEMENTS TO FACES
            face_elements = mesh.GetElementsFaceNumberingTet()

        elif faces_to_plot_flag.shape[0] == mesh.faces.shape[0]:
            # ONLY BOUNDARY FACES
            corr_faces = mesh.faces
            # FOR MAPPING DATA E.G. SCALED JACOBIAN FROM ELEMENTS TO FACES
            face_elements = mesh.GetElementsWithBoundaryFacesTet()
        else:
            # raise ValueError("I do not understand what you want to plot")
            corr_faces = mesh.all_faces
            face_elements = mesh.GetElementsFaceNumberingTet()

        faces_to_plot = corr_faces[faces_to_plot_flag.flatten()==1,:]

        if QuantityToPlot is not None:
            quantity_to_plot = QuantityToPlot[face_elements[faces_to_plot_flag.flatten()==1,0]]

        # BUILD MESH OF SURFACE
        smesh = Mesh()
        smesh.element_type = "tri"
        # smesh.elements = np.copy(corr_faces)
        smesh.elements = np.copy(faces_to_plot)
        smesh.nelem = smesh.elements.shape[0]
        smesh.points = mesh.points[np.unique(smesh.elements),:]


        # MAP         
        unique_elements, inv = np.unique(smesh.elements,return_inverse=True)
        mapper = np.arange(unique_elements.shape[0])
        smesh.elements = mapper[inv].reshape(smesh.elements.shape)

 
        smesh.GetBoundaryEdgesTri()
        smesh.GetEdgesTri()
        edge_elements = smesh.GetElementsEdgeNumberingTri()

        
        # GET EDGE ORDERING IN THE REFERENCE ELEMENT
        reference_edges = NodeArrangementTri(CActual)[0]
        reference_edges = np.concatenate((reference_edges,reference_edges[:,1,None]),axis=1)
        reference_edges = np.delete(reference_edges,1,1)

        # GET EULERIAN GEOMETRY
        if TotalDisp.ndim == 3:
            vpoints = mesh.points + TotalDisp[:,:,-1]
        elif TotalDisp.ndim == 2:
            vpoints = mesh.points + TotalDisp
        else:
            raise AssertionError("mesh points and displacment arrays are incompatible")

        # svpoints = vpoints[np.unique(mesh.faces),:]
        svpoints = vpoints[np.unique(faces_to_plot),:]
        del vpoints
        gc.collect()

        # MAKE A FIGURE
        if figure is None:
            figure = mlab.figure(bgcolor=(1,1,1),fgcolor=(1,1,1),size=(800,600))
        figure.scene.disable_render = True

        if plot_edges:
            # GET X, Y & Z OF CURVED EDGES  
            x_edges = np.zeros((C+2,smesh.all_edges.shape[0]))
            y_edges = np.zeros((C+2,smesh.all_edges.shape[0]))
            z_edges = np.zeros((C+2,smesh.all_edges.shape[0]))

            for iedge in range(smesh.all_edges.shape[0]):
                ielem = edge_elements[iedge,0]
                edge = smesh.elements[ielem,reference_edges[edge_elements[iedge,1],:]]
                coord_edge = svpoints[edge,:]
                x_edges[:,iedge], y_edges[:,iedge], z_edges[:,iedge] = np.dot(coord_edge.T,BasesOneD)

            
            # PLOT CURVED EDGES
            connections_elements = np.arange(x_edges.size).reshape(x_edges.shape[1],x_edges.shape[0])
            connections = np.zeros((x_edges.size,2),dtype=np.int64)
            for i in range(connections_elements.shape[0]):
                connections[i*(x_edges.shape[0]-1):(i+1)*(x_edges.shape[0]-1),0] = connections_elements[i,:-1]
                connections[i*(x_edges.shape[0]-1):(i+1)*(x_edges.shape[0]-1),1] = connections_elements[i,1:]
            connections = connections[:(i+1)*(x_edges.shape[0]-1),:]
            # point_cloulds = np.concatenate((x_edges.flatten()[:,None],y_edges.flatten()[:,None],z_edges.flatten()[:,None]),axis=1)
            
            # src = mlab.pipeline.scalar_scatter(x_edges.flatten(), y_edges.flatten(), z_edges.flatten())
            src = mlab.pipeline.scalar_scatter(x_edges.T.copy().flatten(), y_edges.T.copy().flatten(), z_edges.T.copy().flatten())
            src.mlab_source.dataset.lines = connections
            lines = mlab.pipeline.stripper(src)
            mlab.pipeline.surface(lines, color = (0,0,0), line_width=2)
            # mlab.pipeline.surface(lines, color = (0.72,0.72,0.72), line_width=2)

            # OLDER VERSION
            # for i in range(x_edges.shape[1]):
            #     mlab.plot3d(x_edges[:,i],y_edges[:,i],z_edges[:,i],color=(0,0,0),tube_radius=edge_width)
        

        # CURVED SURFACES
        if plot_surfaces:

            nface = smesh.elements.shape[0]
            nnode = nsize*nface
            nelem = Triangles.shape[0]*nface

            Xplot = np.zeros((nnode,3),dtype=np.float64)
            Tplot = np.zeros((nelem,3),dtype=np.int64)

            # FOR CURVED ELEMENTS
            for ielem in range(nface):
                Xplot[ielem*nsize:(ielem+1)*nsize,:] = np.dot(BasesTri.T, svpoints[smesh.elements[ielem,:],:])
                Tplot[ielem*TrianglesFunc.nsimplex:(ielem+1)*TrianglesFunc.nsimplex,:] = Triangles + ielem*nsize

            if QuantityToPlot is not None:
                Uplot = np.zeros(nnode,dtype=np.float64)
                for ielem in range(nface):
                    Uplot[ielem*nsize:(ielem+1)*nsize] = quantity_to_plot[ielem]

            point_line_width = .002
            # point_line_width = 0.5
            # point_line_width = .0008
            # point_line_width = 2.
            # point_line_width = .045
            # point_line_width = .015 # F6


            if color is None:
                color=(197/255.,241/255.,197/255.)

            # PLOT SURFACES (CURVED ELEMENTS)
            if QuantityToPlot is None:
                trimesh_h = mlab.triangular_mesh(Xplot[:,0], Xplot[:,1], Xplot[:,2], Tplot,
                    line_width=point_line_width,color=color)
            else:
                trimesh_h = mlab.triangular_mesh(Xplot[:,0], Xplot[:,1], Xplot[:,2], Tplot, scalars = Uplot,
                    line_width=point_line_width,colormap='summer')

            # trimesh_h = mlab.triangular_mesh(Xplot[:,0], Xplot[:,1], Xplot[:,2], Tplot, scalars=Uplot,line_width=point_line_width,colormap='summer')

            # PLOT POINTS ON CURVED MESH
            if plot_points:
                # mlab.points3d(svpoints[:,0],svpoints[:,1],svpoints[:,2],color=(0,0,0),mode='sphere',scale_factor=2.5*point_line_width)
                mlab.points3d(svpoints[:,0],svpoints[:,1],svpoints[:,2],color=(0,0,0),mode='sphere',scale_factor=point_radius)

            figure.scene.disable_render = False

            if QuantityToPlot is not None:
                # CHANGE LIGHTING OPTION
                trimesh_h.actor.property.interpolation = 'phong'
                trimesh_h.actor.property.specular = 0.1
                trimesh_h.actor.property.specular_power = 5

                # MAYAVI MLAB DOES NOT HAVE VIRIDIS AS OF NOW SO 
                # GET VIRIDIS COLORMAP FROM MATPLOTLIB
                color_func = ColorConverter()
                rgba_lower = color_func.to_rgba_array(cm.viridis.colors)
                # rgba_lower = color_func.to_rgba_array(cm.viridis_r.colors)
                RGBA_higher = np.round(rgba_lower*255).astype(np.int64)
                # UPDATE LUT OF THE COLORMAP
                trimesh_h.module_manager.scalar_lut_manager.lut.table = RGBA_higher 

        # SAVEFIG
        if save:
            if filename is None:
                raise ValueError("No filename given. Supply one with extension")
            else:
                mlab.savefig(filename,magnification="auto")


        # CONTROL CAMERA VIEW
        # mlab.view(azimuth=45, elevation=50, distance=80, focalpoint=None,
        #         roll=0, reset_roll=True, figure=None)

        mlab.view(azimuth=45, elevation=50, distance=80, focalpoint=None,
            roll=0, reset_roll=True, figure=None)
    
        if show_plot is True:
            # FORCE UPDATE MLAB TO UPDATE COLORMAP
            mlab.draw()
            mlab.show()









































    ###################################################################################
    ###################################################################################

    @staticmethod   
    def HighOrderPatchPlot(MainData,mesh,TotalDisp):

        import matplotlib.pyplot as plt
        
        fig = plt.figure()
        ax = fig.axes

        # TotalDisp = np.zeros_like(TotalDisp)
        # MainData.ScaledJacobian = np.ones_like(MainData.ScaledJacobian)

        # print TotalDisp[:,0,-1]
        # MainData.ScaledJacobian = np.zeros_like(MainData.ScaledJacobian)+1
        vpoints = np.copy(mesh.points)
        # print TotalDisp[:,:MainData.ndim,-1]
        vpoints += TotalDisp[:,:MainData.ndim,-1]

        dum1=[]; dum2=[]; dum3 = []; ddum=np.array([0,1,2,0])
        for i in range(0,MainData.C):
            dum1=np.append(dum1,i+3)
            dum2 = np.append(dum2, 2*MainData.C+3 +i*MainData.C -i*(i-1)/2 )
            dum3 = np.append(dum3,MainData.C+3 +i*(MainData.C+1) -i*(i-1)/2 )

        if MainData.C>0:
            ddum = (np.append(np.append(np.append(np.append(np.append(np.append(0,dum1),1),dum2),2),
                np.fliplr(dum3.reshape(1,dum3.shape[0]))),0) ).astype(np.int32)

        x_avg = []; y_avg = []
        for i in range(mesh.nelem):
            dum = vpoints[mesh.elements[i,:],:]

            plt.plot(dum[ddum,0],dum[ddum,1],alpha=0.02)
            # plt.fill(dum[ddum,0],dum[ddum,1],'#A4DDED')
            plt.fill(dum[ddum,0],dum[ddum,1],color=(0.75,MainData.ScaledJacobian[i],0.35))
            # afig = plt.fill(dum[ddum,0],dum[ddum,1],color=(0.75,MainData.Jacobian[i]/4.,0.35))    
            # afig= plt.fill(dum[ddum,0],dum[ddum,1])   

            # plt.fill(dum[ddum,0],dum[ddum,1],color=(0.75,1.0*i/mesh.elements.shape[0],0.35))  
            # plt.fill(dum[ddum,0],dum[ddum,1],color=(MainData.ScaledJacobian[i],0,1-MainData.ScaledJacobian[i]))   

            plt.plot(dum[ddum,0],dum[ddum,1],'#000000')
            
            # WRITE JACOBIAN VALUES ON ELEMENTS
            # coord = mesh.points[mesh.elements[i,:],:]
            # x_avg.append(np.sum(coord[:,0])/mesh.elements.shape[1])
            # y_avg.append(np.sum(coord[:,1])/mesh.elements.shape[1])
            # plt.text(x_avg[i],y_avg[i],np.around(MainData.ScaledJacobian[i],decimals=3))


        plt.plot(vpoints[:,0],vpoints[:,1],'o',color='#F88379',markersize=5) 

        plt.axis('equal')
        # plt.xlim([-0.52,-0.43])
        # plt.ylim([-0.03,0.045])
        plt.axis('off')

        # ax = plt.gca()
        # PCM=ax.get_children()[2]
        # plt.colorbar(afig)



    @staticmethod
    def HighOrderPatchPlot3D(MainData,mesh,TotalDisp=0):
        """ This 3D patch plot works but the elements at background are
        also shown
        """
        from mpl_toolkits.mplot3d import Axes3D
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        import matplotlib.pyplot as plt

        C = MainData.C
        a1,a2,a3,a4 = [],[],[],[]
        if C==1:
            a1 = [1, 5, 2, 9, 4, 8, 1]
            a2 = [1, 5, 2, 7, 3, 6, 1]
            a3 = [1, 6, 3, 10, 4, 8, 1]
            a4 = [2, 7, 3, 10, 4, 9, 2]
        elif C==2:
            a1 = [1, 5, 6, 2, 9, 11, 3, 10, 7, 1]
            a2 = [1, 5, 6, 2, 14, 19, 4, 18, 12, 1]
            a3 = [2, 9, 11, 3, 17, 20, 4, 19, 14, 2]
            a4 = [1, 12, 18, 4, 20, 17, 3, 10, 7, 1]
        elif C==3:
            a1 = [1, 5, 6, 7, 2, 20, 29, 34, 4, 33, 27, 17, 1]
            a2 = [1, 8, 12, 15, 3, 16, 14, 11, 2, 7, 6, 5, 1]
            a3 = [2, 11, 14, 16, 3, 26, 32, 35, 4, 34, 29, 20, 2]
            a4 = [1, 8, 12, 15, 3, 26, 32, 35, 4, 33, 27, 17, 1]
        elif C==4:
            a1 = [1, 5, 6, 7, 8, 2, 27, 41, 50, 55, 4, 54, 48, 38, 23, 1]
            a2 = [1, 9, 14, 18, 21, 3, 22, 20, 17, 13, 2, 8, 7, 6, 5, 1]
            a3 = [2, 13, 17, 20, 22, 3, 37, 47, 53, 56, 4, 55, 50, 41, 27, 2]
            a4 = [1, 9, 14, 18, 21, 3, 37, 47, 53, 56, 4, 54, 48, 38, 23, 1]

        a1 = np.asarray(a1); a2 = np.asarray(a2); a3 = np.asarray(a3); a4 = np.asarray(a4)
        a1 -= 1;    a2 -= 1;    a3 -= 1;    a4 -= 1
        a_list = [a1,a2,a3,a4]

        fig = plt.figure()
        ax = Axes3D(fig)

        # face_elements = mesh.GetElementsWithBoundaryFacesTet()
        # elements = mesh.elements[face_elements,:]
        # print mesh.faces 
        # mesh.ArrangeFacesTet() 

        # for elem in range(elements.shape[0]):
        for elem in range(mesh.nelem):
        # for elem in range(1):

            # LOOP OVER TET FACES
            num_faces = 4
            for iface in range(num_faces):
                a = a_list[iface]

                x = mesh.points[mesh.elements[elem,a],0]
                y = mesh.points[mesh.elements[elem,a],1]
                z = mesh.points[mesh.elements[elem,a],2]

                # x = mesh.points[elements[elem,a],0]
                # y = mesh.points[elements[elem,a],1]
                # z = mesh.points[elements[elem,a],2]

                vertices = [zip(x,y,z)]
                poly_object = Poly3DCollection(vertices)
                poly_object.set_linewidth(1)
                poly_object.set_linestyle('solid')
                poly_object.set_facecolor((0.75,1,0.35)) 
                ax.add_collection3d(poly_object)


        # ax.autoscale(enable=True, axis=u'both', tight=None)
        ax.plot(mesh.points[:,0],mesh.points[:,1],mesh.points[:,2],'o',color='#F88379')

        plt.axis('equal')
        plt.axis('off')
        # plt.savefig('/home/roman/Desktop/destination_path.eps', format='eps', dpi=1000)
        plt.show()