<#
.SYNOPSIS
    Generates Azure Cosmos DB authorization headers for REST API calls.

.DESCRIPTION
    This script generates the authorization header required for Azure Cosmos DB REST API.
    It uses HMAC-SHA256 signature with the master key following Microsoft's documentation:
    https://learn.microsoft.com/en-us/rest/api/cosmos-db/access-control-on-cosmosdb-resources

.PARAMETER Verb
    The HTTP verb for the request (GET, POST, PUT, DELETE, PATCH). Case-insensitive.

.PARAMETER ResourceType
    The resource type (dbs, colls, docs, sprocs, udfs, triggers, users, permissions).

.PARAMETER ResourceLink
    The resource link path. Examples:
    - For database operations: "dbs/MyDatabase"
    - For container operations: "dbs/MyDatabase/colls/MyContainer"
    - For document operations: "dbs/MyDatabase/colls/MyContainer/docs/MyDoc"
    - For list operations at parent level (e.g., list dbs): "" (empty string)

.PARAMETER Date
    Optional. The date string in RFC1123 format. Defaults to current UTC time.

.EXAMPLE
    # List all databases
    .\Generate-CosmosAuth.ps1 -Verb GET -ResourceType dbs -ResourceLink ""

.EXAMPLE
    # Get a specific database
    .\Generate-CosmosAuth.ps1 -Verb GET -ResourceType dbs -ResourceLink "dbs/MyDatabase"

.EXAMPLE
    # List documents in a container
    .\Generate-CosmosAuth.ps1 -Verb GET -ResourceType docs -ResourceLink "dbs/MyDatabase/colls/MyContainer"

.EXAMPLE
    # Create/Query documents (POST to container)
    .\Generate-CosmosAuth.ps1 -Verb POST -ResourceType docs -ResourceLink "dbs/MyDatabase/colls/MyContainer"

.NOTES
    The output can be used in the Authorization header for Cosmos DB REST API calls.
    Copy the Authorization value and x-ms-date value to use in your .http file.
#>

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("GET", "POST", "PUT", "DELETE", "PATCH", IgnoreCase = $true)]
    [string]$Verb,

    [Parameter(Mandatory = $true)]
    [ValidateSet("dbs", "colls", "docs", "sprocs", "udfs", "triggers", "users", "permissions", IgnoreCase = $true)]
    [string]$ResourceType,

    [Parameter(Mandatory = $false)]
    [string]$ResourceLink = "",

    [Parameter(Mandatory = $false)]
    [string]$Date
)

# Load environment variables from .env file
function Load-EnvFile {
    param([string]$EnvFilePath)
    
    if (Test-Path $EnvFilePath) {
        Get-Content $EnvFilePath | ForEach-Object {
            if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                # Remove quotes if present
                $value = $value -replace '^["'']|["'']$', ''
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
    }
    else {
        Write-Error "Environment file not found: $EnvFilePath"
        exit 1
    }
}

# Generate the authorization token
function Get-CosmosDBAuthorizationToken {
    param(
        [string]$Verb,
        [string]$ResourceType,
        [string]$ResourceLink,
        [string]$Date,
        [string]$MasterKey
    )

    # Normalize values
    $verb = $Verb.ToLowerInvariant()
    $resourceType = $ResourceType.ToLowerInvariant()
    
    # Build the payload string for hashing
    # Format: "{verb}\n{resourceType}\n{resourceLink}\n{date}\n\n"
    $payload = "$verb`n$resourceType`n$ResourceLink`n$($Date.ToLowerInvariant())`n`n"

    Write-Verbose "Payload for signature:`n$payload"

    # Decode the master key from Base64
    $keyBytes = [System.Convert]::FromBase64String($MasterKey)

    # Create HMAC-SHA256 hash
    $hmacSha256 = New-Object System.Security.Cryptography.HMACSHA256
    $hmacSha256.Key = $keyBytes

    # Compute hash of the payload
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
    $hashBytes = $hmacSha256.ComputeHash($payloadBytes)

    # Convert hash to Base64
    $signature = [System.Convert]::ToBase64String($hashBytes)

    # Build the authorization token
    $keyType = "master"
    $tokenVersion = "1.0"
    $authToken = "type=$keyType&ver=$tokenVersion&sig=$signature"

    # URL encode the token
    $encodedToken = [System.Web.HttpUtility]::UrlEncode($authToken)

    return $encodedToken
}

# Main script execution
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$envFilePath = Join-Path $scriptDir ".env"

# Load .env file
Load-EnvFile -EnvFilePath $envFilePath

# Get the master key from environment
$masterKey = [Environment]::GetEnvironmentVariable("COSMOS_DB_KEY", "Process")
if ([string]::IsNullOrEmpty($masterKey)) {
    Write-Error "COSMOS_DB_KEY not found in .env file"
    exit 1
}

# Generate date if not provided
if ([string]::IsNullOrEmpty($Date)) {
    $Date = [DateTime]::UtcNow.ToString("r")  # RFC1123 format
}

# Add System.Web assembly for URL encoding
Add-Type -AssemblyName System.Web

# Generate the authorization token
$authToken = Get-CosmosDBAuthorizationToken `
    -Verb $Verb `
    -ResourceType $ResourceType `
    -ResourceLink $ResourceLink `
    -Date $Date `
    -MasterKey $masterKey

# Output the results
Write-Host ""
Write-Host "=== Cosmos DB Authorization Header ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "HTTP Verb:      $Verb" -ForegroundColor Yellow
Write-Host "Resource Type:  $ResourceType" -ForegroundColor Yellow
Write-Host "Resource Link:  $(if($ResourceLink) { $ResourceLink } else { '(empty)' })" -ForegroundColor Yellow
Write-Host ""
Write-Host "x-ms-date:" -ForegroundColor Green
Write-Host $Date
Write-Host ""
Write-Host "Authorization:" -ForegroundColor Green
Write-Host $authToken
Write-Host ""
Write-Host "=== Copy these values to your .http file ===" -ForegroundColor Cyan
Write-Host ""

# Also output in a format easy to copy for .http files
Write-Host "# Headers for your .http file:" -ForegroundColor DarkGray
Write-Host "x-ms-date: $Date" -ForegroundColor White
Write-Host "Authorization: $authToken" -ForegroundColor White
Write-Host ""

# Return object for pipeline use
return @{
    Date = $Date
    Authorization = $authToken
    Verb = $Verb
    ResourceType = $ResourceType
    ResourceLink = $ResourceLink
}
