import math
import os
import textwrap

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import load, save
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    test_type = "explicit"

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str, run=True)

    def layout(self):
        basic_layout(self)

    @staticmethod
    def _channel_mesh(nx=24, ny=8, length=3.0, height=1.0, bump=0.1):
        # A structured quad mesh of a channel with a circular-arc-like bump on the
        # lower wall between x=1 and x=2, in SU2's native format: VTK element type 9
        # is a quadrilateral, 3 a line.
        def node(i, j):
            return j * (nx + 1) + i

        lines = ["NDIME= 2", f"NELEM= {nx * ny}"]
        for j in range(ny):
            for i in range(nx):
                quad = (node(i, j), node(i + 1, j), node(i + 1, j + 1), node(i, j + 1))
                lines.append("9 " + " ".join(map(str, quad)) + f" {j * nx + i}")
        lines.append(f"NPOIN= {(nx + 1) * (ny + 1)}")
        for j in range(ny + 1):
            for i in range(nx + 1):
                x = length * i / nx
                y_wall = bump * math.sin(math.pi * (x - 1.0)) ** 2 if 1.0 <= x <= 2.0 else 0.0
                y = y_wall + (height - y_wall) * j / ny
                lines.append(f"{x:.6f} {y:.6f} {node(i, j)}")
        markers = {
            "lower": [(node(i, 0), node(i + 1, 0)) for i in range(nx)],
            "upper": [(node(i + 1, ny), node(i, ny)) for i in range(nx)],
            "inlet": [(node(0, j + 1), node(0, j)) for j in range(ny)],
            "outlet": [(node(nx, j), node(nx, j + 1)) for j in range(ny)],
        }
        lines.append(f"NMARK= {len(markers)}")
        for tag, edges in markers.items():
            lines += [f"MARKER_TAG= {tag}", f"MARKER_ELEMS= {len(edges)}"]
            lines += [f"3 {a} {b}" for a, b in edges]
        return "\n".join(lines) + "\n"

    def test(self):
        if not can_run(self):
            return
        save(self, "channel.su2", self._channel_mesh())
        # Inviscid flow over a bump in a channel: walls top and bottom, free stream in
        # and out. A handful of implicit iterations exercises the mesh reader, the
        # partitioner (ParMETIS when run with MPI), the solver and the output writers.
        config = textwrap.dedent("""\
            SOLVER= EULER
            MACH_NUMBER= 0.5
            AOA= 0.0
            FREESTREAM_PRESSURE= 101325.0
            FREESTREAM_TEMPERATURE= 288.15
            REF_DIMENSIONALIZATION= DIMENSIONAL
            MARKER_EULER= ( lower, upper )
            MARKER_FAR= ( inlet, outlet )
            MARKER_MONITORING= ( lower )
            OBJECTIVE_FUNCTION= DRAG
            NUM_METHOD_GRAD= WEIGHTED_LEAST_SQUARES
            CFL_NUMBER= 10.0
            LINEAR_SOLVER= FGMRES
            LINEAR_SOLVER_PREC= ILU
            LINEAR_SOLVER_ERROR= 1E-6
            LINEAR_SOLVER_ITER= 5
            CONV_NUM_METHOD_FLOW= ROE
            TIME_DISCRE_FLOW= EULER_IMPLICIT
            CONV_RESIDUAL_MINVAL= -12
            MESH_FILENAME= channel.su2
            MESH_FORMAT= SU2
            TABULAR_FORMAT= CSV
            RESTART_FILENAME= restart_flow
            SOLUTION_FILENAME= restart_flow
            VOLUME_FILENAME= flow
            OUTPUT_FILES= ( RESTART, PARAVIEW )
            """)
        save(self, "channel.cfg", config + textwrap.dedent("""\
            MATH_PROBLEM= DIRECT
            ITER= 10
            CONV_FIELD= RMS_DENSITY
            CONV_FILENAME= history
            """))
        # The discrete adjoint of the drag, started from the flow solution above.
        save(self, "channel_adjoint.cfg", config + textwrap.dedent("""\
            MATH_PROBLEM= DISCRETE_ADJOINT
            ITER= 3
            CONV_FIELD= RMS_ADJ_DENSITY
            CONV_FILENAME= history_adjoint
            RESTART_ADJ_FILENAME= restart_adj
            VOLUME_ADJ_FILENAME= adjoint
            """))

        options = self.dependencies["su2"].options
        # --oversubscribe: CI runners may report fewer slots than requested.
        launcher = "mpirun --oversubscribe -np 2 " if options.with_mpi else ""
        self.run(f"{launcher}SU2_CFD channel.cfg", env="conanrun")

        history = load(self, "history.csv").strip().splitlines()
        # Header plus one line per iteration.
        if len(history) < 2:
            raise RuntimeError("SU2_CFD wrote no iterations to history.csv")
        for output in ("restart_flow.dat", "flow.vtu"):
            if not os.path.isfile(output):
                raise RuntimeError(f"SU2_CFD did not write {output}")
        self.output.info(f"{len(history) - 1} iterations, last: {history[-1]}")

        if options.with_autodiff:
            self.run(f"{launcher}SU2_CFD_AD channel_adjoint.cfg", env="conanrun")
            adjoint = load(self, "history_adjoint.csv").strip().splitlines()
            if len(adjoint) < 2:
                raise RuntimeError("SU2_CFD_AD wrote no iterations to history_adjoint.csv")
            self.output.info(f"adjoint: {len(adjoint) - 1} iterations, last: {adjoint[-1]}")
