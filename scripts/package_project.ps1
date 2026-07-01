$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$python = "C:\Users\Lenovo\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
& $python (Join-Path $root "scripts\package_project.py")
