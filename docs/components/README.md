# Extensible components in pybm

`pybm` can be customized at a few key spots to fit its user's needs. The three important (class) components for pybm
customization are:

* The `VenvBuilder`, a class managing the lifecycle of Python virtual environments.
* The `BenchmarkRunner`, responsible for discovering, dispatching benchmarks and saving the results.
* The `BenchmarkReporter`, responsible for loading, formatting and presenting benchmark results.

Each of these components are covered in more detail in their respective Markdown documents. They include some guidance
on how to extend these components for your own experience with `pybm`.