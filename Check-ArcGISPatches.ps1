<#
.SYNOPSIS
    ArcGIS Enterprise patch discovery via the ArcGIS Enterprise Administrator API.

.DESCRIPTION
    Authenticates against ArcGIS Enterprise, then calls the Enterprise Admin
    API's "installed" and "available" upgrade operations to report:
      - Currently installed patches/releases
      - Patches/releases available but NOT yet installed (patch discovery)

    Reference (Esri REST API docs):
      Installed: POST {root}/system/upgrades/installed
      Available: POST {root}/system/upgrades/available
      https://developers.arcgis.com/rest/enterprise-administration/enterprise/check-installed-updates/
      https://developers.arcgis.com/rest/enterprise-administration/enterprise/check-available-updates/

.PARAMETER PortalUrl
    Base URL of the Portal, e.g. https://gis.county.gov/portal

.PARAMETER AdminUrl
    Base URL of the Enterprise Admin API root, e.g. https://gis.county.gov/portal/portaladmin
    (or the Kubernetes Enterprise Admin API root for your deployment)

.PARAMETER Username / Password
    ArcGIS Enterprise administrator credentials. In production, pull these
    from a secret store / credential manager rather than plain text.

.PARAMETER OutputPath
    Folder to write the CSV report(s) to. Defaults to current directory.

.EXAMPLE
    ./Check-ArcGISPatches.ps1 -PortalUrl "https://gis.county.gov/portal" `
        -AdminUrl "https://gis.county.gov/portal/portaladmin" `
        -Username "admin_user" -Password "***" -OutputPath "C:\Reports"
#>

param(
    [Parameter(Mandatory = $true)][string]$PortalUrl,
    [Parameter(Mandatory = $true)][string]$AdminUrl,
    [Parameter(Mandatory = $true)][string]$Username,
    [Parameter(Mandatory = $true)][string]$Password,
    [string]$OutputPath = "."
)

function Get-ArcGISToken {
    param($PortalUrl, $Username, $Password)

    $tokenUrl = "$PortalUrl/sharing/rest/generateToken"
    $body = @{
        username = $Username
        password = $Password
        referer  = $PortalUrl
        f        = "json"
    }

    $response = Invoke-RestMethod -Uri $tokenUrl -Method Post -Body $body
    if (-not $response.token) {
        throw "Failed to generate token: $($response | ConvertTo-Json -Depth 5)"
    }
    return $response.token
}

function Get-InstalledUpdates {
    param($AdminUrl, $Token)

    $url = "$AdminUrl/system/upgrades/installed"
    $body = @{ f = "json"; token = $Token }
    $response = Invoke-RestMethod -Uri $url -Method Post -Body $body
    return $response.updates
}

function Get-AvailableUpdates {
    param($AdminUrl, $Token)

    $url = "$AdminUrl/system/upgrades/available"
    $body = @{ f = "json"; token = $Token }
    $response = Invoke-RestMethod -Uri $url -Method Post -Body $body
    return $response
}

# --- Main ---

Write-Host "Authenticating against $PortalUrl ..."
$token = Get-ArcGISToken -PortalUrl $PortalUrl -Username $Username -Password $Password
Write-Host "Token acquired."

Write-Host "Checking installed patches/releases ..."
$installed = Get-InstalledUpdates -AdminUrl $AdminUrl -Token $token

Write-Host "Checking for available (not-yet-installed) patches/releases ..."
$available = Get-AvailableUpdates -AdminUrl $AdminUrl -Token $token

$installedReportPath = Join-Path $OutputPath "installed_patches.csv"
$installed |
    Select-Object name, type, version, build, previousVersion, previousBuild, released, url |
    Export-Csv -Path $installedReportPath -NoTypeInformation

$pendingPatches = $available.patches + $available.releases
$pendingReportPath = Join-Path $OutputPath "pending_patches.csv"
$pendingPatches |
    Select-Object name, type, version, build, previousVersion, released, newLicensesRequired, url |
    Export-Csv -Path $pendingReportPath -NoTypeInformation

Write-Host ""
Write-Host "Installed patches/releases: $($installed.Count) -> $installedReportPath"
Write-Host "Pending (available, not installed): $($pendingPatches.Count) -> $pendingReportPath"

if ($pendingPatches.Count -gt 0) {
    Write-Warning "$($pendingPatches.Count) patch(es)/release(s) available but not installed. Review $pendingReportPath before the next maintenance window."
}
