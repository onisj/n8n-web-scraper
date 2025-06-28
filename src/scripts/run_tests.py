#!/usr/bin/env python3
"""
Test runner script for n8n AI Knowledge System

This script provides convenient commands to run different types of tests.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and handle errors"""
    if description:
        print(f"\n🔄 {description}")
    
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"Warnings: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"❌ Command not found: {cmd[0]}")
        print("Make sure pytest is installed: pip install pytest")
        return False


def check_dependencies():
    """Check if required testing dependencies are installed"""
    print("🔍 Checking test dependencies...")
    
    required_packages = [
        'pytest',
        'pytest-cov',
        'pytest-mock',
        'pytest-asyncio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package} is installed")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} is missing")
    
    if missing_packages:
        print(f"\n📦 Install missing packages with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    return True


def run_all_tests():
    """Run all tests"""
    cmd = ['python', '-m', 'pytest', 'tests/', '-v']
    return run_command(cmd, "Running all tests")


def run_unit_tests():
    """Run only unit tests"""
    cmd = ['python', '-m', 'pytest', 'tests/', '-v', '-m', 'not slow and not integration']
    return run_command(cmd, "Running unit tests")


def run_integration_tests():
    """Run integration tests"""
    cmd = ['python', '-m', 'pytest', 'tests/', '-v', '-m', 'integration']
    return run_command(cmd, "Running integration tests")


def run_api_tests():
    """Run API tests"""
    cmd = ['python', '-m', 'pytest', 'tests/test_api.py', '-v']
    return run_command(cmd, "Running API tests")


def run_agent_tests():
    """Run agent tests"""
    cmd = ['python', '-m', 'pytest', 'tests/test_agents.py', '-v']
    return run_command(cmd, "Running agent tests")


def run_database_tests():
    """Run database tests"""
    cmd = ['python', '-m', 'pytest', 'tests/test_database.py', '-v']
    return run_command(cmd, "Running database tests")


def run_coverage_tests():
    """Run tests with coverage report"""
    cmd = [
        'python', '-m', 'pytest', 'tests/', 
        '--cov=src/n8n_scraper', 
        '--cov-report=term-missing',
        '--cov-report=html:htmlcov',
        '--cov-fail-under=70',
        '-v'
    ]
    return run_command(cmd, "Running tests with coverage")


def run_fast_tests():
    """Run fast tests only (exclude slow tests)"""
    cmd = ['python', '-m', 'pytest', 'tests/', '-v', '-m', 'not slow']
    return run_command(cmd, "Running fast tests")


def run_specific_test(test_path):
    """Run a specific test file or test function"""
    cmd = ['python', '-m', 'pytest', test_path, '-v']
    return run_command(cmd, f"Running specific test: {test_path}")


def run_parallel_tests():
    """Run tests in parallel (requires pytest-xdist)"""
    cmd = ['python', '-m', 'pytest', 'tests/', '-v', '-n', 'auto']
    return run_command(cmd, "Running tests in parallel")


def lint_code():
    """Run code linting"""
    print("\n🔍 Running code linting...")
    
    # Try different linters
    linters = [
        (['python', '-m', 'flake8', '.'], "flake8"),
        (['python', '-m', 'pylint', 'src/n8n_scraper/'], "pylint"),
        (['python', '-m', 'black', '--check', '.'], "black")
    ]
    
    for cmd, name in linters:
        print(f"\n📋 Running {name}...")
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ {name} passed")
        except subprocess.CalledProcessError:
            print(f"⚠️ {name} found issues")
        except FileNotFoundError:
            print(f"⚠️ {name} not installed")


def setup_test_environment():
    """Set up test environment"""
    print("🔧 Setting up test environment...")
    
    # Create test directories
    test_dirs = [
        'tests/test_data',
        'tests/fixtures',
        'htmlcov'
    ]
    
    for dir_path in test_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {dir_path}")
    
    # Set environment variables
    test_env = {
        'TESTING': 'true',
        'LOG_LEVEL': 'WARNING',
        'PYTHONPATH': '.'
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
        print(f"✅ Set {key}={value}")
    
    print("✅ Test environment ready")


def clean_test_artifacts():
    """Clean test artifacts"""
    print("🧹 Cleaning test artifacts...")
    
    artifacts = [
        '.pytest_cache',
        'htmlcov',
        '.coverage',
        '__pycache__',
        '*.pyc'
    ]
    
    for artifact in artifacts:
        if Path(artifact).exists():
            if Path(artifact).is_dir():
                import shutil
                shutil.rmtree(artifact)
            else:
                Path(artifact).unlink()
            print(f"✅ Removed {artifact}")
    
    # Remove __pycache__ directories recursively
    for pycache in Path('.').rglob('__pycache__'):
        import shutil
        shutil.rmtree(pycache)
        print(f"✅ Removed {pycache}")
    
    print("✅ Cleanup complete")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="Test runner for n8n AI Knowledge System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py --all                 # Run all tests
  python run_tests.py --unit                # Run unit tests only
  python run_tests.py --api                 # Run API tests
  python run_tests.py --coverage            # Run with coverage
  python run_tests.py --fast                # Run fast tests only
  python run_tests.py --specific tests/test_api.py::TestHealthEndpoints::test_health_check
  python run_tests.py --setup               # Setup test environment
  python run_tests.py --clean               # Clean test artifacts
        """
    )
    
    # Test type options
    parser.add_argument('--all', action='store_true', help='Run all tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    parser.add_argument('--api', action='store_true', help='Run API tests')
    parser.add_argument('--agents', action='store_true', help='Run agent tests')
    parser.add_argument('--database', action='store_true', help='Run database tests')
    parser.add_argument('--fast', action='store_true', help='Run fast tests only')
    parser.add_argument('--coverage', action='store_true', help='Run tests with coverage')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    
    # Specific test options
    parser.add_argument('--specific', type=str, help='Run specific test file or function')
    
    # Utility options
    parser.add_argument('--check-deps', action='store_true', help='Check test dependencies')
    parser.add_argument('--setup', action='store_true', help='Setup test environment')
    parser.add_argument('--clean', action='store_true', help='Clean test artifacts')
    parser.add_argument('--lint', action='store_true', help='Run code linting')
    
    args = parser.parse_args()
    
    # If no arguments provided, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return
    
    success = True
    
    # Handle utility commands first
    if args.check_deps:
        success = check_dependencies()
    elif args.setup:
        setup_test_environment()
    elif args.clean:
        clean_test_artifacts()
    elif args.lint:
        lint_code()
    # Handle test commands
    elif args.all:
        success = run_all_tests()
    elif args.unit:
        success = run_unit_tests()
    elif args.integration:
        success = run_integration_tests()
    elif args.api:
        success = run_api_tests()
    elif args.agents:
        success = run_agent_tests()
    elif args.database:
        success = run_database_tests()
    elif args.fast:
        success = run_fast_tests()
    elif args.coverage:
        success = run_coverage_tests()
    elif args.parallel:
        success = run_parallel_tests()
    elif args.specific:
        success = run_specific_test(args.specific)
    else:
        print("No valid option selected. Use --help for available options.")
        success = False
    
    if success:
        print("\n✅ Command completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Command failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()