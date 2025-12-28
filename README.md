# C++ SDR Signal Classifier

## Overview
This project is a high-performance signal processing and classification pipeline designed for Software Defined Radio (SDR) applications. It is built in C++ to simulate deployment constraints on embedded edge devices (e.g., NVIDIA Jetson).

## Architecture
The pipeline consists of three stages:
1. **Signal Acquisition:** Interfacing with RTL-SDR hardware to ingest raw IQ data.
2. **Signal Processing:** Using `FFTW3` and `Liquid-DSP` for filtering and Fast Fourier Transforms.
3. **Inference:** A PyTorch-based Deep Learning model deployed via `LibTorch` (C++) for modulation classification.

## Current Status
WIP

## Build Instructions
```bash
mkdir build && cd build
cmake ..
make
./SDR_App