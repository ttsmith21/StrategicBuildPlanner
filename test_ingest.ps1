# Test the /ingest endpoint
# Run this in a SEPARATE PowerShell window while the server is running

Write-Host "Testing /ingest endpoint..." -ForegroundColor Cyan

$response = curl.exe -s -X POST http://127.0.0.1:8001/ingest `
  -F "project_name=Test Project" `
  -F "customer=ACME Corp" `
  -F "files=@inputs/sample_project_test.txt"

Write-Host "`nResponse:" -ForegroundColor Green
$response | ConvertFrom-Json | ConvertTo-Json -Depth 10

Write-Host "`n✅ If you see session_id, vector_store_id, and context_pack, it's working!" -ForegroundColor Green
