import math
import os
import textwrap

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import load, mkdir, save
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
    def _nemoh_cal(mesh_file, points, panels, depth, free_surface):
        # One body moving in heave only, one frequency (1 rad/s), one wave direction.
        return textwrap.dedent(f"""\
            --- Environment ---
            1000.0          ! RHO
            9.81            ! G
            {depth}         ! DEPTH (0 for infinite depth)
            0. 0.           ! XEFF YEFF
            --- Description of floating bodies ---
            1               ! Number of bodies
            --- Body 1 ---
            {mesh_file}     ! Name of mesh file
            {points} {panels}   ! Number of points and number of panels
            1               ! Number of degrees of freedom
            1 0. 0. 1. 0. 0. 0.     ! Heave
            1               ! Number of resulting generalised forces
            1 0. 0. 1. 0. 0. 0.     ! Heave
            0               ! Number of lines of additional information
            --- Load cases to be solved ---
            1 1 1. 1.       ! Freq type, number of frequencies, min and max
            1 0. 0.         ! Number of wave directions, min and max (degrees)
            --- Post processing ---
            0 0.1 10.       ! IRF
            0               ! Show pressure
            0 0. 180.       ! Kochin function
            {free_surface}  ! Free surface elevation
            0               ! RAO
            1               ! Output freq type
            ---QTF---
            0               ! QTF flag
            """)

    @staticmethod
    def _half_sphere():
        # The unit half sphere of upstream's TestCases/5_QuickTests/1_Sphere: a 7x7
        # grid of nodes from the waterline at y<0 down through the bottom to the
        # waterline at y>0, 36 panels, in Nemoh's own mesh format.
        n = 7
        lines = ["2 0"]
        for j in range(n):
            psi = math.radians(30 * j)
            for k in range(n):
                phi = math.radians(30 * k)
                x = -math.cos(phi) * abs(math.cos(psi))
                y = -math.sin(phi) * math.cos(psi)
                z = -math.sin(psi)
                lines.append(f"{j * n + k + 1} {x:.6f} {y:.6f} {z:.6f}")
        lines.append("0 0 0 0")
        for j in range(n - 1):
            for k in range(n - 1):
                a = j * n + k + 1
                lines.append(f"{a} {a + n} {a + n + 1} {a + 1}")
        lines.append("0 0 0 0")
        return "\n".join(lines) + "\n", n * n, (n - 1) ** 2

    @staticmethod
    def _box_geometry(lx=10.0, ly=10.0, draft=5.0):
        # Coarse description of a rectangular barge for the mesh program: the four
        # sides and the bottom, one quadrilateral each, normals pointing out.
        x, y, z = lx / 2, ly / 2, -draft
        faces = [
            [(-x, y, z), (-x, -y, z), (-x, -y, 0), (-x, y, 0)],
            [(x, -y, z), (x, y, z), (x, y, 0), (x, -y, 0)],
            [(-x, -y, z), (x, -y, z), (x, -y, 0), (-x, -y, 0)],
            [(x, y, z), (-x, y, z), (-x, y, 0), (x, y, 0)],
            [(-x, -y, z), (-x, y, z), (x, y, z), (x, -y, z)],
        ]
        lines = [str(4 * len(faces)), str(len(faces))]
        lines += [f"{px} {py} {pz}" for face in faces for (px, py, pz) in face]
        lines += [" ".join(str(4 * i + c + 1) for c in range(4)) for i in range(len(faces))]
        return "\n".join(lines) + "\n", lx * ly * draft

    def _run(self, program, case):
        self.run(f"{program} {case}", env="conanrun")

    def test(self):
        if not can_run(self):
            return

        solver_input = textwrap.dedent("""\
            2           ! Gauss quadrature N (N^2 nodes)
            0.001       ! eps_zmin
            1           ! Linear solver: 0 Gauss elimination, 1 LU, 2 GMRES
            10 1e-5 1000    ! GMRES restart, tolerance, max iterations
            """)

        # Radiation and diffraction around a half sphere in infinite depth:
        # preProc, solver (LAPACK) and postProc, against upstream's reference results.
        mkdir(self, "sphere")
        mesh, points, panels = self._half_sphere()
        save(self, os.path.join("sphere", "Half_sphere.dat"), mesh)
        save(self, os.path.join("sphere", "Nemoh.cal"),
             self._nemoh_cal("Half_sphere.dat", points, panels, "0.", "5 5 100. 100."))
        save(self, os.path.join("sphere", "input_solver.txt"), solver_input)
        for program in ("preProc", "solver", "postProc"):
            self._run(program, "sphere")

        forces = [float(v) for v in load(self, os.path.join("sphere", "results", "Forces.dat")).split()]
        # TestCases/5_QuickTests/1_Sphere/reference_results/Forces.dat
        reference = [1834.87524, -2.93322182, 1819.62512, 379.393982]
        if len(forces) != len(reference) or any(
            abs(f - r) > 0.02 * abs(r) for f, r in zip(forces, reference)
        ):
            raise RuntimeError(f"Forces.dat {forces} differs from the reference {reference}")
        if not os.path.isfile(os.path.join("sphere", "results", "freesurface.00001.tec")):
            raise RuntimeError("postProc did not write the free surface elevation")
        self.output.info(f"half sphere, Forces.dat: {forces}")

        # Meshing and hydrostatics of a 10 m x 10 m barge with a 5 m draft.
        mkdir(self, "box")
        geometry, volume = self._box_geometry()
        save(self, os.path.join("box", "box"), geometry)
        save(self, os.path.join("box", "Mesh.cal"), textwrap.dedent("""\
            box
            0               ! Not a symmetric half mesh
            0. 0.           ! Translation in x and y
            0. 0. -2.5      ! Centre of gravity
            100             ! Target number of panels
            2               ! Minimum subdivision of a geometric panel
            0.
            1.              ! Scaling factor
            1000.           ! Water density
            9.81            ! Gravity
            """))
        self._run("mesh", "box")
        points, panels = (int(v) for v in load(self, os.path.join("box", "mesh", "box_info.dat")).split()[:2])
        save(self, os.path.join("box", "Nemoh.cal"),
             self._nemoh_cal("mesh/box.dat", points, panels, "0.", "0 50 400. 400."))
        save(self, os.path.join("box", "input_solver.txt"), solver_input)
        self._run("preProc", "box")
        self._run("hydrosCal", "box")

        hydrostatics = load(self, os.path.join("box", "mesh", "Hydrostatics.dat"))
        displacement = next(
            float(line.split("=")[1]) for line in hydrostatics.splitlines() if "Displacement" in line
        )
        if abs(displacement - volume) > 1e-3 * volume:
            raise RuntimeError(f"hydrosCal: displacement {displacement}, expected {volume}")
        self.output.info(f"barge: {panels} panels, displacement {displacement} m^3")
