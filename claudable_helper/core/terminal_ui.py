"""Mock terminal UI implementation for claudable_helper.

This module provides a mock implementation of the terminal UI interface
that was originally imported from app.core.terminal_ui.
"""
import sys
from typing import Any, Optional


class MockTerminalUI:
    """Mock terminal UI for logging and user interaction."""
    
    def debug(self, message: str, category: str = "DEBUG") -> None:
        """Log debug message."""
        if self._should_show_debug():
            print(f"[{category}] {message}", file=sys.stderr)
    
    def info(self, message: str, category: str = "INFO") -> None:
        """Log info message."""
        print(f"[{category}] {message}")
    
    def warning(self, message: str, category: str = "WARNING") -> None:
        """Log warning message."""
        print(f"[{category}] {message}", file=sys.stderr)
    
    def error(self, message: str, category: str = "ERROR") -> None:
        """Log error message."""
        print(f"[{category}] {message}", file=sys.stderr)
    
    def success(self, message: str, category: str = "SUCCESS") -> None:
        """Log success message."""
        print(f"[{category}] {message}")
    
    def print(self, message: str = "", **kwargs) -> None:
        """Print message to stdout."""
        print(message, **kwargs)
    
    def input(self, prompt: str = "") -> str:
        """Get user input."""
        return input(prompt)
    
    def confirm(self, message: str, default: bool = True) -> bool:
        """Get user confirmation."""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{message} [{default_text}]: ").lower().strip()
        
        if not response:
            return default
        return response.startswith('y')
    
    def select(self, message: str, choices: list, default: Optional[int] = None) -> int:
        """Select from a list of choices."""
        print(message)
        for i, choice in enumerate(choices):
            marker = " (default)" if default == i else ""
            print(f"{i + 1}. {choice}{marker}")
        
        while True:
            try:
                response = input("Select option: ").strip()
                if not response and default is not None:
                    return default
                
                choice_idx = int(response) - 1
                if 0 <= choice_idx < len(choices):
                    return choice_idx
                else:
                    print(f"Please enter a number between 1 and {len(choices)}")
            except ValueError:
                print("Please enter a valid number")
    
    def _should_show_debug(self) -> bool:
        """Check if debug messages should be shown."""
        import os
        return os.environ.get("DEBUG", "").lower() in ("1", "true", "yes")


# Create singleton instance
ui = MockTerminalUI()