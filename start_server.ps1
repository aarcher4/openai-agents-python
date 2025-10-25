# Start Document Extraction Server
Write-Host "=== Document Extraction Server Startup ===" -ForegroundColor Cyan
Write-Host ""

# Check for OpenAI API Key
if (-not $env:OPENAI_API_KEY) {
    Write-Host "OPENAI_API_KEY is not set." -ForegroundColor Yellow
    Write-Host "Please enter your OpenAI API key (or press Ctrl+C to cancel):" -ForegroundColor Yellow
    $apiKey = Read-Host -AsSecureString
    $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKey)
    $env:OPENAI_API_KEY = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
    
    if (-not $env:OPENAI_API_KEY) {
        Write-Host "Error: API key is required. Exiting." -ForegroundColor Red
        exit 1
    }
    
    Write-Host "API key set successfully!" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Using existing OPENAI_API_KEY from environment." -ForegroundColor Green
    Write-Host ""
}

# Add uv to PATH
$env:PATH = "C:\Users\Alex Archer\.local\bin;" + $env:PATH

# Navigate to project directory
$projectPath = "C:\Users\Alex Archer\Desktop\openai-agents-python"
Set-Location $projectPath

Write-Host "Starting server on http://localhost:5003 ..." -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""
Write-Host "Once started, open your browser to: http://localhost:5003" -ForegroundColor Green
Write-Host ""

# Start the server
& uv run uvicorn examples.document_extraction.web_server:app --host 127.0.0.1 --port 5003

