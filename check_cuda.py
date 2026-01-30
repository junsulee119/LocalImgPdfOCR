"""
CUDA Diagnostic Script
Run this to check your PyTorch and CUDA installation
"""
import sys

print("="*60)
print("CUDA Diagnostic Tool")
print("="*60)
print()

# Check Python version
print(f"Python Version: {sys.version}")
print()

# Check PyTorch installation
try:
    import torch
    print(f"✓ PyTorch Installed: {torch.__version__}")
    print()
except ImportError:
    print("✗ PyTorch is NOT installed")
    print("  Install with: pip install torch --index-url https://download.pytorch.org/whl/cu118")
    sys.exit(1)

# Check CUDA availability
print("CUDA Information:")
print(f"  CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"  CUDA Version: {torch.version.cuda}")
    print(f"  GPU Count: {torch.cuda.device_count()}")
    
    for i in range(torch.cuda.device_count()):
        print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        print(f"    Memory: {torch.cuda.get_device_properties(i).total_memory / 1024**3:.2f} GB")
else:
    print()
    print("✗ CUDA is NOT available")
    print()
    print("Possible reasons:")
    print("  1. PyTorch was installed without CUDA support (CPU-only version)")
    print("  2. NVIDIA GPU drivers not installed")
    print("  3. CUDA toolkit not installed")
    print()
    print("To fix:")
    print("  1. Check if you have an NVIDIA GPU:")
    print("     - Open Device Manager (Windows)")
    print("     - Look for NVIDIA GPU under 'Display adapters'")
    print()
    print("  2. Install NVIDIA GPU drivers:")
    print("     - Visit: https://www.nvidia.com/Download/index.aspx")
    print()
    print("  3. Reinstall PyTorch with CUDA support:")
    print("     - Uninstall current PyTorch:")
    print("       pip uninstall torch torchvision")
    print()
    print("     - Install PyTorch with CUDA 11.8:")
    print("       pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118")
    print()
    print("     - OR CUDA 12.1:")
    print("       pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121")

print()
print("="*60)

# Test tensor operations
if torch.cuda.is_available():
    print()
    print("Testing CUDA tensor operations...")
    try:
        x = torch.rand(3, 3).cuda()
        y = torch.rand(3, 3).cuda()
        z = x + y
        print("✓ CUDA tensor operations working!")
        print(f"  Test tensor on: {z.device}")
    except Exception as e:
        print(f"✗ CUDA test failed: {e}")

print()
print("="*60)
