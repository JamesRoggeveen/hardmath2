from flask import Flask, request, jsonify
import parser
import os
# from dotenv import load_dotenv
import google.generativeai as genai
import numpy as np
# Load environment variables from .env file in development
# if os.environ.get('FLASK_ENV') != 'production':
#     load_dotenv()

app = Flask(__name__)

# Get the API key from environment variable
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("Gemini API key not found in environment variables")

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "service": "latex-parser"})

def my_parse_function(input_string):
    output = {"parsed": False,
              "error": "",
              "solution_latex": None,
              "solution_expr": None,
              "solution_eval": None}
    if not input_string:
        output["error"] = "No input provided"
        return output
    
    try:
        extracted_solution = parser.extract_solution(input_string)
        output["solution_latex"] = extracted_solution
    except Exception as e:
        output["error"] = f"Could not extract solution from input: {str(e)}"
        return output
        
    expr_list = [parser.latex_to_expression(s) for s in extracted_solution]
    output["solution_expr"] = expr_list
    try:
        sympy_solution_list = [parser.expression_to_sympy(expr) for expr in expr_list]
    except Exception as e:
        output["error"] = f"Could not parse expression: {str(e)}"
        return output
    try:
        evaluated_solution = [float(parser.evaluate_sympy_solution(sympy_solution, 2)) for sympy_solution in sympy_solution_list]
        output["solution_eval"] = evaluated_solution
        output["parsed"] = True
        return output
    except Exception as e:
        output["error"] = f"Error evaluating expression: {str(e)}"
        return output
    
def my_query_function(input_string):
    output = {"parsed": False,
              "error": "",
              "solution_latex": None,
              "solution_expr": None,
              "solution_eval": None,
              "query_response": None}
    genai.configure(api_key=GEMINI_API_KEY)
    Gemini_Model = genai.GenerativeModel('models/gemini-2.0-flash-thinking-exp')
    try:
        response = Gemini_Model.generate_content(input_string)
        output["query_response"] = response.text
        parse_output = my_parse_function(response.text)
        for key, value in parse_output.items():
            output[key] = value
        return output
    except Exception as e:
        output["error"] = f"Error querying Gemini: {str(e)}"
        return output
    
def my_eval_function(input_string,solution_string):
    output = {"error": "",
              "solution_parsed": False,
              "error": "",
              "solution_latex": None,
              "solution_expr": None,
              "solution_eval": None,
              "model_parsed":False,
              "model_latex": None,
              "model_error": "",
              "model_expr": None,
              "model_eval": None,
              "eval_error": "",
              "eval_equivalent": False,
              "query_response": None}
    try:
        query_output = my_query_function(input_string)
        output["query_response"] = query_output["query_response"]
        output["model_latex"] = query_output["solution_latex"]
        output["model_expr"] = query_output["solution_expr"]
        output["model_eval"] = query_output["solution_eval"]
        output["model_parsed"] = query_output["parsed"]
        
        solution_output = my_parse_function(solution_string)
        for key, value in solution_output.items():
            output[key] = value
        model_eval = np.array(output["model_eval"])
        solution_eval = np.array(output["solution_eval"])
        if model_eval.shape != solution_eval.shape:
            output["eval_error"] = "Model and solution eval arrays have different shapes"
            return output
        if np.allclose(model_eval, solution_eval, atol=1e-6):
            output["eval_equivalent"] = True
        else:
            output["eval_equivalent"] = False
        return output
    except Exception as e:
        output["error"] = f"Error evaluating model: {str(e)}"
        return output
    
def check_field(data, key):
    if key not in data:
        return f"Missing '{key}' field in JSON", 400
    if not isinstance(data[key], str):
        return f"{key} must be a string", 400
    if not data[key].strip():
        return f"{key} string is empty", 400
    return None, 200  # Return None for error and 200 for status when check passes

@app.route('/parse', methods=['POST'])
def parse():
    output = {"parsed": False,
              "error": "",
              "solution_latex": None,
              "solution_expr": None,
              "solution_eval": None}
    try:
        data = request.get_json()
        if not data or 'input' not in data:
            output["error"] = "Missing input field"
            return jsonify(output), 400
            
        input_string = data['input']
        result = my_parse_function(input_string)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Server error: {str(e)}", "parsed": False}), 500
    
@app.route('/query', methods=['POST'])
def query():
    output = {"parsed": False,
              "error": "",
              "solution_latex": None,
              "solution_expr": None,
              "solution_eval": None}
    try:
        data = request.get_json()
        if not data:
            output["error"] = "No JSON data provided"
            return jsonify(output), 400
        error, status_code = check_field(data,'input')
        if error:
            return jsonify({"error": error}), status_code
        
        input_string = data['input']
        result = my_query_function(input_string)
        return jsonify(result)
    except Exception as e:
        output["error"] = f"Server error: {str(e)}"
        return jsonify(output), 500
    
@app.route('/eval', methods=['POST'])
def eval():
    output = {"error": "",
              "solution_parsed": False,
              "error": "",
              "solution_latex": None,
              "solution_expr": None,
              "solution_eval": None,
              "model_parsed":False,
              "model_latex": None,
              "model_error": "",
              "model_expr": None,
              "model_eval": None,
              "eval_error": "",
              "eval_equivalent": False,
              "query_response": None}
    try:
        data = request.get_json()
        if not data:
            output["error"] = "No JSON data provided"
            return jsonify(output), 400
        for key in ['input','solution']:
            error, status_code = check_field(data,key)
            if error:
                return jsonify({"error": error}), status_code
        
        input_string = data['input']
        solution_string = data['solution']
        result = my_eval_function(input_string,solution_string)
        return jsonify(result)
    except Exception as e:
        output["error"] = f"Server error: {str(e)}"
        return jsonify(output), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)