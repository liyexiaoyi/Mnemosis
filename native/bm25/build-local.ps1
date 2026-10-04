param(
    [string]$StorageRoot = 'E:\Mnemosis',
    [string]$PythonExecutable = 'C:\Python314\python.exe',
    [string]$WheelOutput = 'E:\Mnemosis\tools\wheels'
)
$ErrorActionPreference = 'Stop'
$env:RUSTUP_HOME = Join-Path $StorageRoot 'tools\rustup'
$env:CARGO_HOME = Join-Path $StorageRoot 'tools\cargo'
$env:RUSTUP_TOOLCHAIN = '1.99.0-x86_64-pc-windows-gnu'
$env:PATH = (Join-Path $env:CARGO_HOME 'bin') + ';' + $env:PATH
$env:PYO3_PYTHON = $PythonExecutable
# The minimal GNU toolchain has a linker but no standalone assembler.
# Use CPython's existing import library instead of raw-dylib/dlltool assembly.
$env:PYO3_USE_RAW_DYLIB = '0'
$maturinPath = Join-Path $StorageRoot 'tools\python\bin\maturin.exe'
& $maturinPath build --release --locked --manifest-path (Join-Path $PSScriptRoot 'Cargo.toml') --interpreter $PythonExecutable --out $WheelOutput
if ($LASTEXITCODE -ne 0) { throw "Native build failed: $LASTEXITCODE" }
