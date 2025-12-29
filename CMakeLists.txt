cmake_minimum_required(VERSION 3.10)
project(SDR_Pro)

set(CMAKE_CXX_STANDARD 17)

set(HOMEBREW_PREFIX "/opt/homebrew")
list(APPEND CMAKE_PREFIX_PATH "${HOMEBREW_PREFIX}")

find_package(absl CONFIG REQUIRED)

find_package(Protobuf CONFIG REQUIRED)

find_library(FFTW3_LIB NAMES fftw3 PATHS ${HOMEBREW_PREFIX}/lib)
find_library(ZMQ_LIB NAMES zmq PATHS ${HOMEBREW_PREFIX}/lib)

include_directories(include)

add_executable(SDR_App src/main.cpp src/message.pb.cc)

target_link_libraries(SDR_App 
    PRIVATE 
    ${FFTW3_LIB} 
    ${ZMQ_LIB} 
    protobuf::libprotobuf
    absl::base
)