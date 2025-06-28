#!/usr/bin/env python3
"""
Import Test Runner for n8n Web Scraper

This script runs comprehensive import tests and provides a detailed report
of which imports are working and which are failing.
"""

import sys
import importlib
from pathlib import Path
from typing import List, Tuple, Dict
from dataclasses import dataclass

# Add project paths to Python path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"

# Add both project root (for config) and src (for n8n_scraper) to path
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_path))

@dataclass
class ImportResult:
    """Result of an import test"""
    module_name: str
    success: bool
    error_message: str = ""
    category: str = ""

class ImportTester:
    """Comprehensive import tester for the n8n web scraper project"""
    
    def __init__(self):
        self.results: List[ImportResult] = []
        
        # Define all modules to test by category
        self.test_modules = {
            "Core Package": [
                "n8n_scraper",
                "config.settings"
            ],
            "Core": [
                 "n8n_scraper.database.vector_db"
             ],
            "AI Agents": [
                "n8n_scraper.agents.n8n_agent",
                "n8n_scraper.agents.knowledge_processor"
            ],
            "Automation": [
                "n8n_scraper.automation.update_scheduler",
                "n8n_scraper.automation.knowledge_updater",
                "n8n_scraper.automation.change_detector"
            ],
            "API": [
                "n8n_scraper.api.main",
                "n8n_scraper.api.routes.ai_routes",
                "n8n_scraper.api.routes.knowledge_routes",
                "n8n_scraper.api.routes.system_routes"
            ],
            "Utilities": [
                # Note: utils directory doesn't exist in current structure
            ],
            "Scripts": [
                "scripts.start_system"
            ],
            "Tools": [
                "tools.system_check"
            ],
            "Web Scraping Dependencies": [
                "requests",
                "bs4",
                "selenium",
                "aiohttp"
            ],
            "Data Processing Dependencies": [
                "pandas",
                "numpy",
                "json",
                "yaml",
                "sqlite3"
            ],
            "Web Framework Dependencies": [
                "fastapi",
                "uvicorn",
                # "streamlit",  # Removed - replaced by Next.js frontend
                "pydantic"
            ],
            "AI/ML Dependencies (Optional)": [
                "openai",
                "langchain",
                "nltk"
            ],
            "System Dependencies": [
                "schedule",
                "threading",
                "subprocess",
                "datetime",
                "pathlib",
                "os",
                "sys"
            ]
        }
    
    def test_import(self, module_name: str, category: str) -> ImportResult:
        """Test importing a single module"""
        try:
            module = importlib.import_module(module_name)
            if module is None:
                return ImportResult(
                    module_name=module_name,
                    success=False,
                    error_message="Module imported but is None",
                    category=category
                )
            return ImportResult(
                module_name=module_name,
                success=True,
                category=category
            )
        except ImportError as e:
            return ImportResult(
                module_name=module_name,
                success=False,
                error_message=str(e),
                category=category
            )
        except Exception as e:
            return ImportResult(
                module_name=module_name,
                success=False,
                error_message=f"Unexpected error: {str(e)}",
                category=category
            )
    
    def run_all_tests(self) -> None:
        """Run all import tests"""
        print("🔍 Running comprehensive import tests...\n")
        
        for category, modules in self.test_modules.items():
            print(f"Testing {category}...")
            
            for module_name in modules:
                result = self.test_import(module_name, category)
                self.results.append(result)
                
                status = "✅" if result.success else "❌"
                print(f"  {status} {module_name}")
                
                if not result.success and result.error_message:
                    print(f"    Error: {result.error_message}")
            
            print()  # Empty line between categories
    
    def generate_report(self) -> None:
        """Generate a comprehensive report of test results"""
        print("\n" + "="*80)
        print("📊 IMPORT TEST REPORT")
        print("="*80)
        
        # Summary statistics
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results if r.success)
        failed_tests = total_tests - successful_tests
        success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n📈 Summary:")
        print(f"  Total tests: {total_tests}")
        print(f"  Successful: {successful_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Success rate: {success_rate:.1f}%")
        
        # Group results by category
        results_by_category: Dict[str, List[ImportResult]] = {}
        for result in self.results:
            if result.category not in results_by_category:
                results_by_category[result.category] = []
            results_by_category[result.category].append(result)
        
        # Detailed results by category
        print(f"\n📋 Detailed Results by Category:")
        for category, results in results_by_category.items():
            successful = sum(1 for r in results if r.success)
            total = len(results)
            
            print(f"\n  {category}: {successful}/{total} successful")
            
            # Show failed imports
            failed_results = [r for r in results if not r.success]
            if failed_results:
                print(f"    Failed imports:")
                for result in failed_results:
                    print(f"      ❌ {result.module_name}: {result.error_message}")
        
        # Recommendations
        print(f"\n💡 Recommendations:")
        
        if failed_tests == 0:
            print("  🎉 All imports are working correctly! Your environment is properly set up.")
        else:
            print(f"  📦 Install missing dependencies for failed imports")
            print(f"  🔧 Check module paths and file structure for internal modules")
            print(f"  📝 Review pyproject.toml dependencies")
            
            # Suggest specific actions for common issues
            failed_external = [r for r in self.results if not r.success and not r.module_name.startswith('n8n_scraper')]
            if failed_external:
                print(f"  🛠️  Run: pip install -r requirements.txt")
            
            failed_internal = [r for r in self.results if not r.success and r.module_name.startswith('n8n_scraper')]
            if failed_internal:
                print(f"  📁 Check that all source files exist in the expected locations")
        
        print("\n" + "="*80)
    
    def save_report(self, filename: str = "import_test_report.txt") -> None:
        """Save the report to a file"""
        report_path = Path(__file__).parent / filename
        
        with open(report_path, 'w') as f:
            f.write("Import Test Report\n")
            f.write("=" * 50 + "\n\n")
            
            # Summary
            total_tests = len(self.results)
            successful_tests = sum(1 for r in self.results if r.success)
            failed_tests = total_tests - successful_tests
            success_rate = (successful_tests / total_tests * 100) if total_tests > 0 else 0
            
            f.write(f"Summary:\n")
            f.write(f"Total tests: {total_tests}\n")
            f.write(f"Successful: {successful_tests}\n")
            f.write(f"Failed: {failed_tests}\n")
            f.write(f"Success rate: {success_rate:.1f}%\n\n")
            
            # Detailed results
            f.write("Detailed Results:\n")
            for result in self.results:
                status = "PASS" if result.success else "FAIL"
                f.write(f"[{status}] {result.module_name}")
                if not result.success:
                    f.write(f" - {result.error_message}")
                f.write("\n")
        
        print(f"📄 Report saved to: {report_path}")

def main():
    """Main function to run import tests"""
    tester = ImportTester()
    
    try:
        tester.run_all_tests()
        tester.generate_report()
        
        # Save report if requested
        if len(sys.argv) > 1 and sys.argv[1] == "--save":
            tester.save_report()
        
        # Exit with appropriate code
        failed_tests = sum(1 for r in tester.results if not r.success)
        sys.exit(0 if failed_tests == 0 else 1)
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during testing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()