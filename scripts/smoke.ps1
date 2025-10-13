param(
    [string]$BaseUrl = "http://localhost:8001"
)

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
$inputsPath = Join-Path $root "inputs"
$outputsPath = Join-Path $root "outputs"
$sampleFile = Join-Path $inputsPath "test_project_sample.txt"

if (-not (Test-Path $sampleFile)) {
    throw "Sample input file not found at $sampleFile"
}

Write-Host "Running smoke script against $BaseUrl" -ForegroundColor Cyan

# Draft (ingest via curl). To avoid quoting issues with spaces in paths, copy to temp.
$tempSample = Join-Path $env:TEMP 'sbp_test_project_sample.txt'
Copy-Item -Force $sampleFile $tempSample
$ingestJson = & curl.exe -s -X POST -F files=@$tempSample -F project_name='ACME_Bracket_Test' -F customer='ACME' -F family='Brackets' "$BaseUrl/ingest"
if (-not $ingestJson) {
    throw "Failed to ingest sample file: empty response from server."
}
try {
    $session = $ingestJson | ConvertFrom-Json
} catch {
    Write-Host "Raw ingest response:" -ForegroundColor Yellow
    Write-Host $ingestJson
    throw "Failed to parse ingest response."
}
if (-not $session.session_id) {
    throw "Failed to ingest sample file."
}

$projectName = 'ACME Bracket Test'
${draftBody} = @{
    session_id = $session.session_id
    project_name = $projectName
    customer = 'ACME'
    family = 'Brackets'
}
$draftResponse = Invoke-RestMethod -Method Post "$BaseUrl/draft" -ContentType 'application/json' -Body (${draftBody} | ConvertTo-Json -Depth 6)
($draftResponse | ConvertTo-Json -Depth 10) | Out-File (Join-Path $outputsPath '_smoke_draft.json') -Encoding utf8

# Agents run
${agentBody} = @{
    session_id = $session.session_id
    vector_store_id = $draftResponse.vector_store_id
    plan_json = $draftResponse.plan_json
    context_pack = $draftResponse.context_pack
}
$agentsResponse = Invoke-RestMethod -Method Post "$BaseUrl/agents/run" -ContentType 'application/json' -Body (${agentBody} | ConvertTo-Json -Depth 10)
($agentsResponse | ConvertTo-Json -Depth 12) | Out-File (Join-Path $outputsPath '_smoke_agents.json') -Encoding utf8

$qaScore = if ($agentsResponse.qa) { $agentsResponse.qa.score } else { $null }
$qaBlocked = if ($agentsResponse.qa) { $agentsResponse.qa.blocked } else { $null }
$suggestedCount = if ($agentsResponse.tasks_suggested) { $agentsResponse.tasks_suggested.Count } else { 0 }
Write-Host "Agents QA Score=$qaScore Blocked=$qaBlocked SuggestedTasks=$suggestedCount" -ForegroundColor Yellow

# Publish (optional; skip if not configured)
try {
    $latestMarkdown = Get-ChildItem -Path $outputsPath -Filter 'Strategic_Build_Plan__*.md' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latestMarkdown) {
        $markdownContent = Get-Content $latestMarkdown.FullName -Raw
        $publishBody = @{
            customer = 'ACME'
            family = 'Brackets'
            project = $projectName
            markdown = $markdownContent
        }
        Invoke-RestMethod -Method Post "$BaseUrl/publish" -ContentType 'application/json' -Body ($publishBody | ConvertTo-Json -Depth 4) |
            Out-File (Join-Path $outputsPath '_smoke_publish.json') -Encoding utf8
    }
} catch {
    Write-Host "Publish step skipped or failed (likely not configured)." -ForegroundColor DarkYellow
}

# QA
$latestJson = Get-ChildItem -Path $outputsPath -Filter 'Strategic_Build_Plan__*.json' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latestJson) {
    throw "No JSON plan found in outputs/. Run draft first."
}
$planJson = Get-Content $latestJson.FullName -Raw | ConvertFrom-Json
$planForQa = if ($agentsResponse.plan_json) { $agentsResponse.plan_json } else { $planJson }
$qaBody = @{ plan_json = $planForQa }
Invoke-RestMethod -Method Post "$BaseUrl/qa/grade" -ContentType 'application/json' -Body ($qaBody | ConvertTo-Json -Depth 10) |
    Out-File (Join-Path $outputsPath '_smoke_qa.json') -Encoding utf8

Write-Host "Smoke script completed. Results in outputs/_smoke_*.json" -ForegroundColor Green
