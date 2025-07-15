#!/usr/bin/env powershell
<#
.SYNOPSIS
    Test Plex Token Validity
.DESCRIPTION
    Tests if a Plex token is valid and can connect to the Plex server.
    Provides detailed information about the token and connection status.
.PARAMETER PlexHost
    Plex server URL (default: http://127.0.0.1:32400)
.PARAMETER PlexToken
    Plex authentication token to test
.EXAMPLE
    .\test_plex_token.ps1
.EXAMPLE
    .\test_plex_token.ps1 -PlexHost "http://192.168.1.100:32400" -PlexToken "your-token-here"
#>

[CmdletBinding()]
param(
    [string]$PlexHost = "http://127.0.0.1:32400",
    [string]$PlexToken = ""
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Cyan = "Cyan"
$Gray = "Gray"
$Magenta = "Magenta"

function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Test-PlexConnection {
    param([string]$Host, [string]$Token)
    
    try {
        Write-Status "🔍 Testing basic connection to Plex server..." $Yellow
        
        # Test 1: Basic connection (no token)
        $identityResponse = Invoke-RestMethod -Uri "$Host/identity" -TimeoutSec 10 -ErrorAction Stop
        
        if ($identityResponse) {
            Write-Status "✅ Basic connection successful" $Green
            
            if ($identityResponse.MediaContainer) {
                Write-Status "   Server Name: $($identityResponse.MediaContainer.friendlyName)" $Gray
                Write-Status "   Version: $($identityResponse.MediaContainer.version)" $Gray
                Write-Status "   Platform: $($identityResponse.MediaContainer.platform)" $Gray
                Write-Status "   Machine ID: $($identityResponse.MediaContainer.machineIdentifier)" $Gray
            }
        }
        
        # Test 2: Token validation
        if ($Token) {
            Write-Status "`n🔐 Testing token authentication..." $Yellow
            
            $headers = @{ 'X-Plex-Token' = $Token }
            $accountResponse = Invoke-RestMethod -Uri "$Host/myplex/account" -Headers $headers -TimeoutSec 10 -ErrorAction Stop
            
            if ($accountResponse) {
                Write-Status "✅ Token authentication successful" $Green
                
                if ($accountResponse.MyPlex) {
                    Write-Status "   Account: $($accountResponse.MyPlex.username)" $Gray
                    Write-Status "   Email: $($accountResponse.MyPlex.email)" $Gray
                    Write-Status "   Subscription: $($accountResponse.MyPlex.subscription)" $Gray
                }
            }
            
            # Test 3: Library access
            Write-Status "`n📚 Testing library access..." $Yellow
            
            $libraryResponse = Invoke-RestMethod -Uri "$Host/library/sections" -Headers $headers -TimeoutSec 10 -ErrorAction Stop
            
            if ($libraryResponse -and $libraryResponse.MediaContainer -and $libraryResponse.MediaContainer.Directory) {
                Write-Status "✅ Library access successful" $Green
                Write-Status "   Found $($libraryResponse.MediaContainer.Directory.Count) libraries:" $Gray
                
                foreach ($library in $libraryResponse.MediaContainer.Directory) {
                    Write-Status "   - [$($library.key)] $($library.title) ($($library.type))" $Gray
                }
            }
            
            return $true
        } else {
            Write-Status "⚠️  No token provided - only basic connection tested" $Yellow
            return $false
        }
        
    } catch {
        Write-Status "❌ Connection failed: $_" $Red
        return $false
    }
}

function Get-PlexTokenInteractive {
    Write-Status "`n=============================================================================" $Yellow
    Write-Status "                      PLEX TOKEN RETRIEVAL GUIDE                           " $Yellow
    Write-Status "=============================================================================" $Yellow
    Write-Status ""
    Write-Status "EASY METHOD (Recommended):" $Green
    Write-Status "  1. Open Plex web interface: $PlexHost/web" $Cyan
    Write-Status "  2. Click on any movie or TV show" $Cyan
    Write-Status "  3. Click the 'View XML' button (or press 'i' for info)" $Cyan
    Write-Status "  4. Copy the 'X-Plex-Token' value from the URL" $Cyan
    Write-Status "     Example: ...?X-Plex-Token=ABC123XYZ789" $Gray
    Write-Status ""
    Write-Status "ALTERNATIVE METHOD:" $Yellow
    Write-Status "  1. Open Plex web interface: $PlexHost/web" $Cyan
    Write-Status "  2. Go to Settings -> General -> Network" $Cyan
    Write-Status "  3. Click 'Show Advanced' at the top" $Cyan
    Write-Status "  4. Copy the 'Plex Token' value" $Cyan
    Write-Status ""
    Write-Status "=============================================================================" $Yellow
    Write-Status ""
    
    do {
        $token = Read-Host "Enter your Plex token"
        
        if (-not $token) {
            Write-Status "Token is required. Please enter your Plex token." $Red
        } elseif ($token.Length -lt 10) {
            Write-Status "Token seems too short. Expected 20-30 characters, got $($token.Length)." $Red
            $token = $null
        } elseif ($token.Length -gt 50) {
            Write-Status "Token seems too long. Expected 20-30 characters, got $($token.Length)." $Red
            $token = $null
        } elseif ($token -notmatch '^[A-Za-z0-9_-]+$') {
            Write-Status "Token contains invalid characters. Should only contain letters, numbers, underscores, and hyphens." $Red
            $token = $null
        }
    } while (-not $token)
    
    return $token
}

# Main execution
Clear-Host
Write-Status "=============================================================================" $Cyan
Write-Status "                            PLEX TOKEN TESTER                              " $Cyan
Write-Status "=============================================================================" $Cyan
Write-Status ""

# Get Plex host
if (-not $PlexHost) {
    $PlexHost = Read-Host "Enter Plex server URL (default: http://127.0.0.1:32400)"
    if (-not $PlexHost) {
        $PlexHost = "http://127.0.0.1:32400"
    }
}

Write-Status "🖥️  Plex Server: $PlexHost" $Cyan

# Get Plex token
if (-not $PlexToken) {
    $PlexToken = Get-PlexTokenInteractive
}

Write-Status "🔑 Token Length: $($PlexToken.Length) characters" $Cyan
Write-Status "🔑 Token Preview: $($PlexToken.Substring(0, 8))..." $Cyan
Write-Status ""

# Test connection
$testResult = Test-PlexConnection -Host $PlexHost -Token $PlexToken

Write-Status ""
Write-Status "=============================================================================" $Cyan

if ($testResult) {
    Write-Status "🎉 ALL TESTS PASSED! Your Plex token is valid and working." $Green
    Write-Status ""
    Write-Status "You can now use this token in your Plex RAR Bridge configuration:" $Yellow
    Write-Status "  PlexHost: $PlexHost" $Gray
    Write-Status "  PlexToken: $PlexToken" $Gray
} else {
    Write-Status "❌ TESTS FAILED! Please check your token and try again." $Red
    Write-Status ""
    Write-Status "Common issues:" $Yellow
    Write-Status "  - Token copied incorrectly (missing characters)" $Gray
    Write-Status "  - Token expired (generate a new one)" $Gray
    Write-Status "  - Plex server not running or accessible" $Gray
    Write-Status "  - Network connectivity issues" $Gray
}

Write-Status ""
Write-Status "=============================================================================" $Cyan
Write-Status "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 