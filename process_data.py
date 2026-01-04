import numpy as np
import torch
import os

# Configuration
CHUNK_SIZE = 1024
FILES = {
    "noise": "data_noise.bin",
    "fm":    "data_fm.bin",
    "keyfob": "data_keyfob.bin"
}
LABELS = {"noise": 0, "fm": 1, "keyfob": 2}

def load_and_slice(filename, label_id, energy_threshold=0.0):
    print(f"Processing {filename}...")
    
    try:
        raw = np.fromfile(filename, dtype=np.uint8)
    except FileNotFoundError:
        print(f"Error: {filename} not found! Did you record it?")
        return np.array([]), np.array([])
    
    raw = (raw.astype(np.float32) - 127.5) / 127.5

    i_samples = raw[0::2]
    q_samples = raw[1::2]
    
    min_len = min(len(i_samples), len(q_samples))
    i_samples = i_samples[:min_len]
    q_samples = q_samples[:min_len]

    num_chunks = min_len // CHUNK_SIZE
    data = []
    labels = []

    for k in range(num_chunks):
        start = k * CHUNK_SIZE
        end = start + CHUNK_SIZE
        
        chunk_i = i_samples[start:end]
        chunk_q = q_samples[start:end]
    
        energy = np.sum(chunk_i**2 + chunk_q**2)

        if label_id == 2 and energy < 5.0: 
            continue
            
        chunk_combined = np.stack([chunk_i, chunk_q], axis=0)
        data.append(chunk_combined)
        labels.append(label_id)

    print(f"  -> Extracted {len(data)} samples.")
    return np.array(data), np.array(labels)

# --- EXECUTION ---
all_data = []
all_labels = []

# Process all files
for class_name, fname in FILES.items():
    # Set threshold only for keyfob
    thresh = 0.0
    if class_name == "keyfob": thresh = 10.0 
    
    d, l = load_and_slice(fname, LABELS[class_name], thresh)
    if len(d) > 0:
        all_data.append(d)
        all_labels.append(l)

# Combine
X = np.concatenate(all_data, axis=0) # Shape: [N, 2, 1024]
y = np.concatenate(all_labels, axis=0) # Shape: [N]

# Shuffle
indices = np.arange(len(X))
np.random.shuffle(indices)
X = X[indices]
y = y[indices]

# Save
print(f"Saving dataset: {X.shape}")
np.save("dataset_x.npy", X)
np.save("dataset_y.npy", y)
print("Done! You can now run train_model.py")