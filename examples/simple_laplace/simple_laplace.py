import numpy as np
from Florence import *


def simple_laplace():
<<<<<<< HEAD
    """An example of solving simple laplace equation using
        fourth order hexahedral elements on a cube
    """

    mesh = Mesh()
    mesh.Cube(element_type="hex",nx=6,ny=6,nz=6)
    mesh.GetHighOrderMesh(p=4)

    def DirichletFunc(mesh):
        boundary_data = np.zeros((mesh.points.shape[0]))+np.NAN
=======
    """An example of solving the Laplace equation using
        fourth order hexahedral elements on a cube
    """

    # generate a linear hexahedral mesh on a cube
    mesh = Mesh()
    mesh.Cube(element_type="hex", nx=6, ny=6, nz=6)
    # generate the corresponding fourth order mesh
    mesh.GetHighOrderMesh(p=4)

    # set up boundary conditions
    def dirichlet_function(mesh):
        # create boundary flags - nan values would be treated as free boundary
        boundary_data = np.zeros(mesh.nnode)+np.NAN
>>>>>>> upstream/master
        # potential at left (Y=0)
        Y_0 = np.isclose(mesh.points[:,1],0)
        boundary_data[Y_0] = 0.
        # potential at right (Y=1)
        Y_1 = np.isclose(mesh.points[:,1],mesh.points[:,1].max())
        boundary_data[Y_1] = 10.
<<<<<<< HEAD
        return boundary_data


    boundary_condition = BoundaryCondition()
    boundary_condition.SetDirichletCriteria(DirichletFunc, mesh)

    material = IdealDielectric(mesh.InferSpatialDimension(),eps_1=2.35)
    formulation = LaplacianFormulation(mesh)
    fem_solver = FEMSolver(optimise=True)

    solution = fem_solver.Solve(boundary_condition=boundary_condition,
=======

        return boundary_data

    boundary_condition = BoundaryCondition()
    boundary_condition.SetDirichletCriteria(dirichlet_function, mesh)

    # set up material
    material = IdealDielectric(mesh.InferSpatialDimension(), eps=2.35)
    # set up variational form
    formulation = LaplacianFormulation(mesh)
    # set up solver
    fem_solver = FEMSolver(optimise=True)
    # solve
    results = fem_solver.Solve( boundary_condition=boundary_condition,
>>>>>>> upstream/master
                                material=material,
                                formulation=formulation,
                                mesh=mesh)

<<<<<<< HEAD
    # Write results to vtk file
    # solution.WriteVTK("results", quantity=4)
=======
    # write results to vtk file
    # results.WriteVTK("laplacian_results")
>>>>>>> upstream/master


if __name__ == "__main__":
    simple_laplace()