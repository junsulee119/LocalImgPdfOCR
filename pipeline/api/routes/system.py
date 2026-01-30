"""
System information endpoints
"""
from fastapi import APIRouter
import torch

router = APIRouter()

@router.get("/info")
async def get_system_info():
    """Get system capabilities"""
    cuda_supported = torch.cuda.is_available()
    cuda_devices = torch.cuda.device_count() if cuda_supported else 0
    
    return {
        "cudaSupported": cuda_supported,
        "cudaDevices": cuda_devices,
        "torchVersion": torch.__version__
    }
