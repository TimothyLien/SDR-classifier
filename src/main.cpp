#include <iostream>
#include <vector>
#include <complex>
#include <cmath>
#include <fstream>
#include "fftw3.h"

const double PI = 3.14159265358979323846;

void generate_signal(std::vector<std::complex<float>>& buffer, int num_samples, double sample_rate, double freq){
    for (int i = 0; i < num_samples; ++i) {
        double t = (double)i / sample_rate;
        double angle = 2.0 * PI * freq * t;
        buffer[i] = std::complex<float>(cos(angle), sin(angle));
    }
}

double find_peak_frequency(const std::vector<std::complex<float>>& buffer, double sample_rate){
    int N = buffer.size();

    fftw_complex* in = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * N);
    fftw_complex* out = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * N);

    fftw_plan plan = fftw_plan_dft_1d(N, in, out, FFTW_FORWARD, FFTW_ESTIMATE);

    for (int i = 0; i < N; ++i){
        in[i][0] = buffer[i].real();
        in[i][1] = buffer[i].imag();
    }

    fftw_execute(plan);

    double max_magnitude = 0.0;
    int peak_bin = 0;

    for (int i = 0; i < N; ++i){
        double mag = sqrt(out[i][0]*out[i][0] + out[i][1]*out[i][1]);
        if (mag > max_magnitude){
            max_magnitude = mag;
            peak_bin = i;
        }
    }

    fftw_destroy_plan(plan);
    fftw_free(in);
    fftw_free(out);

    double detected_freq = (double)peak_bin * sample_rate / (double)N;
    return detected_freq;
}

int main(){
    std::cout << "Starting signal generation and analysis..." << std::endl;

    const int sample_rate = 1000;
    const int num_samples = 1000;
    const double target_freq = 10.0;

    std::vector<std::complex<float>> signal_buffer(num_samples);

    generate_signal(signal_buffer, num_samples, sample_rate, target_freq);
    std::cout << "Signal generated with frequency: " << target_freq << " Hz" << std::endl;

    double detected = find_peak_frequency(signal_buffer, sample_rate);

    std::cout << "Detected peak frequency: " << detected << " Hz" << std::endl;

    if (abs(detected - target_freq) < 0.1){
        std::cout << "Frequency detection successful!" << std::endl;
    } else {
        std::cout << "Frequency detection failed!" << std::endl;
    }
    return 0;
}