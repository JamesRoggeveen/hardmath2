from flask import Flask, request, jsonify
import parser

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "latex-parser"})

def my_parse_function(input_string):
    if not input_string:
        return {"error": "No input provided", "parsed": False}
        
    extracted_solution = parser.extract_solution(input_string)
    if extracted_solution is None:
        return {"error": "Could not extract solution from input", "parsed": False}
        
    expr = parser.latex_to_expression(extracted_solution)
    sympy_solution = parser.expression_to_sympy(expr)
    
    if sympy_solution is None:
        return {"error": "Could not parse expression", "parsed": False}
    
    try:
        evaluated_solution = float(parser.evaluate_sympy_solution(sympy_solution, 2))
        return {"solution": evaluated_solution, "parsed": True}
    except Exception as e:
        return {"error": f"Error evaluating expression: {str(e)}", "parsed": False}

@app.route('/parse', methods=['POST'])
def parse():
    try:
        data = request.get_json()
        if not data or 'input' not in data:
            return jsonify({"error": "Missing input field", "parsed": False}), 400
            
        input_string = data['input']
        result = my_parse_function(input_string)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}", "parsed": False}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)