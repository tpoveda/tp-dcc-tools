# Set the minimum CMake version supported
cmake_minimum_required(VERSION 3.7)

# Set the project name
project(baseLoc)

# Set the CMake modules path to find the cmake Find* files
list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/../cmake)

# Set the source directories
set(PLUGIN_SOURCES_DIR ${CMAKE_CURRENT_SOURCE_DIR}/source)
set(PLUGIN_HEADERS_DIR ${CMAKE_CURRENT_SOURCE_DIR}/include)

# Glob together all the source code
file(GLOB_RECURSE PLUGIN_SOURCES ${PLUGIN_SOURCES_DIR}/*.c ${PLUGIN_SOURCES_DIR}/*.cpp)
file(GLOB_RECURSE PLUGIN_HEADERS ${PLUGIN_HEADERS_DIR}/*.h ${PLUGIN_HEADERS_DIR}/*.hpp)

# Set list of supported Maya versions. Plugin will be built for each one of the defined versions.
set(MAYA_VERSIONS "2024")

foreach(VERSION_FOUND IN LISTS MAYA_VERSIONS)

    set(Maya_FIND_VERSION_EXACT 1)
	set(Maya_FIND_VERSION ${VERSION_FOUND})

    # Use the cmake/FindMaya.cmake finder
    find_package(Maya REQUIRED)

    # Plugin Name and folder
    set(PLUGIN_NAME ${CMAKE_PROJECT_NAME}_maya${MAYA_VERSION})
    set(PLUGINS_FOLDER Plugins/Maya/${MAYA_VERSION})

    # Setup Plugin project
    add_library(${PLUGIN_NAME} SHARED ${PLUGIN_SOURCES} ${PLUGIN_HEADERS})
    set_target_properties(${PLUGIN_NAME} PROPERTIES FOLDER ${PLUGINS_FOLDER})
    target_include_directories(${PLUGIN_NAME} PRIVATE include)
    target_include_directories(${PLUGIN_NAME} PUBLIC ${MAYA_INCLUDE_DIRS} ${EIGEN_INCLUDE_DIR})
    target_link_directories(${PLUGIN_NAME} PRIVATE ${MAYA_LIBRARIES})
    target_link_libraries(${PLUGIN_NAME} PRIVATE ${MAYA_LIBRARIES})

    # this is a macro defined in FindMaya that sets up our plugin with standard Maya build settings
    MAYA_SET_PLUGIN_PROPERTIES(${PLUGIN_NAME})
    #install(TARGETS ${PLUGIN_NAME} ${MAYA_TARGET_TYPE} DESTINATION plug-ins)
endforeach()

source_group("Include" FILES ${PLUGIN_HEADERS})
source_group("Source" FILES ${PLUGIN_SOURCES})


