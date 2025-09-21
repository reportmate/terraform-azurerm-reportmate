import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({'success': True, 'events': [], 'count': 0}),
        status_code=200,
        mimetype='application/json'
    )
