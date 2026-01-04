import torch
import torch.nn as nn
import torch.optim as optim
import torch.utils.data as data
import numpy as np

# Configuration
BATCH_SIZE = 32
EPOCHS = 10
LEARNING_RATE = 0.001
MODEL_PATH = "radio_model.pt"

# 1D Convolutional Neural Network optimized for I/Q Radio Signals
class RadioClassifier(nn.Module):
    def __init__(self):
        super(RadioClassifier, self).__init__()
        
        self.features = nn.Sequential(
            nn.Conv1d(in_channels=2, out_channels=16, kernel_size=11, stride=1, padding=5),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2),
            nn.Conv1d(in_channels=16, out_channels=32, kernel_size=5, stride=1, padding=2),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2),
            nn.Conv1d(in_channels=32, out_channels=64, kernel_size=3, stride=1, padding=1),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 128, 128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, 3)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x

try:
    x_numpy = np.load("dataset_x.npy")
    y_numpy = np.load("dataset_y.npy")
    print(f"Loaded {len(x_numpy)} samples.")
except FileNotFoundError:
    print("CRITICAL ERROR: 'dataset_x.npy' not found!")
    print("Please run 'python3 process_data.py' first.")
    exit()

x_tensor = torch.from_numpy(x_numpy).float()
y_tensor = torch.from_numpy(y_numpy).long()

dataset = data.TensorDataset(x_tensor, y_tensor)
train_size = int(0.8 * len(dataset))
test_size = len(dataset) - train_size
train_set, test_set = data.random_split(dataset, [train_size, test_size])

train_loader = data.DataLoader(train_set, batch_size=BATCH_SIZE, shuffle=True)
test_loader = data.DataLoader(test_set, batch_size=BATCH_SIZE, shuffle=False)

print(f"Training on {len(train_set)} samples, Validating on {len(test_set)}...")

model = RadioClassifier()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)

for epoch in range(EPOCHS):
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    for inputs, labels in train_loader:
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item()
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

    acc = 100 * correct / total
    print(f"Epoch {epoch+1}/{EPOCHS} | Loss: {running_loss/len(train_loader):.4f} | Acc: {acc:.2f}%")

print("\nEvaluating on Test Set...")
model.eval()
correct = 0
total = 0
with torch.no_grad():
    for inputs, labels in test_loader:
        outputs = model(inputs)
        _, predicted = torch.max(outputs.data, 1)
        total += labels.size(0)
        correct += (predicted == labels).sum().item()

print(f"Final Test Accuracy: {100 * correct / total:.2f}%")

print(f"\nExporting model to {MODEL_PATH}...")

# Create a dummy input that matches the C++ input shape [1, 2, 1024]
dummy_input = torch.randn(1, 2, 1024)
traced_script_module = torch.jit.trace(model, dummy_input)
traced_script_module.save(MODEL_PATH)

print("Model has been saved! Copy this file to your C++ build folder:")
print(f"  cp {MODEL_PATH} build/")