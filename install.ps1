# Hometax help installer for Windows PowerShell. install.py performs the install.
# If script execution is blocked, run this in the same folder: py -3 install.py
$ErrorActionPreference = 'Stop'
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Installer = Join-Path $Here 'install.py'
if (-not (Test-Path -LiteralPath $Installer)) {
    Write-Error 'install.py is missing. Check the package contents.'
}
function Find-Python {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) { return @{ File = $py.Source; Prefix = @('-3') } }
    foreach ($name in @('python', 'python3')) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return @{ File = $cmd.Source; Prefix = @() } }
    }
    return $null
}
$Python = Find-Python
if (-not $Python) {
    Write-Error 'Python 3.10 or newer is required. Install it from https://www.python.org/downloads/ and run py -3 install.py.'
}
$PythonArgs = @($Python.Prefix) + @('-B', $Installer) + @($args)
& $Python.File @PythonArgs
exit $LASTEXITCODE
