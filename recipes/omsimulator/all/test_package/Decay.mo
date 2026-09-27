model Decay
  "x' = -k*x, exported as an FMU and co-simulated by the test package"
  parameter Real k = 1.0;
  Real x(start = 1.0, fixed = true);
  // Pulls in the Modelica Standard Library, which the package bundles.
  Modelica.Units.SI.Time t = time;
equation
  der(x) = -k * x;
end Decay;
