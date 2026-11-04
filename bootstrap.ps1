param(
  [string]$ToolsRoot,
  [string]$Workspace,
  [string]$GameContent,
  [string]$Optimizer,
  [switch]$Dev,
  [switch]$NoSelfTest
)
$ErrorActionPreference='Stop'
function Get-LiverySha256([string]$FilePath){
  $hash=[Security.Cryptography.SHA256]::Create()
  $stream=[IO.File]::OpenRead($FilePath)
  try{return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
  finally{$stream.Dispose();$hash.Dispose()}
}
$repo=$PSScriptRoot
if(-not [Environment]::Is64BitOperatingSystem){throw 'Windows x64 is required for the complete native workflow'}
if(-not $ToolsRoot){$ToolsRoot=Join-Path $env:LOCALAPPDATA 'ForzaLiveryAgent\tools'}
if(-not $Workspace){$Workspace=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'ForzaLiveryProjects'}
$ToolsRoot=[IO.Path]::GetFullPath($ToolsRoot)
$Workspace=[IO.Path]::GetFullPath($Workspace)
New-Item -ItemType Directory -Path $ToolsRoot -Force | Out-Null
$lock=Get-Content -LiteralPath (Join-Path $repo 'toolchain.lock.json') -Raw -Encoding utf8 | ConvertFrom-Json
$uvDir=Join-Path $ToolsRoot ('uv-'+$lock.uv.version)
$uvExe=Join-Path $uvDir 'uv.exe'
if(-not (Test-Path -LiteralPath $uvExe)){
  $archive=Join-Path $ToolsRoot 'uv-download.zip'
  [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
  Invoke-WebRequest -Uri $lock.uv.url -OutFile $archive -UseBasicParsing
  if((Get-LiverySha256 $archive) -ne $lock.uv.sha256){throw 'uv download SHA-256 mismatch'}
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $zip=[IO.Compression.ZipFile]::OpenRead($archive)
  try{
    $entry=@($zip.Entries | Where-Object {$_.Name -eq 'uv.exe'})
    if($entry.Count -ne 1){throw 'Unexpected uv release contents'}
    New-Item -ItemType Directory -Path $uvDir -Force | Out-Null
    [IO.Compression.ZipFileExtensions]::ExtractToFile($entry[0],$uvExe,$false)
  }finally{$zip.Dispose()}
  @{archiveSha256=$lock.uv.sha256;exeSha256=(Get-LiverySha256 $uvExe)} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $uvDir 'verified.json') -Encoding utf8
  Remove-Item -LiteralPath $archive
}
$proof=Get-Content -LiteralPath (Join-Path $uvDir 'verified.json') -Raw -Encoding utf8 | ConvertFrom-Json
if((Get-LiverySha256 $uvExe) -ne $proof.exeSha256){throw 'Installed uv changed; select a new tools directory'}
$oldPythonDir=$env:UV_PYTHON_INSTALL_DIR
$oldCacheDir=$env:UV_CACHE_DIR
try{
  $env:UV_PYTHON_INSTALL_DIR=Join-Path $ToolsRoot 'python'
  $env:UV_CACHE_DIR=Join-Path $ToolsRoot 'cache\uv'
  $argsList=@('run','--no-project','--python',$lock.python,(Join-Path $repo 'scripts\bootstrap.py'),'--uv',$uvExe,'--tools-root',$ToolsRoot,'--workspace',$Workspace)
  if($GameContent){$argsList+=@('--game-content',$GameContent)}
  if($Optimizer){$argsList+=@('--optimizer',$Optimizer)}
  if($Dev){$argsList+='--dev'}
  if($NoSelfTest){$argsList+='--no-self-test'}
  & $uvExe @argsList
  if($LASTEXITCODE -ne 0){throw "Bootstrap failed with exit $LASTEXITCODE"}
}finally{
  $env:UV_PYTHON_INSTALL_DIR=$oldPythonDir
  $env:UV_CACHE_DIR=$oldCacheDir
}
