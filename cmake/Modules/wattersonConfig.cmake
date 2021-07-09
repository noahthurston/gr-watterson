INCLUDE(FindPkgConfig)
PKG_CHECK_MODULES(PC_WATTERSON watterson)

FIND_PATH(
    WATTERSON_INCLUDE_DIRS
    NAMES watterson/api.h
    HINTS $ENV{WATTERSON_DIR}/include
        ${PC_WATTERSON_INCLUDEDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/include
          /usr/local/include
          /usr/include
)

FIND_LIBRARY(
    WATTERSON_LIBRARIES
    NAMES gnuradio-watterson
    HINTS $ENV{WATTERSON_DIR}/lib
        ${PC_WATTERSON_LIBDIR}
    PATHS ${CMAKE_INSTALL_PREFIX}/lib
          ${CMAKE_INSTALL_PREFIX}/lib64
          /usr/local/lib
          /usr/local/lib64
          /usr/lib
          /usr/lib64
)

INCLUDE(FindPackageHandleStandardArgs)
FIND_PACKAGE_HANDLE_STANDARD_ARGS(WATTERSON DEFAULT_MSG WATTERSON_LIBRARIES WATTERSON_INCLUDE_DIRS)
MARK_AS_ADVANCED(WATTERSON_LIBRARIES WATTERSON_INCLUDE_DIRS)

