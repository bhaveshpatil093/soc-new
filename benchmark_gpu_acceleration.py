"""
Benchmark script to evaluate GPU (MPS/CUDA) vs CPU for TADS PyTorch models.
Evaluates training and inference for Autoencoder and SequenceLSTM,
and simple numeric transforms, including data transfer overhead.
"""

import time
import torch
import torch.nn as nn
import numpy as np
from tabulate import tabulate
import os

# Import network definitions (they are private, so we import directly)
from tads.models.detectors.autoencoder import _AutoencoderNetwork
from tads.models.detectors.sequence_lstm import _CausalLSTMPredictor


def get_device() -> torch.device:
    if torch.cuda.is_available():
        return torch.device("cuda")
    elif torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")

def benchmark_numeric_transform(device: torch.device, n_rows: int = 1_000_000, n_cols: int = 10):
    print(f"\n--- Numeric Transform (Z-Score Standardization) ---")
    data_np = np.random.randn(n_rows, n_cols).astype(np.float32)
    
    # NumPy (CPU)
    t0 = time.time()
    mean = np.mean(data_np, axis=0)
    std = np.std(data_np, axis=0)
    _ = (data_np - mean) / (std + 1e-8)
    t_numpy = time.time() - t0
    
    # PyTorch (Target Device)
    t0 = time.time()
    # include data transfer overhead
    tensor = torch.from_numpy(data_np).to(device)
    mean_t = torch.mean(tensor, dim=0)
    std_t = torch.std(tensor, dim=0)
    _ = (tensor - mean_t) / (std_t + 1e-8)
    # Move back to CPU/NumPy to complete the cycle
    _ = _.cpu().numpy()
    t_torch = time.time() - t0
    
    return ["Numeric Transform", f"{t_numpy:.4f}s", f"{t_torch:.4f}s", f"{t_numpy/t_torch:.1f}x"]


def benchmark_autoencoder(device: torch.device, train_rows: int = 50_000, inf_rows: int = 500_000):
    print(f"\n--- Autoencoder ---")
    input_dim = 10
    batch_size = 256
    
    # CPU Model
    model_cpu = _AutoencoderNetwork(input_dim, 32, 8).to("cpu")
    opt_cpu = torch.optim.Adam(model_cpu.parameters(), lr=1e-3)
    criterion = nn.MSELoss()
    
    # Target Device Model
    model_gpu = _AutoencoderNetwork(input_dim, 32, 8).to(device)
    opt_gpu = torch.optim.Adam(model_gpu.parameters(), lr=1e-3)
    
    # Dummy Data
    train_np = np.random.randn(train_rows, input_dim).astype(np.float32)
    inf_np = np.random.randn(inf_rows, input_dim).astype(np.float32)
    
    # Train CPU
    train_t_cpu = torch.from_numpy(train_np)
    train_dataset_cpu = torch.utils.data.TensorDataset(train_t_cpu)
    loader_cpu = torch.utils.data.DataLoader(train_dataset_cpu, batch_size=batch_size)
    
    t0 = time.time()
    model_cpu.train()
    for _ in range(3): # 3 epochs
        for (b,) in loader_cpu:
            opt_cpu.zero_grad()
            loss = criterion(model_cpu(b), b)
            loss.backward()
            opt_cpu.step()
    t_train_cpu = time.time() - t0
    
    # Train GPU (including data transfer in the loop)
    t0 = time.time()
    model_gpu.train()
    for _ in range(3):
        for (b,) in loader_cpu: # Loader is on CPU, must transfer inside loop
            b_gpu = b.to(device)
            opt_gpu.zero_grad()
            loss = criterion(model_gpu(b_gpu), b_gpu)
            loss.backward()
            opt_gpu.step()
    t_train_gpu = time.time() - t0
    
    # Inference CPU
    inf_t_cpu = torch.from_numpy(inf_np)
    inf_loader_cpu = torch.utils.data.DataLoader(torch.utils.data.TensorDataset(inf_t_cpu), batch_size=2048)
    
    t0 = time.time()
    model_cpu.eval()
    with torch.no_grad():
        for (b,) in inf_loader_cpu:
            _ = model_cpu(b)
    t_inf_cpu = time.time() - t0
    
    # Inference GPU
    t0 = time.time()
    model_gpu.eval()
    with torch.no_grad():
        for (b,) in inf_loader_cpu:
            b_gpu = b.to(device)
            out = model_gpu(b_gpu)
            _ = out.cpu().numpy() # Must bring back to CPU for anomaly scores
    t_inf_gpu = time.time() - t0
    
    return [
        ["AE Training (3 epochs)", f"{t_train_cpu:.3f}s", f"{t_train_gpu:.3f}s", f"{t_train_cpu/t_train_gpu:.1f}x"],
        ["AE Inference (500k)", f"{t_inf_cpu:.3f}s", f"{t_inf_gpu:.3f}s", f"{t_inf_cpu/t_inf_gpu:.1f}x"]
    ]


