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
#include <torch/script.h>
#include <rtl-sdr.h>

// Type Alias: A "Chunk" of IQ data
using IQBlock = std::vector<std::complex<float>>;

SafeQueue<IQBlock> q;
std::atomic<bool> running(true);

const double PI = 3.14159265358979323846;

// RTL-SDR Driver Thread
void sdr_driver() {
    std::cout << "[SDR] Initializing Hardware..." << std::endl;

    if (rtlsdr_get_device_count() == 0) {
        std::cerr << "[SDR] Error: No dongle found!" << std::endl;
        return;
    }

    rtlsdr_dev_t *dev = nullptr;
    if (rtlsdr_open(&dev, 0) < 0) {
        std::cerr << "[SDR] Error opening device." << std::endl;
        return;
    }

    // Tune to FM Radio (98.5 MHz)
    rtlsdr_set_center_freq(dev, 98500000); 
    rtlsdr_set_sample_rate(dev, 1024000); 
    rtlsdr_set_tuner_gain_mode(dev, 1);
    rtlsdr_set_tuner_gain(dev, 250); // 25.0 dB
    rtlsdr_reset_buffer(dev);

    std::cout << "[SDR] Hardware Locked. Tuning to 98.5 MHz." << std::endl;

    int n_read;
    int buffer_size = 1024 * 2; 
    uint8_t buffer[buffer_size]; 

    while (running) {
        if (rtlsdr_read_sync(dev, buffer, buffer_size, &n_read) < 0) break;

        IQBlock block;
        block.reserve(1024);
        for (int i = 0; i < n_read; i += 2) {
            float i_val = (buffer[i] - 127.5f) / 127.5f;     
            float q_val = (buffer[i+1] - 127.5f) / 127.5f;   
            block.push_back(std::complex<float>(i_val, q_val));
        }
        q.push(block);
    }
    rtlsdr_close(dev);
}

// Producer Thread: Simulates Radio Hardware
void radio_producer() {
    std::cout << "[Producer] Started. Simulating incoming radio data..." << std::endl;
    
    int sample_rate = 240000; // 240k samples/sec
    int block_size = 1024;    // We send data in blocks of 1024 samples
    double frequency = 100.0; // 1 kHz test tone
    int counter = 0;

    while (running) {
        IQBlock block(block_size);

        int mode = (counter / 50) % 3;

        // For BPSK phase tracking
        static double phase_offset = 0.0; 

        for (int i = 0; i < block_size; ++i) {
            double t = (double)(counter * block_size + i) / sample_rate;

            if (mode == 0) {
                // Noise
                float r1 = ((rand() % 200) / 100.0f) - 1.0f; 
                float r2 = ((rand() % 200) / 100.0f) - 1.0f;
                block[i] = std::complex<float>(r1, r2);
            } 
            else if (mode == 1) {
                // Sine Wave
                block[i] = std::complex<float>(
                    cos(2 * PI * frequency * t), 
                    sin(2 * PI * frequency * t)
                );
            } 
            else if (mode == 2) {
                // Active BPSK
                if ((counter * block_size + i) % 100 == 0) {
                     // Randomly decide to flip or not (50% chance)
                     if (rand() % 2 == 0) {
                         phase_offset += PI;
                     }
                }
                block[i] = std::complex<float>(
                    cos(2 * PI * frequency * t + phase_offset), 
                    sin(2 * PI * frequency * t + phase_offset)
                );
            }
        }
        counter++;
        q.push(block);
        std::this_thread::sleep_for(std::chrono::milliseconds(20));
    }
    std::cout << "[Producer] Stopped." << std::endl;
}

// Consumer Thread: Processes IQ Data
void dsp_consumer() {
    std::cout << "[Consumer] Connecting to Network (Port 5555)..." << std::endl;
    
    torch::jit::script::Module model;
    try { 
        // Load the model
        model = torch::jit::load("radio_model.pt"); 
        std::cout << "[Consumer] AI Model Loaded Successfully." << std::endl;
    } 
    catch (const c10::Error& e) { 
        std::cerr << "[Consumer] CRITICAL ERROR: Could not load 'radio_model.pt'!" << std::endl;
        std::cerr << "Make sure the file is in the 'build' folder." << std::endl;
        return; 
    }

    int N = 1024;
    fftw_complex* in = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * N);
    fftw_complex* out = (fftw_complex*) fftw_malloc(sizeof(fftw_complex) * N);
    fftw_plan plan = fftw_plan_dft_1d(N, in, out, FFTW_FORWARD, FFTW_ESTIMATE);

    void* context = zmq_ctx_new();
    void* publisher = zmq_socket(context, ZMQ_PUB);
    zmq_bind(publisher, "tcp://*:5555");

    std::cout << "[Consumer] Running..." << std::endl;

    while (running) {
        IQBlock block;
        if(!q.pop(block)) continue; 

        for(int i=0; i<N; i++) {
            in[i][0] = block[i].real();
            in[i][1] = block[i].imag();
        }
        fftw_execute(plan);

        radio::SignalResult result;
        result.set_timestamp(time(NULL));
        result.set_center_frequency(98500000.0);
        
        result.mutable_spectrum_data()->Reserve(N);

        double max_mag = 0;
        int peak_bin = 0;

        for(int i=0; i<N; i++) {
             float mag = sqrt(out[i][0]*out[i][0] + out[i][1]*out[i][1]);
             
             result.add_spectrum_data(mag);

             if(mag > max_mag) { max_mag = mag; peak_bin = i; }
        }
        
        result.set_peak_bin_index(peak_bin);
        result.set_signal_strength(max_mag);

        std::vector<float> i_data(N);
        std::vector<float> q_data(N);
        for(int k=0; k<N; ++k) {
            i_data[k] = block[k].real();
            q_data[k] = block[k].imag();
        }
        auto options = torch::TensorOptions().dtype(torch::kFloat32);
        torch::Tensor i_t = torch::from_blob(i_data.data(), {1, 1, N}, options);
        torch::Tensor q_t = torch::from_blob(q_data.data(), {1, 1, N}, options);
        torch::Tensor input = torch::cat({i_t, q_t}, 1);

        at::Tensor output = model.forward({input}).toTensor();
        int class_id = output.argmax(1).item<int>();
        
        std::string class_name = "Unknown";
        if (class_id == 0) class_name = "Noise";
        if (class_id == 1) class_name = "FM_Signal";
        if (class_id == 2) class_name = "Key_Fob";
        
        result.set_modulation(class_name); 

        std::string payload;
        result.SerializeToString(&payload);
        zmq_send(publisher, payload.data(), payload.size(), 0);
    }

    // Cleanup
    fftw_destroy_plan(plan);
    fftw_free(in); fftw_free(out);
    zmq_close(publisher);
    zmq_ctx_destroy(context);
}

int main() {
    std::cout << "[Main] Starting SDR..." << std::endl;

    std::thread t1(sdr_driver);
    std::thread t2(dsp_consumer);

    std::cin.get();

    std::cout << "[Main] Shutting down..." << std::endl;
    running = false;

    if (t1.joinable()) t1.join();
    if (t2.joinable()) t2.join();

    std::cout << "[Main] Done." << std::endl;
    return 0;
}