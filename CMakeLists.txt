cmake_minimum_required(VERSION 3.10)
project(SDR_Project)

set(CMAKE_CXX_STANDARD 17)

# Standard C++ Setup
include_directories(include)

# Define the executable
add_executable(SDR_App src/main.cpp)