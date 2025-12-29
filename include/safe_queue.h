#ifndef SAFE_QUEUE_H
#define SAFE_QUEUE_H

#include <queue>
#include <mutex>
#include <condition_variable>
#include <vector>
#include <complex>

template <typename T>
class SafeQueue {
private:
    std::queue<T> queue_;
    std::mutex mutex_;
    std::condition_variable cond_;

public:
    void push(T value) {
        std::lock_guard<std::mutex> lock(mutex_); // Lock the mutex
        queue_.push(value);
        cond_.notify_one(); // Wakes consumer if waiting
    }

    // Pop data from the queue (Consumer calls this)
    // Returns true if data was retrieved, false if queue is empty
    bool pop(T& value) {
        std::unique_lock<std::mutex> lock(mutex_);
        
        // Wait until queue is not empty (prevents CPU burning loop)
        cond_.wait(lock, [this]{ return !queue_.empty(); });

        value = queue_.front();
        queue_.pop();
        return true;
    }

    bool empty() {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.empty();
    }
    
    size_t size() {
        std::lock_guard<std::mutex> lock(mutex_);
        return queue_.size();
    }
};

#endif