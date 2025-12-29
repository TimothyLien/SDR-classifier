cmake_minimum_required(VERSION 3.10)
project(SDR_Project)

set(CMAKE_CXX_STANDARD 17)

set(HOMEBREW_PREFIX "/opt/homebrew")
include_directories(${HOMEBREW_PREFIX}/include)
link_directories(${HOMEBREW_PREFIX}/lib)

find_library(FFTW3_LIB NAMES fftw3 PATHS ${HOMEBREW_PREFIX}/lib)

if(NOT FFTW3_LIB)
    message(FATAL_ERROR "Could not find fftw3!")
endif()

include_directories(include)

add_executable(SDR_App src/main.cpp)

target_link_libraries(SDR_App PRIVATE ${FFTW3_LIB})