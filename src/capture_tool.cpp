// src/capture_tool.cpp
#include <iostream>
#include <fstream>
#include <vector>
#include <complex>
#include <rtl-sdr.h>
#include <thread>
#include <chrono>

// FM Radio = 98.5 MHz
// KeyFob = 313.8 MHz
int main(int argc, char* argv[]) {
    if (argc < 2) {
        std::cout << "Usage: ./capture_tool <filename_prefix> [frequency_hz]" << std::endl;
        std::cout << "Example: ./capture_tool fm_radio 98500000" << std::endl;
        return 1;
    }

    std::string prefix = argv[1];
    int freq = (argc > 2) ? std::atoi(argv[2]) : 98500000;

    std::cout << "[REC] Initializing SDR at " << freq << " Hz..." << std::endl;

    if (rtlsdr_get_device_count() == 0) {
        std::cerr << "No device found." << std::endl;
        return 1;
    }

    rtlsdr_dev_t *dev = nullptr;
    rtlsdr_open(&dev, 0);
    rtlsdr_set_center_freq(dev, freq);
    rtlsdr_set_sample_rate(dev, 1024000);
    rtlsdr_set_tuner_gain_mode(dev, 1);
    rtlsdr_set_tuner_gain(dev, 250);
    rtlsdr_reset_buffer(dev);

    // Prepare Output File
    std::string filename = prefix + ".bin";
    std::ofstream outfile(filename, std::ios::binary);
    
    std::cout << "[REC] Recording to " << filename << " for 10 seconds..." << std::endl;

    int n_read;
    const int CHUNK = 16384 * 2;
    uint8_t buffer[CHUNK];
    
    auto start_time = std::chrono::high_resolution_clock::now();
    int total_bytes = 0;

    while (true) {
        auto now = std::chrono::high_resolution_clock::now();
        if (std::chrono::duration_cast<std::chrono::seconds>(now - start_time).count() >= 10) break;

        rtlsdr_read_sync(dev, buffer, CHUNK, &n_read);
        outfile.write((char*)buffer, n_read);
        total_bytes += n_read;

        // --- NEW: CALCULATE LOUDNESS ---
        double energy = 0.0;
        for (int i=0; i<n_read; i+=2) {
            // Convert uint8 to centered float (-127 to 127)
            float i_val = (float)buffer[i] - 127.5f;
            float q_val = (float)buffer[i+1] - 127.5f;
            energy += (i_val*i_val + q_val*q_val);
        }
        energy /= (n_read/2); // Average energy per sample

        // Print Visual Bar if loud
        if (energy > 500.0) { // Threshold (adjust if needed)
            std::cout << "\r[DETECTED] Energy: " << (int)energy << " ||||||||||||||||||||" << std::flush;
        } else {
            std::cout << "\r[........] Energy: " << (int)energy << "                      " << std::flush;
        }
    }

    outfile.close();
    rtlsdr_close(dev);
    std::cout << "\n[DONE] Saved raw data." << std::endl;
    return 0;
}