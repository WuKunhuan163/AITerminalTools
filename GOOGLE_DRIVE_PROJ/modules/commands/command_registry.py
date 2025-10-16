"""
Command registry for managing GDS special commands.
"""

from typing import Dict, List, Optional
from .base_command import BaseCommand


class CommandRegistry:
    """Registry for managing special commands."""
    
    def __init__(self):
        self._commands: Dict[str, BaseCommand] = {}
    
    def register(self, command: BaseCommand) -> None:
        """
        Register a command handler.
        
        Args:
            command: Command handler instance
        """
        self._commands[command.command_name] = command
    
    def get_command(self, name: str) -> Optional[BaseCommand]:
        """
        Get command handler by name.
        
        Args:
            name: Command name
            
        Returns:
            BaseCommand instance or None if not found
        """
        return self._commands.get(name)
    
    def is_special_command(self, name: str) -> bool:
        """
        Check if a command is a special command.
        
        Args:
            name: Command name
            
        Returns:
            bool: True if it's a special command, False otherwise
        """
        return name in self._commands
    
    def get_all_commands(self) -> List[str]:
        """
        Get list of all registered command names.
        
        Returns:
            List of command names
        """
        return list(self._commands.keys())
    
    def execute_command(self, name: str, args: List[str], **kwargs) -> int:
        """
        Execute a command by name.
        
        Args:
            name: Command name
            args: Command arguments
            **kwargs: Additional keyword arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for failure)
        """
        command = self.get_command(name)
        if command is None:
            print(f"Error: Unknown command '{name}'")
            return 1
        
        if not command.validate_args(args):
            return 1
        
        return command.execute(args, **kwargs)
