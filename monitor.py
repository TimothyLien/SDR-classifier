import zmq
import message_pb2
import time
import sys

def main():
    print("[Monitor] Connecting to C++ Radio on localhost:5555...")

    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://localhost:5555")
    
    subscriber.setsockopt_string(zmq.SUBSCRIBE, "")

    print("[Monitor] Waiting for data streams...")

    count = 0
    start_time = time.time()

    try:
        while True:
            raw_data = subscriber.recv()

            result = message_pb2.SignalResult()
            result.ParseFromString(raw_data)

            count += 1
            if count % 50 == 0:
                elapsed = time.time() - start_time
                rate = count / elapsed
                
                sys.stdout.write(
                    f"\r[Dashboard] Rx Rate: {rate:.1f} msg/s | "
                    f"Freq: {result.center_frequency:.1f}Hz | "
                    f"Peak Bin: {result.peak_bin_index} | "
                    f"Power: {result.signal_strength:.2f}"
                )
                sys.stdout.flush()

    except KeyboardInterrupt:
        print("\n[Monitor] Stopping...")

if __name__ == "__main__":
    main()