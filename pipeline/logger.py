"""
Colored logging and formatting utilities for CLI output
Provides ANSI color codes and hierarchical formatting
"""
import sys
from enum import Enum

class Color(Enum):
    """ANSI color codes"""
    # Basic colors
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # Bright colors
    BRIGHT_BLACK = '\033[90m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # Styles
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'

class LogLevel(Enum):
    """Log level definitions with colors"""
    DEBUG = ('DEBUG', Color.BRIGHT_BLACK)
    INFO = ('INFO', Color.CYAN)
    SUCCESS = ('✓', Color.BRIGHT_GREEN)
    WARNING = ('⚠', Color.BRIGHT_YELLOW)
    ERROR = ('✗', Color.BRIGHT_RED)
    CRITICAL = ('!!!', Color.RED)

# Enable ANSI colors on Windows
def enable_ansi_colors():
    """Enable ANSI escape codes on Windows"""
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Enable ANSI processing
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except:
            pass

enable_ansi_colors()

class Logger:
    """Hierarchical colored logger with indentation"""
    
    def __init__(self, indent_size=2):
        self.indent_level = 0
        self.indent_size = indent_size
        self.verbose = False
    
    def _format(self, message, level=None, indent_override=None):
        """Format message with color and indentation"""
        indent = indent_override if indent_override is not None else self.indent_level
        prefix = ' ' * (indent * self.indent_size)
        
        if level:
            label, color = level.value
            colored_label = f"{color.value}{label}{Color.RESET.value}"
            return f"{prefix}{colored_label} {message}"
        else:
            return f"{prefix}{message}"
    
    def debug(self, message, indent=None):
        """Debug message (only shown in verbose mode)"""
        if self.verbose:
            print(self._format(message, LogLevel.DEBUG, indent))
    
    def info(self, message, indent=None):
        """Info message"""
        print(self._format(message, LogLevel.INFO, indent))
    
    def success(self, message, indent=None):
        """Success message"""
        print(self._format(message, LogLevel.SUCCESS, indent))
    
    def warning(self, message, indent=None):
        """Warning message"""
        print(self._format(message, LogLevel.WARNING, indent))
    
    def error(self, message, indent=None):
        """Error message"""
        print(self._format(message, LogLevel.ERROR, indent))
    
    def critical(self, message, indent=None):
        """Critical error message"""
        print(self._format(message, LogLevel.CRITICAL, indent))
    
    def plain(self, message, indent=None):
        """Plain message without level"""
        print(self._format(message, None, indent))
    
    def colored(self, message, color, indent=None, bold=False):
        """Custom colored message"""
        style = Color.BOLD.value if bold else ''
        colored_msg = f"{style}{color.value}{message}{Color.RESET.value}"
        prefix = ' ' * ((indent if indent is not None else self.indent_level) * self.indent_size)
        print(f"{prefix}{colored_msg}")
    
    def header(self, message):
        """Print a header"""
        separator = '=' * 60
        print(f"\n{Color.BOLD.value}{Color.CYAN.value}{separator}{Color.RESET.value}")
        print(f"{Color.BOLD.value}{Color.CYAN.value}{message}{Color.RESET.value}")
        print(f"{Color.BOLD.value}{Color.CYAN.value}{separator}{Color.RESET.value}\n")
    
    def section(self, message):
        """Print a section header"""
        print(f"\n{Color.BOLD.value}{Color.BLUE.value}▶ {message}{Color.RESET.value}")
    
    def indent(self):
        """Increase indentation level"""
        self.indent_level += 1
    
    def dedent(self):
        """Decrease indentation level"""
        self.indent_level = max(0, self.indent_level - 1)
    
    def reset_indent(self):
        """Reset indentation to 0"""
        self.indent_level = 0

class ProgressBar:
    """Simple progress bar for terminal"""
    
    def __init__(self, total, prefix='Progress', length=40):
        self.total = total
        self.current = 0
        self.prefix = prefix
        self.length = length
    
    def update(self, value=None, suffix=''):
        """Update progress bar"""
        if value is not None:
            self.current = value
        else:
            self.current += 1
        
        percent = min(100, int(100 * self.current / self.total))
        filled = int(self.length * self.current / self.total)
        bar = '█' * filled + '░' * (self.length - filled)
        
        # Color based on progress
        if percent == 100:
            color = Color.BRIGHT_GREEN.value
        elif percent >= 50:
            color = Color.CYAN.value
        else:
            color = Color.YELLOW.value
        
        print(f'\r{self.prefix}: {color}|{bar}| {percent}%{Color.RESET.value} {suffix}', end='', flush=True)
        
        if self.current >= self.total:
            print()  # New line when complete

# Global logger instance
logger = Logger()

def format_size(bytes_size):
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} TB"

def format_duration(seconds):
    """Format seconds to human readable duration"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"