def benchmark_sequence(device: torch.device, train_rows: int = 10_000, inf_rows: int = 100_000):
    print(f"\n--- Sequence LSTM ---")
    input_dim = 10
    seq_len = 10
    batch_size = 128
    
    model_cpu = _CausalLSTMPredictor(input_dim, 32, 1).to("cpu")
    opt_cpu = torch.optim.Adam(model_cpu.parameters(), lr=1e-3)
    criterion = nn.MSELoss()
    
    model_gpu = _CausalLSTMPredictor(input_dim, 32, 1).to(device)
    opt_gpu = torch.optim.Adam(model_gpu.parameters(), lr=1e-3)
    
    # Shape: (batch, seq_len, features)
    train_np = np.random.randn(train_rows, seq_len, input_dim).astype(np.float32)
    inf_np = np.random.randn(inf_rows, seq_len, input_dim).astype(np.float32)
    
    loader_cpu = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(torch.from_numpy(train_np)), batch_size=batch_size
    )
    inf_loader_cpu = torch.utils.data.DataLoader(
        torch.utils.data.TensorDataset(torch.from_numpy(inf_np)), batch_size=1024
    )
    
    # Train CPU
    t0 = time.time()
    model_cpu.train()
    for _ in range(3):
        for (b,) in loader_cpu:
            opt_cpu.zero_grad()
            out = model_cpu(b)
            loss = criterion(out, b)
            loss.backward()
            opt_cpu.step()
    t_train_cpu = time.time() - t0
    
    # Train GPU
    t0 = time.time()
    model_gpu.train()
    for _ in range(3):
        for (b,) in loader_cpu:
            b_gpu = b.to(device)
            opt_gpu.zero_grad()
            out = model_gpu(b_gpu)
            loss = criterion(out, b_gpu)
            loss.backward()
            opt_gpu.step()
    t_train_gpu = time.time() - t0
    
    # Inference CPU
    t0 = time.time()
    model_cpu.eval()
    with torch.no_grad():
        for (b,) in inf_loader_cpu:
            _ = model_cpu(b)
    t_inf_cpu = time.time() - t0
    
    # Inference GPU
    t0 = time.time()
    model_gpu.eval()
    with torch.no_grad():
        for (b,) in inf_loader_cpu:
            b_gpu = b.to(device)
            out = model_gpu(b_gpu)
            _ = out.cpu().numpy()
    t_inf_gpu = time.time() - t0
    
    return [
        ["LSTM Training (3 epochs)", f"{t_train_cpu:.3f}s", f"{t_train_gpu:.3f}s", f"{t_train_cpu/t_train_gpu:.1f}x"],
        ["LSTM Inference (100k)", f"{t_inf_cpu:.3f}s", f"{t_inf_gpu:.3f}s", f"{t_inf_cpu/t_inf_gpu:.1f}x"]
    ]


def main():
    target_device = get_device()
    print(f"Target Device: {target_device}")
    
    if target_device.type == "cpu":
        print("No GPU detected! Cannot run benchmark.")
        return

    results = []
    
    res = benchmark_numeric_transform(target_device)
    results.append(res)
    
    res = benchmark_autoencoder(target_device)
    results.extend(res)
    
    res = benchmark_sequence(target_device)
    results.extend(res)
    
    print("\n" + "="*80)
    print("=== GPU ACCELERATION BENCHMARK REPORT ===")
    print("="*80)
    print(tabulate(results, headers=["Stage", "CPU Time", f"GPU ({target_device}) Time", "Speedup"], tablefmt="grid"))


if __name__ == "__main__":
    # Prevent PyTorch from using too many threads and skewing CPU benchmark
    torch.set_num_threads(4) 
    main()
