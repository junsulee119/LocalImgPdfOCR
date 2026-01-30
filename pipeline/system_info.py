"""
System information and diagnostics utilities
"""
import sys
import platform
from pathlib import Path

def get_system_info():
    """Get detailed system information"""
    info = {
        'python_version': sys.version.split()[0],
        'python_full': sys.version,
        'platform': platform.system(),
        'platform_release': platform.release(),
        'platform_version': platform.version(),
        'architecture': platform.machine(),
        'processor': platform.processor(),
    }
    
    # Get more detailed Windows version
    if platform.system() == 'Windows':
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
            
            # Try to get DisplayVersion (e.g., "23H2") or ReleaseId
            try:
                display_version = winreg.QueryValueEx(key, "DisplayVersion")[0]
            except:
                try:
                    display_version = winreg.QueryValueEx(key, "ReleaseId")[0]
                except:
                    display_version = None
            
            build = winreg.QueryValueEx(key, "CurrentBuild")[0]
            
            # Detect Windows 11 vs 10 by build number
            # Windows 11 starts at build 22000
            if int(build) >= 22000:
                os_name = "Windows 11"
            else:
                os_name = "Windows 10"
            
            # Try to get edition (Pro, Home, etc.)
            try:
                edition = winreg.QueryValueEx(key, "EditionID")[0]
                if edition:
                    os_name = f"{os_name} {edition}"
            except:
                pass
            
            winreg.CloseKey(key)
            
            if display_version:
                info['platform_release'] = f"{os_name} {display_version} (Build {build})"
            else:
                info['platform_release'] = f"{os_name} (Build {build})"
        except Exception as ex:
            # Fallback to default
            pass
    
    # PyTorch info
    try:
        import torch
        info['pytorch_version'] = torch.__version__
        info['cuda_available'] = torch.cuda.is_available()
        if torch.cuda.is_available():
            info['cuda_version'] = torch.version.cuda
            info['cudnn_version'] = torch.backends.cudnn.version()
            info['gpu_count'] = torch.cuda.device_count()
            info['gpu_name'] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info['gpu_memory_gb'] = props.total_memory / 1024**3
            info['compute_capability'] = f"{props.major}.{props.minor}"
    except ImportError:
        info['pytorch_version'] = 'Not installed'
        info['cuda_available'] = False
    
    # Check for MPS (Apple Silicon)
    try:
        import torch
        if hasattr(torch.backends, 'mps'):
            info['mps_available'] = torch.backends.mps.is_available()
        else:
            info['mps_available'] = False
    except:
        info['mps_available'] = False
    
    return info

def print_system_info(logger):
    """Print detailed system information using logger"""
    from logger import Color
    
    logger.header("SYSTEM INFORMATION")
    logger.indent()
    
    info = get_system_info()
    
    # Python info
    logger.colored("Python Environment", Color.BRIGHT_CYAN, bold=True)
    logger.indent()
    logger.info(f"Version: {info['python_version']}")
    logger.info(f"Platform: {info['platform']} {info['platform_release']}")
    logger.info(f"Architecture: {info['architecture']}")
    logger.dedent()
    
    print()
    
    # PyTorch info
    logger.colored("PyTorch & Compute", Color.BRIGHT_CYAN, bold=True)
    logger.indent()
    logger.info(f"PyTorch: {info['pytorch_version']}")
    
    if info['cuda_available']:
        logger.success(f"CUDA: {info['cuda_version']}")
        logger.success(f"GPU: {info['gpu_name']}")
        logger.info(f"VRAM: {info['gpu_memory_gb']:.2f} GB")
        logger.info(f"Compute Capability: {info['compute_capability']}")
        logger.info(f"cuDNN: {info.get('cudnn_version', 'N/A')}")
    elif info.get('mps_available'):
        logger.success("Apple Silicon (MPS) Available")
    else:
        logger.warning("No GPU detected - using CPU")
    
    logger.dedent()
    logger.dedent()
    print()
