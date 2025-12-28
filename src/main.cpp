#include <iostream>
#include <vector>
#include <complex> // The standard C++ complex number library
#include <cmath>
#include <fstream> // For writing to files

// Constants
const double PI = 3.14159265358979323846;

int main() {
    std::cout << "[*] Starting Signal Generator..." << std::endl;

    // Simulation Parameters
    const int sample_rate = 1000;  // 1000 samples per second
    const int duration_sec = 1;    // 1 second of data
    const int num_samples = sample_rate * duration_sec;
    const double frequency = 10.0; // 10 Hz tone

    // The Buffer: A vector of complex floats (Standard for SDR)
    std::vector<std::complex<float>> signal_buffer;
    signal_buffer.reserve(num_samples);

    // Generate the Signal (Euler's Formula: e^(j*2*pi*f*t))
    for (int i = 0; i < num_samples; ++i) {
        double t = (double)i / sample_rate; // Current time
        
        // IQ Math: 
        // Real part (I) = cos(2*pi*f*t)
        // Imag part (Q) = sin(2*pi*f*t)
        double angle = 2.0 * PI * frequency * t;
        
        std::complex<float> sample(cos(angle), sin(angle));
        signal_buffer.push_back(sample);
    }

    std::cout << "[+] Generated " << signal_buffer.size() << " IQ samples." << std::endl;

    // Save to CSV so we can check our work in Python later
    std::ofstream outfile("signal_data.csv");
    outfile << "I,Q\n"; // Header
    for (const auto& s : signal_buffer) {
        outfile << s.real() << "," << s.imag() << "\n";
    }
    outfile.close();
    std::cout << "[+] Data saved to 'signal_data.csv'" << std::endl;

    return 0;
}