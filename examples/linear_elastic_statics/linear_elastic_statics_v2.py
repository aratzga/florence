import numpy as np
from Florence import *


def linear_elastic_dynamics():
    """An example of finite element simulation of linear elastodynamics with
        a 2D column of linear quad elements
    """

    mesh = Mesh()
    mesh.Rectangle(upper_right_point=(1,10), element_type="quad", nx=10, ny=100)
    ndim = mesh.InferSpatialDimension()

    # nu = 0.24  # Poisson
    # E = 38.5e3 # Young's modulus (MPa)

    v = 0.49
    mu = 1e5
    material = LinearElastic(ndim, mu=mu, lamb=2.*mu*v/(1-2.*v), density=1100)
    # Or use this material model alternatively
    #material = IncrementalLinearElastic(ndim, mu=mu, lamb=2.*mu*v/(1-2.*v), density=1100)


    aaaaa = np.arange(5)

    file = open("testfile.txt","w") 
 
    file.write("Hello World") 
    file.write("This is our new text file") 
    file.write("and this is another line.") 
    file.write("Why? Because we can.") 

    for i in range(0,5):
        file.write('{0:2d} {1:2d}\n'.format(i,aaaaa[i]))

# ...     file.write('{0:2d} {1:2d}'.format(i,aaaaa[i]))
     
    
    file.close() 


    def DirichletFuncDynamic(mesh, time_step):
        boundary_data = np.zeros((mesh.points.shape[0],ndim, time_step))+np.NAN
        # FIX BASE OF COLUMN
        Y_0 = np.isclose(mesh.points[:,1],0.0)
        boundary_data[Y_0,:,:] = 0.
        # APLLY DIRICHLET DRIVEN LOAD TO TOP OF THE COLUMN X-DIRECTION
        Y_0 = np.isclose(mesh.points[:,1],mesh.points[:,1].max())
        # boundary_data[Y_0,0,:] = np.linspace(0,2,time_step)
        boundary_data[Y_0,0,:] = 2

        return boundary_data


    # time_step = 300
    time_step = 1
    boundary_condition = BoundaryCondition()
    boundary_condition.SetDirichletCriteria(DirichletFuncDynamic, mesh, time_step)
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
    linear_elastic_dynamics()
