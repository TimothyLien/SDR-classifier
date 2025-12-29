#include <iostream>
#include <vector>
#include <complex>
#include <cmath>
#include <thread>
#include <chrono>
#include <atomic>
#include <zmq.h>
#include "safe_queue.h"
#include <message.pb.h>
#include <fftw3.h>

// Type Alias: A "Chunk" of IQ data
using IQBlock = std::vector<std::complex<float>>;

SafeQueue<IQBlock> q;
std::atomic<bool> running(true);

const double PI = 3.14159265358979323846;

// Producer Thread: Simulates Radio Hardware
void radio_producer() {
    std::cout << "[Producer] Started. Simulating incoming radio data..." << std::endl;
    
    int sample_rate = 240000; // 240k samples/sec
    int block_size = 1024;    // We send data in blocks of 1024 samples
    double frequency = 1000.0; // 1 kHz test tone
    int counter = 0;

    while (running) {
        IQBlock block(block_size);

        // Generate a chunk of data (Fake Sine Wave)
        for (int i = 0; i < block_size; ++i) {
            double t = (double)(counter * block_size + i) / sample_rate;
            double angle = 2.0 * PI * frequency * t;
            block[i] = std::complex<float>(cos(angle), sin(angle));
        }
        counter++;

        q.push(block);

        // Simulates Hardware Latency
        std::this_thread::sleep_for(std::chrono::milliseconds(10)); 
    }
    std::cout << "[Producer] Stopped." << std::endl;
}

// Consumer Thread: Processes IQ Data
void dsp_consumer() {
    std::cout << "[Consumer] Connecting to Nerwork (Port 5555)..." << std::endl;
    
    void* context = zmq_ctx_new();
    void* publisher = zmq_socket(context, ZMQ_PUB);
    int rc = zmq_bind(publisher, "tcp://*:5555"); // Bind to port 5555
    if (rc != 0) {
        std::cerr << "[Consumer] Failed to bind to port 5555." << std::endl;
        return;
    }

    int N = 1024;
    fftw_complex* in = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * N);
    fftw_complex* out = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * N);
    fftw_plan plan = fftw_plan_dft_1d(N, in, out, FFTW_FORWARD, FFTW_ESTIMATE);

    while (running) {
        IQBlock block;
        q.pop(block);

        for(int i=0; i<N; i++) {
            in[i][0] = block[i].real();
            in[i][1] = block[i].imag();
        }
        fftw_execute(plan);

        double max_mag = 0;
        int peak_bin = 0;
        for(int i=0; i<N; i++) {
             double mag = sqrt(out[i][0]*out[i][0] + out[i][1]*out[i][1]);
             if(mag > max_mag) { max_mag = mag; peak_bin = i; }
        }
        
        radio::SignalResult result;
        result.set_timestamp(time(NULL));
        result.set_peak_bin_index(peak_bin);
        result.set_signal_strength(max_mag);
        result.set_center_frequency(1000.0); // Dummy value
        result.set_modulation("TEST_TONE");

        std::string payload;
        result.SerializeToString(&payload);

        zmq_send(publisher, payload.data(), payload.size(), 0);

        static int print_count = 0;
        if (print_count++ % 50 == 0) {
            std::cout << "[Consumer] Processed Block. Peak Bin: " << peak_bin 
                      << " (Queue Size: " << q.size() << ")" << std::endl;
        }
    }

    // Cleanup
    zmq_close(publisher);
    zmq_ctx_destroy(context);
    fftw_destroy_plan(plan);
    fftw_free(in); fftw_free(out);
    std::cout << "[Consumer] Stopped." << std::endl;
}

int main() {
    std::cout << "[Main] Starting SDR..." << std::endl;

    std::thread t1(radio_producer);
    std::thread t2(dsp_consumer);

    std::this_thread::sleep_for(std::chrono::seconds(10));

    std::cout << "[Main] Shutting down..." << std::endl;
    running = false;

    t1.detach();
    t2.detach();

    std::cout << "[Main] Done." << std::endl;
    return 0;
}