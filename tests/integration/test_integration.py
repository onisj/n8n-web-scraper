#!/usr/bin/env python3
from src.n8n_scraper.workflow_integration import get_workflow_integration

# Test workflow integration
integration = get_workflow_integration()
print(f'Workflow Integration initialized: {integration}')
print(f'Database path: {integration.workflow_db_path}')
print(f'JSON directory: {integration.workflows_json_dir}')

# Test search functionality
print("\n=== Testing Search Functionality ===")
try:
    # Use WorkflowIntegration.search_workflows with correct parameters
    search_result = integration.search_workflows("telegram", category="all", limit=3)
    if search_result.get('success'):
        results = search_result.get('data', [])
        print(f"Found {len(results)} telegram workflows:")
        for workflow in results[:3]:  # Show first 3
            print(f"  - {workflow['name']} ({workflow['trigger_type']})")
    else:
        print(f"Search failed: {search_result.get('error')}")
except Exception as e:
    print(f"Search error: {e}")

# Test categories and integrations
print("\n=== Testing Categories and Integrations ===")
try:
    categories_result = integration.get_categories()
    if categories_result.get('success'):
        categories = categories_result.get('data', {})
        print(f"Categories result: {categories}")
    else:
        print(f"Categories failed: {categories_result.get('error')}")
except Exception as e:
    print(f"Categories error: {e}")

try:
    integrations_result = integration.get_integrations()
    if integrations_result.get('success'):
        integrations = integrations_result.get('data', {})
        print(f"Integrations result: {integrations}")
    else:
        print(f"Integrations failed: {integrations_result.get('error')}")
except Exception as e:
    print(f"Integrations error: {e}")

# Test direct database access
print("\n=== Testing Direct Database Access ===")
try:
    from src.n8n_scraper.database.workflow_db import WorkflowDatabase
    db = WorkflowDatabase(integration.workflow_db_path)
    service_categories = db.get_service_categories()
    print(f"Service categories from DB: {list(service_categories.keys())[:3]}...")  # Show first 3
except Exception as e:
    print(f"Direct DB access error: {e}")

print('\n=== Integration Test Complete ===')