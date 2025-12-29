#include <iostream>
#include <vector>
#include <complex>
#include <cmath>
#include <fstream>

const double PI = 3.14159265358979323846;

int main() {
    const int sample_rate = 1000;
    const int duration_sec = 1;
    const int num_samples = sample_rate * duration_sec;
    const double frequency = 10.0;

    std::vector<std::complex<float>> signal_buffer;
    signal_buffer.reserve(num_samples);

    for (int i = 0; i < num_samples; ++i) {
        double t = (double)i / sample_rate;
        
        double angle = 2.0 * PI * frequency * t;
        
        std::complex<float> sample(cos(angle), sin(angle));
        signal_buffer.push_back(sample);
    }

    std::cout << "[+] Generated " << signal_buffer.size() << " IQ samples." << std::endl;

    std::ofstream outfile("signal_data.csv");
    outfile << "I,Q\n";
    for (const auto& s : signal_buffer) {
        outfile << s.real() << "," << s.imag() << "\n";
    }
    outfile.close();
    std::cout << "[+] Data saved to 'signal_data.csv'" << std::endl;

    return 0;
}