param([Parameter(Mandatory=$true)][string]$PlanPath)
$ErrorActionPreference='Stop'
function Get-LiverySha256([string]$FilePath){
  $hash=[Security.Cryptography.SHA256]::Create();$stream=[IO.File]::OpenRead($FilePath)
  try{return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
  finally{$stream.Dispose();$hash.Dispose()}
}
$plan=Get-Content -LiteralPath $PlanPath -Raw -Encoding utf8 | ConvertFrom-Json
if($plan.kind -ne 'owned-regenerable-fit-buffers'){throw 'Unexpected buffer plan'}
$root=(Resolve-Path -LiteralPath $plan.root).Path.TrimEnd('\')
foreach($entry in $plan.files){
  $path=(Resolve-Path -LiteralPath $entry.path).Path
  if(-not $path.StartsWith($root+'\work\',[StringComparison]::OrdinalIgnoreCase)){throw 'Buffer path escaped work directory'}
  $item=Get-Item -LiteralPath $path
  if($item.Name -notin @('target.rgb','foreground.bin','weights.bin','base_seed.rgb','base_seed.alpha')){throw 'Not an owned buffer'}
  $walk=$item
  while($walk){if($walk.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse point refused'};$walk=if($walk.PSIsContainer){$walk.Parent}else{$walk.Directory}}
  if($item.Length -ne $entry.bytes -or (Get-LiverySha256 $path) -ne $entry.sha256){throw 'Buffer changed'}
  Remove-Item -LiteralPath $path -ErrorAction Stop
}
