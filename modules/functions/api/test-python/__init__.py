import logging
import azure.functions as func
import json
import sys
import pkg_resources

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Testing Python environment in Azure Functions')
    
    try:
        # Get Python version
        python_version = sys.version
        
        # Get available packages
        installed_packages = []
        for package in pkg_resources.working_set:
            installed_packages.append({
                'name': package.project_name,
                'version': package.version
            })
        
        # Sort by name
        installed_packages.sort(key=lambda x: x['name'])
        
        # Look for database-related packages
        db_packages = [pkg for pkg in installed_packages if any(
            term in pkg['name'].lower() 
            for term in ['sql', 'db', 'postgres', 'pyodbc', 'azure', 'requests', 'urllib']
        )]
        
        response_data = {
            'success': True,
            'python_version': python_version,
            'total_packages': len(installed_packages),
            'database_packages': db_packages,
            'all_packages': installed_packages[:50]  # First 50 packages
        }
        
        return func.HttpResponse(
            json.dumps(response_data, indent=2),
            status_code=200,
            mimetype="application/json"
        )
        
    except Exception as e:
        error_response = {
            'success': False,
            'error': str(e),
            'python_version': sys.version
        }
        
        return func.HttpResponse(
            json.dumps(error_response, indent=2),
            status_code=500,
            mimetype="application/json"
        )
