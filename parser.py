import sympy as sp
from sympy.parsing.sympy_parser import standard_transformations, implicit_multiplication_application, convert_xor, implicit_application
import os
import regex as re
import numpy as np
import argparse

def extract_solution(solution_string):
  """ Searches LLM response for boxed solution and returns it

  Searches through output generated by LLM in response to a given problem and
  extracts the boxed answer. Returns None if no boxed answer is found. Also returns 
  a string indicating the type of error that occurred if no boxed answer is found.

  Parameters
  ----------
  solution_string: str
  """
  solution_group = re.search(r'boxed\{(.*)\}', solution_string)
  if solution_group:
    solution = solution_group.group(1)
    solution_list = solution.split(';')
    solution_list = [s.strip() for s in solution_list]
    return solution_list
  else:
    raise ValueError("No boxed solution found")

# This should probably not be a dictionary as order of rule application matters
replacement_rules = {
    r'\\approx': r'=',                                  # replace all forms of approximate equals
    r'\\sim': r'=',
    r'\\pm': r'',                                       # rewrite plus or minus to take positive branch (FIX LATER)
    r'\\left': r'',                                     # delete latex formatting
    r'\\right': r'',
    r'\\sqrt\[(\d+?)\]\{(.*?)\}': r'(\1)^(1/(\2))',     # rewrite fractional powers that were expressed using \sqrt fn (may be issues with expression inside sqrt)
    r'\\frac\{(.*?)\}\{(.*?)\}': r'((\1)/(\2))',        # rewrite \frac functions
    r'(?<![a-zA-Z])e(?![a-zA-Z])': r'E',
    r'_\{(.*?)\}': r'\1',                               # for variable identification, rewrite all underscores
    r'\{': r'(',                                        # remove bracket formatting (especially important for exponents)
    r'\}': r')',
    r'\\': r''                                          # remove remaining escape characters
}

def latex_to_expression(latex_string):
  """Applies replacement rules to a LaTeX expression.

  Converts a string containing a LaTeX math expression into one compatible
  with sympy's parse_expr function by applying a custom set of replacement
  rules.

  Parameters
  ----------
  latex_string: str
  """
  for pattern, replacement in replacement_rules.items():
    latex_string = re.sub(pattern, replacement, latex_string)
  return latex_string

def expression_to_sympy(expr_string):
  """Converts an expression string to a sympy expression.

  Uses sympy's parse_expr function to convert a string containing a mathematical
  expression into a sympy expression object. Uses sympy transformation functions
  to handle certain inputs without requiring use of custom rules. Returns None
  if conversion fails.

  Parameters
  ----------
  expr_string: str
  """
  try:
    if "=" in expr_string:
      expr_string = expr_string.split("=")[1].strip()
    if ',' in expr_string:
      expr_string = expr_string.split(',')[0].strip()
    # expr = parse_latex(latex_string)
    transformations = (standard_transformations + (implicit_multiplication_application,convert_xor,implicit_application))
    expr = sp.parsing.parse_expr(expr_string,transformations=transformations)
    return expr
  except Exception as e:
    raise ValueError("Sympy conversion failure")

def solution_to_sympy(solution_string):
  """ Converts solution string to sympy expression

  Takes an LLM solution to a given math problem, extracts the boxed answer,
  converts it to a sympy expression using the latex_to_expression and
  expression_to_sympy functions, and returns the sympy expression. Returns None
  if any step of the conversion fails.

  Parameters
  ----------
  solution_string: str
  """
  error_message = ""
  extracted_solution = None
  solution_expr_list = None
  solution_sympy_list = None
  try:
    extracted_solution = extract_solution(solution_string)
  except ValueError as e:
    error_message = e.args[0]
  if error_message == "":
    solution_expr_list = [latex_to_expression(s) for s in extracted_solution]
    try:
      solution_sympy_list = [expression_to_sympy(s) for s in solution_expr_list]
    except ValueError as e:
      error_message = e.args[0]
  return solution_sympy_list, error_message, extracted_solution, solution_expr_list

def evaluate_sympy_solution(sympy_solution, t):
  """ Evaluates sympy expression at given value of t

  Given a sympy expression written for the variable x, evaluates the expression
  at the given value of x=t and returns the result as a numpy float32.

  Parameters
  ----------
  sympy_solution: sympy expression
  t: float
  """
  try:
    x = sp.symbols('x')
    result = sympy_solution.subs(x, t).evalf()
    return np.array(float(result),dtype=np.float32)
  except Exception as e:
    raise ValueError("Sympy expression evaluation failure")

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Parse and evaluate LaTeX expressions')
    parser.add_argument('expression', type=str, help='LaTeX expression to evaluate')
    parser.add_argument('--t', type=float, default=2.0, 
                       help='Value of x to evaluate expression at (default: 2.0)')
    
    args = parser.parse_args()
    
    # Convert the LaTeX expression to sympy and evaluate
    sympy_expr, error_message, extracted_solution, solution_expr_list = solution_to_sympy(args.expression)
    if sympy_expr is not None:
        result = evaluate_sympy_solution(sympy_expr, args.t)
        print(f"Result at x = {args.t}: {result}")
    else:
        print("Failed to parse the expression")