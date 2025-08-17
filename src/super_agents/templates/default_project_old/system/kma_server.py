
import json
import os
from flask import Flask, request, jsonify

app = Flask(__name__)
DB_FILE = os.path.join(os.path.dirname(__file__), "kma_database.json")

def get_db():
    if not os.path.exists(DB_FILE):
        return {"files": {}, "components": {}, "contracts": {}}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"files": {}, "components": {}, "contracts": {}}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

@app.route('/mcp', methods=['POST'])
def mcp_endpoint():
    data = request.json
    tool_name = data.get('tool_name')
    tool_input = data.get('tool_input', {})
    db = get_db()
    
    response = {}
    
    try:
        if tool_name == 'register_file':
            path = tool_input.get('file_path')
            description = tool_input.get('description')
            db['files'][path] = {'description': description, 'api_surface': tool_input.get('api_surface')}
            response = {"success": True, "message": f"File {path} registered."}

        elif tool_name == 'get_file_path':
            # This logic should be enhanced with rules from CLAUDE.md
            comp_name = tool_input.get('component_name')
            comp_type = tool_input.get('component_type', 'general')
            # Example for a monorepo
            path = f"packages/client/src/components/{comp_name}.jsx"
            response = {"path": path}

        elif tool_name == 'get_api':
            path = tool_input.get('file_path')
            if path in db['files'] and 'api_surface' in db['files'][path]:
                response = {"api": db['files'][path]['api_surface']}
            else:
                response = {"error": "API surface not found for this file."}
        
        elif tool_name == 'get_dependencies':
            # Placeholder for a more complex dependency analysis tool
            # In a real system, this would parse package.json files
            path = tool_input.get('file_path')
            response = {"dependencies": ["@my-app/client", "@my-app/shared-ui"]}

        else:
            return jsonify({"error": f"Unknown tool: {tool_name}"}), 400
        
        save_db(db)
        return jsonify({"tool_response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_mcp_spec():
    return {
        "protocol_version": "1.0",
        "tools": [
            {"tool_name": "register_file", "description": "Registers a file in the codebase manifest.", "parameters": [
                {"name": "file_path", "type": "string"}, {"name": "description", "type": "string"}, {"name": "api_surface", "type": "string"}
            ]},
            {"tool_name": "get_file_path", "description": "Gets the canonical file path for a new component.", "parameters": [
                {"name": "component_name", "type": "string"}, {"name": "component_type", "type": "string"}
            ]},
            {"tool_name": "get_api", "description": "Gets the registered API surface for a component.", "parameters": [
                {"name": "file_path", "type": "string"}
            ]},
            {"tool_name": "get_dependencies", "description": "Gets a list of packages that depend on a given file.", "parameters": [
                {"name": "file_path", "type": "string"}
            ]}
        ]
    }

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'spec':
        print(json.dumps(get_mcp_spec()))
    else:
        # Ensure the database file exists
        if not os.path.exists(DB_FILE):
            save_db({"files": {}, "components": {}, "contracts": {}})
        app.run(port=5001, host='0.0.0.0')
