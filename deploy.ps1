param (
    [string]$Message = "sync and deploy site updates"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " ASHNEL INC. - SYNC AND DEPLOY" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. Stage and commit
Write-Host "`n[1/3] Staging changes..." -ForegroundColor Yellow
git add .

$status = git status --porcelain
if ($status) {
    Write-Host "[2/3] Committing: '$Message'..." -ForegroundColor Yellow
    git commit -m "$Message"
    Write-Host "Pushing to GitHub (origin/main)..." -ForegroundColor Yellow
    git push origin main
} else {
    Write-Host "[2/3] Working tree clean. Pushing to origin/main if needed..." -ForegroundColor Green
    git push origin main
}

# 2. Deploy to Gawah server
Write-Host "`n[3/3] Deploying to Gawah server (76.13.99.12 -> /home/ashnel.com)..." -ForegroundColor Yellow
$VENV_PYTHON = "c:\Users\nevil\Documents\GitHub\marryacatholic\.venv\Scripts\python.exe"
if (Test-Path $VENV_PYTHON) {
    & $VENV_PYTHON scratch\deploy.py
} else {
    Write-Error "Virtualenv Python not found at $VENV_PYTHON"
}
