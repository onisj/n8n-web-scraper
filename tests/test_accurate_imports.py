#!/usr/bin/env python3
"""
Accurate Import Test for n8n Web Scraper

This script tests all actual imports in the project to ensure they work correctly.
It's based on the real project structure and existing import statements.
"""

import sys
import importlib
import os
from pathlib import Path
from typing import List, Tuple, Dict, Set
from dataclasses import dataclass
import traceback

# Add project paths to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
scripts_path = project_root / "src" / "scripts"
tools_path = project_root / "src" / "tools"

# Add project root for config imports and src for n8n_scraper imports
for path in [project_root, src_path, scripts_path, tools_path]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

@dataclass
class ImportTest:
    """Represents a single import test"""
    module_name: str
    category: str
    is_optional: bool = False
    description: str = ""
    success: bool = False
    error_message: str = ""
    import_time: float = 0.0

class AccurateImportTester:
    """Tests all imports based on actual project structure"""
    
    def __init__(self):
        self.tests: List[ImportTest] = []
        self.setup_tests()
    
    def setup_tests(self):
        """Setup all import tests based on actual project structure"""
        
        # Core Configuration
        self.add_test("config.settings", "Core Configuration", 
                     description="Main configuration settings")
        
        # Core n8n_scraper package
        self.add_test("n8n_scraper", "Core Package",
                     description="Main package initialization")
        
        # Database modules
        self.add_test("n8n_scraper.database", "Database",
                     description="Database package")
        self.add_test("n8n_scraper.database.vector_db", "Database",
                     description="Vector database implementation")
        self.add_test("n8n_scraper.database.schemas", "Database",
                     description="Database schemas")
        self.add_test("n8n_scraper.database.schemas.document", "Database",
                     description="Document schema")
        self.add_test("n8n_scraper.database.schemas.knowledge_base", "Database",
                     description="Knowledge base schema")
        self.add_test("n8n_scraper.database.migrations.migration_manager", "Database",
                     description="Migration manager")
        
        # AI Agents
        self.add_test("n8n_scraper.agents.n8n_agent", "AI Agents",
                     description="Main n8n expert agent")
        self.add_test("n8n_scraper.agents.knowledge_processor", "AI Agents",
                     description="Knowledge processing agent")
        
        # Automation modules
        self.add_test("n8n_scraper.automation.update_scheduler", "Automation",
                     description="Automated update scheduler")
        self.add_test("n8n_scraper.automation.knowledge_updater", "Automation",
                     description="Knowledge updater (scraper)")
        self.add_test("n8n_scraper.automation.change_detector", "Automation",
                     description="Change detection and analysis")
        
        # API modules
        self.add_test("n8n_scraper.api", "API",
                     description="API package")
        self.add_test("n8n_scraper.api.main", "API",
                     description="Main FastAPI application")
        self.add_test("n8n_scraper.api.routes", "API",
                     description="API routes package")
        self.add_test("n8n_scraper.api.routes.ai_routes", "API",
                     description="AI-related API routes")
        self.add_test("n8n_scraper.api.routes.knowledge_routes", "API",
                     description="Knowledge API routes")
        self.add_test("n8n_scraper.api.routes.system_routes", "API",
                     description="System API routes")
        
        # API Middleware
        self.add_test("n8n_scraper.api.middleware", "API Middleware",
                     description="Middleware package")
        self.add_test("n8n_scraper.api.middleware.auth", "API Middleware",
                     description="Authentication middleware")
        self.add_test("n8n_scraper.api.middleware.cors", "API Middleware",
                     description="CORS middleware")
        self.add_test("n8n_scraper.api.middleware.rate_limit", "API Middleware",
                     description="Rate limiting middleware")
        
        # Web Interface
        self.add_test("n8n_scraper.web_interface", "Web Interface",
                     description="Web interface package")
        # self.add_test("n8n_scraper.web_interface.streamlit_app", "Web Interface",
        #              description="Main Streamlit application - DEPRECATED")
        self.add_test("n8n_scraper.web_interface.components", "Web Interface",
                     description="UI components package")
        self.add_test("n8n_scraper.web_interface.components.chat_interface", "Web Interface",
                     description="Chat interface component")
        self.add_test("n8n_scraper.web_interface.components.knowledge_browser", "Web Interface",
                     description="Knowledge browser component")
        self.add_test("n8n_scraper.web_interface.components.system_monitor", "Web Interface",
                     description="System monitor component")
        self.add_test("n8n_scraper.web_interface.components.settings_panel", "Web Interface",
                     description="Settings panel component")
        
        # Scripts
        self.add_test("scripts.start_system", "Scripts",
                     description="System startup script")
        self.add_test("scripts.run_scraper", "Scripts",
                     description="Scraper runner script")
        self.add_test("scripts.run_tests", "Scripts",
                     description="Test runner script")
        
        # Tools
        self.add_test("tools.system_check", "Tools",
                     description="System health check tool")
        self.add_test("tools.restructure_project", "Tools",
                     description="Project restructuring tool")
        
        # Required Dependencies
        self.add_test("fastapi", "Required Dependencies",
                     description="FastAPI web framework")
        self.add_test("uvicorn", "Required Dependencies",
                     description="ASGI server")
        # self.add_test("streamlit", "Required Dependencies",
        #              description="Streamlit web app framework - DEPRECATED")
        self.add_test("pydantic", "Required Dependencies",
                     description="Data validation library")
        self.add_test("requests", "Required Dependencies",
                     description="HTTP library")
        self.add_test("bs4", "Required Dependencies",
                     description="Beautiful Soup HTML parser")
        self.add_test("chromadb", "Required Dependencies",
                     description="Vector database")
        self.add_test("schedule", "Required Dependencies",
                     description="Job scheduling library")
        self.add_test("psutil", "Required Dependencies",
                     description="System monitoring library")
        
        # Optional Dependencies
        self.add_test("selenium", "Optional Dependencies", is_optional=True,
                     description="Web automation (optional)")
        self.add_test("openai", "Optional Dependencies", is_optional=True,
                     description="OpenAI API client (optional)")
        self.add_test("langchain", "Optional Dependencies", is_optional=True,
                     description="LangChain framework (optional)")
        self.add_test("nltk", "Optional Dependencies", is_optional=True,
                     description="Natural Language Toolkit (optional)")
        self.add_test("plotly", "Optional Dependencies", is_optional=True,
                     description="Plotting library (optional)")
        
        # Standard Library (should always work)
        self.add_test("json", "Standard Library",
                     description="JSON handling")
        self.add_test("os", "Standard Library",
                     description="Operating system interface")
        self.add_test("sys", "Standard Library",
                     description="System-specific parameters")
        self.add_test("pathlib", "Standard Library",
                     description="Path handling")
        self.add_test("datetime", "Standard Library",
                     description="Date and time handling")
        self.add_test("logging", "Standard Library",
                     description="Logging facility")
        self.add_test("threading", "Standard Library",
                     description="Threading support")
        self.add_test("subprocess", "Standard Library",
                     description="Subprocess management")
    
    def add_test(self, module_name: str, category: str, is_optional: bool = False, description: str = ""):
        """Add a test to the test suite"""
        test = ImportTest(
            module_name=module_name,
            category=category,
            is_optional=is_optional,
            description=description
        )
        self.tests.append(test)
    
    def run_single_test(self, test: ImportTest) -> ImportTest:
        """Run a single import test"""
        import time
        start_time = time.time()
        
        try:
            # Try to import the module
            module = importlib.import_module(test.module_name)
            
            # Verify the module was actually imported
            if module is None:
                test.success = False
                test.error_message = "Module imported but returned None"
            else:
                test.success = True
                test.error_message = ""
                
        except ImportError as e:
            test.success = False
            test.error_message = f"ImportError: {str(e)}"
            
        except Exception as e:
            test.success = False
            test.error_message = f"Unexpected error: {str(e)}"
            
        test.import_time = time.time() - start_time
        return test
    
    def run_all_tests(self) -> Dict[str, any]:
        """Run all import tests and return results"""
        print("🔍 Running Accurate Import Tests...\n")
        print(f"Testing {len(self.tests)} modules across multiple categories\n")
        
        # Group tests by category
        categories = {}
        for test in self.tests:
            if test.category not in categories:
                categories[test.category] = []
            categories[test.category].append(test)
        
        # Run tests by category
        for category, category_tests in categories.items():
            print(f"📦 Testing {category} ({len(category_tests)} modules)...")
            
            for test in category_tests:
                self.run_single_test(test)
                
                # Display result
                if test.success:
                    status = "✅"
                    time_info = f"({test.import_time:.3f}s)"
                elif test.is_optional:
                    status = "⚠️ "
                    time_info = "(optional)"
                else:
                    status = "❌"
                    time_info = "(failed)"
                
                print(f"  {status} {test.module_name} {time_info}")
                if test.description:
                    print(f"      {test.description}")
                
                if not test.success and not test.is_optional:
                    print(f"      Error: {test.error_message}")
            
            print()  # Empty line between categories
        
        return self.generate_report()
    
    def generate_report(self) -> Dict[str, any]:
        """Generate a comprehensive test report"""
        total_tests = len(self.tests)
        successful_tests = sum(1 for test in self.tests if test.success)
        failed_required = sum(1 for test in self.tests if not test.success and not test.is_optional)
        failed_optional = sum(1 for test in self.tests if not test.success and test.is_optional)
        
        # Calculate success rate (excluding optional dependencies)
        required_tests = sum(1 for test in self.tests if not test.is_optional)
        required_successful = sum(1 for test in self.tests if test.success and not test.is_optional)
        success_rate = (required_successful / required_tests * 100) if required_tests > 0 else 0
        
        print("="*80)
        print("📊 ACCURATE IMPORT TEST REPORT")
        print("="*80)
        
        print(f"\n📈 Summary:")
        print(f"  Total modules tested: {total_tests}")
        print(f"  Successfully imported: {successful_tests}")
        print(f"  Required modules failed: {failed_required}")
        print(f"  Optional modules failed: {failed_optional}")
        print(f"  Success rate (required): {success_rate:.1f}%")
        
        # Group results by category
        categories = {}
        for test in self.tests:
            if test.category not in categories:
                categories[test.category] = []
            categories[test.category].append(test)
        
        print(f"\n📋 Results by Category:")
        for category, tests in categories.items():
            successful = sum(1 for test in tests if test.success)
            total = len(tests)
            failed_tests = [test for test in tests if not test.success]
            
            print(f"\n  📁 {category}: {successful}/{total} successful")
            
            if failed_tests:
                required_failed = [test for test in failed_tests if not test.is_optional]
                optional_failed = [test for test in failed_tests if test.is_optional]
                
                if required_failed:
                    print(f"    ❌ Required failures:")
                    for test in required_failed:
                        print(f"      • {test.module_name}: {test.error_message}")
                
                if optional_failed:
                    print(f"    ⚠️  Optional failures:")
                    for test in optional_failed:
                        print(f"      • {test.module_name}: {test.error_message}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if failed_required == 0:
            print("  🎉 All required modules imported successfully!")
            print("  ✨ Your development environment is properly configured.")
        else:
            print(f"  🔧 Fix {failed_required} required import failures")
            print(f"  📦 Install missing dependencies: pip install -r requirements.txt")
            print(f"  🔍 Check PYTHONPATH includes project src directory")
            print(f"  📝 Verify all __init__.py files are present")
        
        if failed_optional > 0:
            print(f"  📋 {failed_optional} optional dependencies not installed (this is OK)")
            print(f"  💡 Install optional dependencies if you need their features")
        
        # Performance insights
        slow_imports = [test for test in self.tests if test.success and test.import_time > 0.1]
        if slow_imports:
            print(f"\n⏱️  Slow imports (>0.1s):")
            for test in sorted(slow_imports, key=lambda x: x.import_time, reverse=True)[:5]:
                print(f"    • {test.module_name}: {test.import_time:.3f}s")
        
        return {
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_required": failed_required,
            "failed_optional": failed_optional,
            "success_rate": success_rate,
            "categories": categories,
            "all_required_passed": failed_required == 0
        }
    
    def save_report(self, filename: str = "accurate_import_report.txt"):
        """Save the test report to a file"""
        report_path = Path(__file__).parent / filename
        
        with open(report_path, 'w') as f:
            f.write("Accurate Import Test Report\n")
            f.write("=" * 50 + "\n\n")
            
            for test in self.tests:
                status = "PASS" if test.success else "FAIL"
                optional = " (OPTIONAL)" if test.is_optional else ""
                f.write(f"{status}{optional}: {test.module_name}\n")
                if test.description:
                    f.write(f"  Description: {test.description}\n")
                if not test.success:
                    f.write(f"  Error: {test.error_message}\n")
                f.write(f"  Import time: {test.import_time:.3f}s\n\n")
        
        print(f"\n📄 Report saved to: {report_path}")

def main():
    """Main function to run the accurate import tests"""
    tester = AccurateImportTester()
    results = tester.run_all_tests()
    
    # Save report
    tester.save_report()
    
    # Exit with appropriate code
    if results["all_required_passed"]:
        print("\n🎉 All required imports working correctly!")
        sys.exit(0)
    else:
        print(f"\n❌ {results['failed_required']} required imports failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()