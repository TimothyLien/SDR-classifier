cmake_minimum_required(VERSION 3.10)
project(SDR_Pro)

set(CMAKE_CXX_STANDARD 17)

include_directories("/opt/homebrew/include")
include_directories(include)

set(HOMEBREW_PREFIX "/opt/homebrew")
list(APPEND CMAKE_PREFIX_PATH "${HOMEBREW_PREFIX}")

find_package(absl CONFIG REQUIRED)
find_package(Protobuf CONFIG REQUIRED)
find_library(FFTW3_LIB NAMES fftw3 PATHS ${HOMEBREW_PREFIX}/lib)
find_library(ZMQ_LIB NAMES zmq PATHS ${HOMEBREW_PREFIX}/lib)

set(Torch_DIR "/Users/timothylien/SDR_project/venv/lib/python3.13/site-packages/torch/share/cmake/Torch") 
find_package(Torch REQUIRED)

add_executable(SDR_App src/main.cpp src/message.pb.cc)

target_link_libraries(SDR_App 
    PRIVATE 
    ${FFTW3_LIB} 
    ${ZMQ_LIB} 
    "/opt/homebrew/lib/librtlsdr.dylib"
    protobuf::libprotobuf 
    ${TORCH_LIBRARIES} 
    absl::base
)