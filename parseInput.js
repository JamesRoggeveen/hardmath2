// Configuration
const CONFIG = {
  BATCH_SIZE: 10,           // Number of rows to process in each batch
  DELAY_MS: 1000,          // Delay between API calls in milliseconds
  API_BASE_URL: "https://latex-parser-498348760329.us-central1.run.app"
};

// Helper function to process a single parse request
function parseInput(input) {
  input = input.replace(/\\/g, "\\\\");
  
  var options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify({ input: input }),
    "muteHttpExceptions": true
  };
  
  try {
    var response = UrlFetchApp.fetch(CONFIG.API_BASE_URL + "/parse", options);
    var responseText = response.getContentText();
    var responseCode = response.getResponseCode();
    
    // Log response for debugging
    Logger.log("Parse Response Code: " + responseCode);
    Logger.log("Parse Raw Response: " + responseText);
    
    if (responseCode !== 200) {
      return [false, `HTTP Error: ${responseCode} - ${responseText}`, "", "", ""];
    }
    
    try {
      var result = JSON.parse(responseText);
      return [
        result.parsed,
        result.error || "",
        Array.isArray(result.solution_latex) ? result.solution_latex.join("; ") : (result.solution_latex || ""),
        Array.isArray(result.solution_expr) ? result.solution_expr.join("; ") : (result.solution_expr || ""),
        Array.isArray(result.solution_eval) ? result.solution_eval.join("; ") : (result.solution_eval || "")
      ];
    } catch (jsonError) {
      return [false, `JSON Parse Error: ${jsonError.toString()} - Raw Response: ${responseText}`, "", "", ""];
    }
  } catch (e) {
    return [false, `Request Error: ${e.toString()}`, "", "", ""];
  }
}

// Helper function to process a single evaluation request
function evaluateProblem(input, solution) {
  input = input.replace(/\\/g, "\\\\");
  solution = solution.replace(/\\/g, "\\\\");
  
  var options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify({ input: input, solution: solution }),
    "muteHttpExceptions": true
  };
  
  try {
    var response = UrlFetchApp.fetch(CONFIG.API_BASE_URL + "/eval", options);
    var responseText = response.getContentText();
    var responseCode = response.getResponseCode();
    
    // Log response for debugging
    Logger.log("Eval Response Code: " + responseCode);
    Logger.log("Eval Raw Response: " + responseText);
    
    if (responseCode !== 200) {
      return [false, `HTTP Error: ${responseCode} - ${responseText}`, false, false, "", "", "", "", "", "", "", "", ""];
    }
    
    try {
      var result = JSON.parse(responseText);
      return [
        result.eval_equivalent,
        result.eval_error || "",
        result.model_parsed,
        result.solution_parsed,
        result.error || "",
        result.model_error || "",
        Array.isArray(result.model_eval) ? result.model_eval.join("; ") : (result.model_eval || ""),
        Array.isArray(result.solution_eval) ? result.solution_eval.join("; ") : (result.solution_eval || ""),
        Array.isArray(result.model_latex) ? result.model_latex.join("; ") : (result.model_latex || ""),
        Array.isArray(result.model_expr) ? result.model_expr.join("; ") : (result.model_expr || ""),
        Array.isArray(result.solution_latex) ? result.solution_latex.join("; ") : (result.solution_latex || ""),
        Array.isArray(result.solution_expr) ? result.solution_expr.join("; ") : (result.solution_expr || ""),
        result.query_response || ""
      ];
    } catch (jsonError) {
      return [false, `JSON Parse Error: ${jsonError.toString()} - Raw Response: ${responseText}`, false, false, "", "", "", "", "", "", "", "", ""];
    }
  } catch (e) {
    return [false, `Request Error: ${e.toString()}`, false, false, "", "", "", "", "", "", "", "", ""];
  }
}

// Main function to process the spreadsheet
function processSpreadsheet() {
  var sheet = SpreadsheetApp.getActiveSheet();
  var lastRow = sheet.getLastRow();
  var processedCount = 0;
  var startTime = new Date();
  
  // Get the operation type from cell A1
  var operationType = sheet.getRange("A1").getValue().toLowerCase();
  var isEvaluation = operationType.includes("eval");
  
  // Set up progress tracking
  var progressCell = sheet.getRange("A2");
  progressCell.setValue("Processing...");
  
  // Process in batches, starting from row 3
  for (var startRow = 3; startRow <= lastRow; startRow += CONFIG.BATCH_SIZE) {
    var endRow = Math.min(startRow + CONFIG.BATCH_SIZE - 1, lastRow);
    var batchRange = sheet.getRange(startRow, 1, endRow - startRow + 1, isEvaluation ? 2 : 1);
    var batchValues = batchRange.getValues();
    
    // Process each row in the batch
    for (var i = 0; i < batchValues.length; i++) {
      var currentRow = startRow + i;
      
      // Skip empty rows or already processed rows
      if (!batchValues[i][0] || (isEvaluation && !batchValues[i][1])) continue;
      
      try {
        var result;
        if (isEvaluation) {
          result = [evaluateProblem(batchValues[i][0], batchValues[i][1])];
          sheet.getRange(currentRow, 3, 1, result[0].length).setValues(result);
        } else {
          result = [parseInput(batchValues[i][0])];
          sheet.getRange(currentRow, 2, 1, result[0].length).setValues(result);
        }
        processedCount++;
        
        // Update progress
        progressCell.setValue(`Processed ${processedCount} rows...`);
        
        // Add delay between requests
        Utilities.sleep(CONFIG.DELAY_MS);
      } catch (e) {
        Logger.log(`Error processing row ${currentRow}: ${e.toString()}`);
        continue;
      }
    }
    
    // Check if we're approaching the timeout (5 minutes)
    if (new Date() - startTime > 4.5 * 60 * 1000) {
      progressCell.setValue(`Timeout reached. Processed ${processedCount} rows. Run again for remaining rows.`);
      return;
    }
  }
  
  progressCell.setValue(`Completed! Processed ${processedCount} rows.`);
}

// Function to set up the spreadsheet
function setupSpreadsheet() {
  var sheet = SpreadsheetApp.getActiveSheet();
  
  // Clear existing content
  sheet.clear();
  
  // Set up headers based on operation type
  sheet.getRange("A1").setValue("Operation Type (parse/eval)");
  sheet.getRange("A2").setValue("Status");
  
  // Add instructions
  sheet.getRange("A3").setValue("Instructions:");
  sheet.getRange("A4").setValue("1. Enter 'parse' or 'eval' in cell A1");
  sheet.getRange("A5").setValue("2. For parse: Put input in column A starting from row 3");
  sheet.getRange("A6").setValue("3. For eval: Put input in column A and solution in column B starting from row 3");
  sheet.getRange("A7").setValue("4. Run the script");
}