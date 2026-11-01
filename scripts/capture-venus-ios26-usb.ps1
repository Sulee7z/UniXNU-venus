param(
  [string]$Image = "G:\UniXNU-Port\artifacts\venus-ios26\boot-venus-ios26-v2.img",
  [string]$LogDir = "G:\UniXNU-Port\logs",
  [int]$Seconds = 150
)

$ErrorActionPreference = "Continue"
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$eventLog = Join-Path $LogDir "venus-ios26-v2-usb-events-$stamp.jsonl"
$serialLog = Join-Path $LogDir "venus-ios26-v2-usb-serial-$stamp.log"
$bootLog = Join-Path $LogDir "venus-ios26-v2-fastboot-$stamp.log"

$fastboot = "G:\UniXNU-Port\tools\platform-tools\fastboot.exe"

function Write-Event([string]$kind, [hashtable]$data) {
  $row = [ordered]@{
    t = (Get-Date).ToUniversalTime().ToString("o")
    kind = $kind
  }
  foreach ($k in $data.Keys) { $row[$k] = $data[$k] }
  ($row | ConvertTo-Json -Compress) | Add-Content -LiteralPath $eventLog -Encoding utf8
}

Write-Event "start" @{ image = $Image; image_sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $Image).Hash.ToLower(); seconds = $Seconds }

# Verify the device is visible in fastboot before doing anything.
$devices = & $fastboot devices 2>&1 | Out-String
Write-Event "fastboot_devices" @{ output = $devices.Trim() }
if ($devices -notmatch '55870427') {
  Write-Event "abort" @{ reason = "serial 55870427 not in fastboot" }
  Write-Output "ABORT: device not in fastboot"
  exit 2
}

# Start the boot in the background so polling begins immediately.
$boot = Start-Process -FilePath $fastboot -ArgumentList @("-s","55870427","boot",$Image) `
  -RedirectStandardOutput $bootLog -RedirectStandardError "$bootLog.err" -PassThru -NoNewWindow
Write-Event "boot_started" @{ pid = $boot.Id; output_log = $bootLog }

$seen = @{}
$serial = $null
$deadline = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $deadline) {
  # Track every candidate USB identity so appearance/disappearance is timestamped.
  $devs = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue |
    Where-Object { $_.InstanceId -match 'VID_0525|VID_18D1|VID_2C7C|VID_2717|VID_05C6' }
  $current = @{}
  foreach ($d in $devs) {
    $key = "$($d.Class)|$($d.FriendlyName)|$($d.InstanceId)"
    $current[$key] = $true
    if (-not $seen.ContainsKey($key)) {
      $seen[$key] = $true
      Write-Event "device_appeared" @{ class = $d.Class; name = $d.FriendlyName; instance = $d.InstanceId; status = "$($d.Status)" }
    }
  }
  # Snapshot the key list: the dictionary is mutated inside the loop.
  $known = @($seen.Keys)
  foreach ($key in $known) {
    if ($key.StartsWith("gone|")) { continue }
    if (-not $current.ContainsKey($key)) {
      $seen["gone|$key"] = $true
      Write-Event "device_removed" @{ previous = $key }
    }
  }

  if (-not $serial) {
    $port = Get-CimInstance Win32_SerialPort -ErrorAction SilentlyContinue |
      Where-Object { $_.DeviceID -ne 'COM1' } | Select-Object -First 1
    if ($port) {
      $serial = $port.DeviceID
      Write-Event "serial_port_found" @{ port = $serial; description = $port.Description; pnp = $port.PNPDeviceID }
      try {
        $sp = New-Object System.IO.Ports.SerialPort $serial, 115200, 'None', 8, 'One'
        $sp.ReadTimeout = 500
        $sp.Open()
        Write-Event "serial_opened" @{ port = $serial }
        $buffer = New-Object byte[] 4096
        while ((Get-Date) -lt $deadline -and $sp.IsOpen) {
          try {
            $n = $sp.Read($buffer, 0, $buffer.Length)
            if ($n -gt 0) {
              $text = [Text.Encoding]::ASCII.GetString($buffer, 0, $n)
              [IO.File]::AppendAllText($serialLog, $text)
            }
          } catch [System.TimeoutException] { }
          catch { Write-Event "serial_error" @{ message = "$_" }; break }
        }
        if ($sp.IsOpen) { $sp.Close() }
        Write-Event "serial_closed" @{ port = $serial }
      } catch {
        Write-Event "serial_open_failed" @{ port = $serial; message = "$_" }
        $serial = $null
      }
    }
  }
  Start-Sleep -Milliseconds 700
}

$boot.Refresh()
Write-Event "boot_process" @{ exited = $boot.HasExited; exit_code = $(if ($boot.HasExited) { $boot.ExitCode } else { $null }) }
if (-not $boot.HasExited) { try { $boot.Kill() } catch { } }

$final = & $fastboot devices 2>&1 | Out-String
Write-Event "fastboot_devices_after" @{ output = $final.Trim() }
$adb = "G:\UniXNU-Port\tools\platform-tools\adb.exe"
$adbOut = & $adb devices 2>&1 | Out-String
Write-Event "adb_devices_after" @{ output = $adbOut.Trim() }

Write-Output "events=$eventLog"
Write-Output "serial=$serialLog"
Write-Output "boot=$bootLog"
