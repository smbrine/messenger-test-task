#!/usr/bin/env python
"""
Script to check repository interfaces and implementations for consistency.
"""
import inspect
import importlib
import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

def check_repository_implementation(interface_module, implementation_module, interface_class, implementation_class):
    """
    Check if an implementation class properly implements all methods of its interface.
    
    Args:
        interface_module: Name of the interface module
        implementation_module: Name of the implementation module
        interface_class: Name of the interface class
        implementation_class: Name of the implementation class
        
    Returns:
        A list of missing methods
    """
    # Import the modules
    interface = importlib.import_module(interface_module)
    implementation = importlib.import_module(implementation_module)
    
    # Get the classes
    interface_cls = getattr(interface, interface_class)
    implementation_cls = getattr(implementation, implementation_class)
    
    # Get all abstract methods from the interface
    abstract_methods = []
    for name, method in inspect.getmembers(interface_cls, predicate=inspect.isfunction):
        if getattr(method, '__isabstractmethod__', False):
            abstract_methods.append(name)
    
    # Get all methods from the implementation
    implementation_methods = [name for name, method in inspect.getmembers(implementation_cls, predicate=inspect.isfunction)]
    
    # Find missing methods
    missing_methods = []
    for method in abstract_methods:
        if method not in implementation_methods:
            missing_methods.append(method)
    
    return missing_methods

def main():
    """Check all repository implementations."""
    # List of repository interfaces and implementations to check
    repositories = [
        {
            'interface_module': 'src.application.repositories.user_repository',
            'implementation_module': 'src.infrastructure.repositories.user_repository',
            'interface_class': 'UserRepository',
            'implementation_class': 'SQLAlchemyUserRepository',
        },
        {
            'interface_module': 'src.application.repositories.chat_repository',
            'implementation_module': 'src.infrastructure.repositories.chat_repository',
            'interface_class': 'ChatRepository',
            'implementation_class': 'SQLAlchemyChatRepository',
        },
        # Add other repositories here as they are implemented
    ]
    
    # Check each repository
    found_issues = False
    for repo in repositories:
        missing_methods = check_repository_implementation(
            repo['interface_module'],
            repo['implementation_module'],
            repo['interface_class'],
            repo['implementation_class'],
        )
        
        if missing_methods:
            found_issues = True
            print(f"Repository {repo['implementation_class']} is missing implementations for:")
            for method in missing_methods:
                print(f"  - {method}")
        else:
            print(f"Repository {repo['implementation_class']} implements all required methods.")
    
    # Exit with error code if issues were found
    if found_issues:
        sys.exit(1)
    else:
        print("\nAll repositories implement their interfaces correctly.")
        sys.exit(0)

if __name__ == '__main__':
    main() 