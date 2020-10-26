Transmute is a framework for building packages and for managing the
dependencies of a package on other packages. It provides a common
interface to configuring and building any package, but it is not a
build system like make or cmake. You will still need platform-specific
make, cmake, or project files to configure and build your
library. Transmute will, however, allow you invoke these commands and
package the product with a common interface.

To install run

`pip install transmute --extra-index-url https://pkg.alchemyviewer.org/repository/autobuild/simple`
