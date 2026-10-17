# Copies the skill into your user skills folder so Claude Code can load it everywhere.
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $HOME ".claude\skills" }
$dest = Join-Path $root "cuelab"
New-Item -ItemType Directory -Force -Path $root | Out-Null
if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
Copy-Item -Recurse -Path (Join-Path $here "skills\cuelab") -Destination $dest
Write-Host "installed to $dest"
