function parseInput(input) {
  // Escape any backslashes: replace "\" with "\\".
  input = input.replace(/\\/g, "\\\\");
  
  var url = "https://latex-parser-498348760329.us-central1.run.app/parse";
  var payload = JSON.stringify({ input: input });
  var options = {
    "method": "post",
    "contentType": "application/json",
    "payload": payload
  };
  
  try {
    var response = UrlFetchApp.fetch(url, options);
    var result = JSON.parse(response.getContentText());
    
    // If the response includes a 'solution', return [parsed, solution]
    if (result.solution !== undefined) {
      return [[result.parsed, result.solution]];
    }
    // Otherwise, if it includes an 'error', return [parsed, error]
    else if (result.error !== undefined) {
      return [[result.parsed, result.error]];
    }
    // If neither key is present, return an unexpected response message.
    else {
      return [["Unexpected response", JSON.stringify(result)]];
    }
  } catch (e) {
    // In case of an error (network, parsing, etc.), return the error in two cells.
    return [["Error", e.toString()]];
  }
}