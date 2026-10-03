// Solves a 1D Poisson system (tridiagonal, Dirichlet ends) with AztecOO CG,
// preconditioned once with Ifpack ILU and once with ML smoothed aggregation.
#include <Epetra_ConfigDefs.h>
#ifdef HAVE_MPI
#include <Epetra_MpiComm.h>
#include <mpi.h>
#else
#include <Epetra_SerialComm.h>
#endif
#include <AztecOO.h>
#include <Epetra_CrsMatrix.h>
#include <Epetra_LinearProblem.h>
#include <Epetra_Map.h>
#include <Epetra_Vector.h>
#include <Ifpack.h>
#include <ml_MultiLevelPreconditioner.h>
#include <Teuchos_ParameterList.hpp>
#include <Teuchos_RCP.hpp>
#include <Trilinos_version.h>

#include <cmath>
#include <cstdio>

static int solve(const Epetra_Comm &comm, const char *preconditioner)
{
  const int  n = 200;
  Epetra_Map map(n, 0, comm);

  Epetra_CrsMatrix A(Copy, map, 3);
  for (int i = 0; i < map.NumMyElements(); ++i)
    {
      const int row = map.GID(i);
      double    values[3];
      int       columns[3];
      int       count = 0;
      if (row > 0)
        {
          values[count] = -1.0;
          columns[count++] = row - 1;
        }
      values[count] = 2.0;
      columns[count++] = row;
      if (row < n - 1)
        {
          values[count] = -1.0;
          columns[count++] = row + 1;
        }
      A.InsertGlobalValues(row, count, values, columns);
    }
  A.FillComplete();

  Epetra_Vector x(map), b(map), exact(map);
  exact.Random();
  A.Multiply(false, exact, b);

  Epetra_LinearProblem problem(&A, &x, &b);
  AztecOO solver(problem);
  solver.SetAztecOption(AZ_solver, AZ_cg);
  solver.SetAztecOption(AZ_output, AZ_none);

  Teuchos::RCP<Ifpack_Preconditioner>             ilu;
  Teuchos::RCP<ML_Epetra::MultiLevelPreconditioner> ml;
  if (std::string(preconditioner) == "ILU")
    {
      Ifpack factory;
      ilu = Teuchos::rcp(factory.Create("ILU", &A, 0));
      Teuchos::ParameterList list;
      ilu->SetParameters(list);
      ilu->Initialize();
      ilu->Compute();
      solver.SetPrecOperator(ilu.get());
    }
  else
    {
      Teuchos::ParameterList list;
      ML_Epetra::SetDefaults("SA", list);
      list.set("ML output", 0);
      ml = Teuchos::rcp(new ML_Epetra::MultiLevelPreconditioner(A, list));
      solver.SetPrecOperator(ml.get());
    }
  solver.Iterate(1000, 1e-10);

  x.Update(-1.0, exact, 1.0);
  double error;
  x.NormInf(&error);
  if (comm.MyPID() == 0)
    std::printf("CG + %s: %d iterations, max error %.3e\n",
                preconditioner, solver.NumIters(), error);
  return error < 1e-6 ? 0 : 1;
}

int main(int argc, char *argv[])
{
#ifdef HAVE_MPI
  MPI_Init(&argc, &argv);
  {
    Epetra_MpiComm comm(MPI_COMM_WORLD);
#else
  (void)argc;
  (void)argv;
  {
    Epetra_SerialComm comm;
#endif
    if (comm.MyPID() == 0)
      std::printf("Trilinos %s on %d rank(s)\n", TRILINOS_VERSION_STRING, comm.NumProc());
    int status = solve(comm, "ILU") + solve(comm, "ML");
    if (status != 0)
      return status;
  }
#ifdef HAVE_MPI
  MPI_Finalize();
#endif
  return 0;
}
