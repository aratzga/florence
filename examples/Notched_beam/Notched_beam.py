import numpy as np
from Florence import *


def Notched_beam():
    """Manzoli beam (linear elastic)
    """


# MESHNG:
#------------

    mesh = Mesh()
    mesh.ReadGmsh(os.path.join(PWD(__file__),"notched_beam_Manzoli.msh"),element_type="tri")
    ndim = mesh.InferSpatialDimension()

    poissons_ratio = 0.24  # Poisson
    youngs_modulus = 38.5e3 # Young's modulus (MPa)

    # def YoungPoisson2Lamel(poissons_ratio,youngs_modulus)
    #    E = youngs_modulus
    #    v = poissons_ratio
    #    lamb = v*E/((1+v)*(1-2*v))  # lame_parameter_2
    #    mu = 0.5*E/(1+v) # lame_parameter_1
    #   # Only is implemented plane strain: .../florence/MaterialLibrary/MaterialBase.py (line 70-80)

    #   return mu, lamb

    lamb = poissons_ratio*youngs_modulus/((1+poissons_ratio)*(1-2*poissons_ratio))  # lame_parameter_2
    mu = 0.5*youngs_modulus/(1+poissons_ratio) # lame_parameter_1
    # mu = 0.24  # Poisson
    # E = 38.5e3 # Young's modulus (MPa)

# MATERIAL:
#-------------

    material = LinearElastic(ndim, mu=mu, lamb=lamb)

# BOUNDARY CONDITIONS:
#------------------------

    def DirichletFuncStatic(mesh, time_step):
        boundary_data = np.zeros((mesh.points.shape[0],ndim, time_step))+np.NAN


        # FIX NODE ON THE LEFT SUPPORT (LS): 
        tole_data = 1e-3 # In case the nodes aren't exactly on the boundary (tolerance)
        Y_0 = np.logical_and(np.isclose(mesh.points[:,1],0.0,tole_data),\
            np.isclose(mesh.points[:,0],80,tole_data))

        boundary_data[Y_0,:,:] = 0.

        # FIX NODE ON THE RIGHT SUPPORT:
        tole_data = 1e-3 # In case the nodes aren't exactly on the boundary (tolerance)
        Y_0 = np.logical_and(np.isclose(mesh.points[:,1],0.0,tole_data),\
            np.isclose(mesh.points[:,0],560,tole_data))

        boundary_data[Y_0,1,:] = 0.


        # APPLY DISPLAMENT ON THE CENTER OF THE BEAM:
        tole_data = 1e-3 # In case the nodes aren't exactly on the boundary (tolerance)
        Y_0 = np.logical_and(np.isclose(mesh.points[:,1],160,tole_data),\
            np.isclose(mesh.points[:,0],320,tole_data))

        boundary_data[Y_0,1,:] = -20

        return boundary_data


    # def DirichletFuncDynamic(mesh, time_step):
    #     boundary_data = np.zeros((mesh.points.shape[0],ndim, time_step))+np.NAN

    #     # FIX BASE OF COLUMN
    #     Y_0 = np.isclose(mesh.points[:,1],0.0)
    #     boundary_data[Y_0,:,:] = 0.

    #     # APLLY DIRICHLET DRIVEN LOAD TO TOP OF THE COLUMN X-DIRECTION
    #     Y_0 = np.isclose(mesh.points[:,1],mesh.points[:,1].max())
    #     boundary_data[Y_0,0,:] = 2

    #     # APLLY DIRICHLET DRIVEN LOAD TO TOP OF THE COLUMN X-DIRECTION
    #     Y_0 = np.isclose(mesh.points[:,1],mesh.points[:,1].max())
    #     boundary_data[Y_0,0,:] = 2



    #     return boundary_data


    # time_step = 300
    time_step = 1
    boundary_condition = BoundaryCondition()
    boundary_condition.SetDirichletCriteria(DirichletFuncStatic, mesh, time_step)
    #It doesn't work:  boundary_condition.SetDirichletCriteria(DirichletFuncStatic, mesh)


    formulation = DisplacementFormulation(mesh)

    #fem_solver = FEMSolver(total_time=60.,
     #   number_of_load_increments=time_step,
     #   analysis_nature="linear",
     #   analysis_type="dynamic",
     #   optimise=True,
     #   print_incremental_log=True)

    fem_solver = FEMSolver(analysis_nature="linear",
        #number_of_load_increments=time_step,
        analysis_type="static",
        optimise=True,
        print_incremental_log=True)

    solution = fem_solver.Solve(formulation=formulation, mesh=mesh,
            material=material, boundary_condition=boundary_condition)

    # Write results
    solution.WriteVTK("linear_dynamic_results", quantity="all")


if __name__ == "__main__":
    Notched_beam()
