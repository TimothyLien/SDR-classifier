import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import math

NUM_SAMPLES = 2000
BLOCK_SIZE = 1024
EPOCHS = 100

CLASSES = ["Noise", "Sine_Wave", "BPSK_Digital"]

def generate_data(num_samples):
    X = [] # Data (Signals)
    y = [] # Labels (Answers)

    print(f"[*] Generating {num_samples} synthetic signals...")

    for _ in range(num_samples):
        t = np.linspace(0, 1, BLOCK_SIZE)
        
        # Pick a random class
        label_idx = np.random.randint(0, 3)
        
        sig_i = np.zeros(BLOCK_SIZE)
        sig_q = np.zeros(BLOCK_SIZE)

        if label_idx == 0: # NOISE
            pass # Signal remains 0, noise added later

        elif label_idx == 1: # SINE WAVE
            freq = np.random.uniform(50, 200) # Random freq
            sig_i = np.cos(2 * np.pi * freq * t)
            sig_q = np.sin(2 * np.pi * freq * t)

        elif label_idx == 2: # BPSK (Digital Data)
            # BPSK flips phase by 180 degrees to send a '1' or '0'
            freq = np.random.uniform(50, 200)
            phase = 0
            # Flip phase every 100 samples
            for i in range(BLOCK_SIZE):
                if i % 100 == 0:
                    phase += np.pi if np.random.rand() > 0.5 else 0
                sig_i[i] = np.cos(2 * np.pi * freq * t[i] + phase)
                sig_q[i] = np.sin(2 * np.pi * freq * t[i] + phase)

        # Add Random Gaussian Noise (The "Static")
        noise_power = 0.5
        sig_i += np.random.normal(0, noise_power, BLOCK_SIZE)
        sig_q += np.random.normal(0, noise_power, BLOCK_SIZE)

        # Stack into [2, 1024] format (Channel 0 = I, Channel 1 = Q)
        data = np.vstack([sig_i, sig_q])
        X.append(data)
        y.append(label_idx)

    # Convert to PyTorch Tensors
    X_tensor = torch.tensor(np.array(X), dtype=torch.float32)
    y_tensor = torch.tensor(np.array(y), dtype=torch.long)
    return X_tensor, y_tensor

# Neural Network
class RadioClassifier(nn.Module):
    def __init__(self):
        super(RadioClassifier, self).__init__()
        # Input: 2 channels (I and Q), Length 1024
        self.conv1 = nn.Conv1d(in_channels=2, out_channels=16, kernel_size=7, padding=3)
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool1d(kernel_size=2) # Shrinks size by half
        
        self.conv2 = nn.Conv1d(16, 32, 7, padding=3)
        
        # After 2 pools, 1024 -> 512 -> 256
        self.flatten = nn.Flatten()
        self.fc1 = nn.Linear(32 * 256, 3) # Output: 3 Classes

    def forward(self, x):
        x = self.pool(self.relu(self.conv1(x)))
        x = self.pool(self.relu(self.conv2(x)))
        x = self.flatten(x)
        x = self.fc1(x)
        return x

# Training
def main():
    X_train, y_train = generate_data(NUM_SAMPLES)

    model = RadioClassifier()
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    model.train()
    for epoch in range(EPOCHS):
        optimizer.zero_grad()
        outputs = model(X_train)
        loss = criterion(outputs, y_train)
        loss.backward()
        optimizer.step()
        
        # Calculate Accuracy
        _, predicted = torch.max(outputs.data, 1)
        acc = (predicted == y_train).sum().item() / NUM_SAMPLES
        print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {loss.item():.4f} | Accuracy: {acc*100:.1f}%")

    print("Training Complete.")

    model.eval()
    
    example_input = torch.rand(1, 2, BLOCK_SIZE) 
    
    traced_script_module = torch.jit.trace(model, example_input)
    
    traced_script_module.save("radio_model.pt")
    print("[SUCCESS] Model saved as 'radio_model.pt'")

if __name__ == "__main__":
    main()