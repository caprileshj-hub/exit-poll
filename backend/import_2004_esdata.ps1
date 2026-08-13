param(
    [string]$Out = "resultados_rr2004.csv",
    [int[]]$CenterOld = @(),
    [string]$OldPrefix = "",
    [int]$OldMin = 0,
    [int]$OldMax = 0,
    [string]$StateCode = "",
    [string]$MunicipioCode = "",
    [int]$Limit = 0,
    [double]$Sleep = 10,
    [int]$PauseEvery = 50,
    [int]$PauseSeconds = 60,
    [switch]$Append,
    [switch]$SkipExisting,
    [int]$Retries = 4,
    [int]$RetrySleep = 15
)

$ErrorActionPreference = "Stop"

function Clean-Text([string]$Value) {
    if ($null -eq $Value) { return "" }
    $v = [System.Net.WebUtility]::HtmlDecode(($Value -replace '<[^>]+>', ' '))
    return (($v -replace '\s+', ' ').Trim())
}

function Get-RowInt([string]$Block, [string]$Label) {
    $m = [regex]::Match($Block, "$Label</th>\s*<td[^>]*>([0-9.,]+)</td>", "Singleline,IgnoreCase")
    if (-not $m.Success) { return 0 }
    $raw = $m.Groups[1].Value.Replace(".", "").Replace(",", ".")
    return [int][double]$raw
}

function Parse-CenterPage([string]$Html, [string]$SourceUrl) {
    if ($Html -notmatch 'Revocatorio Presidencial agosto 2004') { return $null }

    $old = [regex]::Match($Html, 'C[oó]digo Viejo CNE:</strong>\s*([0-9]+)', "IgnoreCase")
    $new = [regex]::Match($Html, 'C[oó]digo Nuevo CNE:</strong>\s*([0-9]+)', "IgnoreCase")
    if (-not $old.Success) {
        $old = [regex]::Match($Html, 'C.{0,4}digo Viejo CNE:</strong>\s*([0-9]+)', "IgnoreCase")
    }
    if (-not $new.Success) {
        $new = [regex]::Match($Html, 'C.{0,4}digo Nuevo CNE:</strong>\s*([0-9]+)', "IgnoreCase")
    }
    if (-not $old.Success -or -not $new.Success) { return $null }

    $title = [regex]::Match($Html, '<span class="currentpage">(.*?)</span>', "Singleline")
    $name = if ($title.Success) { Clean-Text $title.Groups[1].Value } else { "" }

    $blockMatch = [regex]::Match(
        $Html,
        'Refer.*?Revocatorio Presidencial agosto 2004</h2>(.*?)</table>',
        "Singleline,IgnoreCase"
    )
    if (-not $blockMatch.Success) { return $null }
    $block = $blockMatch.Groups[1].Value

    $si = Get-RowInt $block "Total Votos SI"
    $no = Get-RowInt $block "Total Votos NO"
    $nulos = Get-RowInt $block "Total Votos Nulos"
    $total = Get-RowInt $block "Total Votos"
    if ($total -le 0) { $total = $si + $no + $nulos }
    $validos = $si + $no
    if ($validos -le 0) { return $null }

    $rep = 0
    $repMatch = [regex]::Match(
        $Html,
        '<td>2004-07-01</td>\s*<td>Referendo Revocatorio</td>\s*<td>([0-9]+)</td>\s*<td>([0-9]*)</td>\s*<td>([0-9]+)</td>',
        "Singleline"
    )
    if ($repMatch.Success) { $rep = [int]$repMatch.Groups[3].Value }

    $tipo = ""
    $tipoMatch = [regex]::Match($block, 'Tipo de Centro</th>\s*<td colspan="2">([^<]+)</td>', "Singleline,IgnoreCase")
    if ($tipoMatch.Success) { $tipo = Clean-Text $tipoMatch.Groups[1].Value }

    [PSCustomObject]@{
        codigo_centro  = $new.Groups[1].Value.PadLeft(9, "0")
        codigo_cne_nuevo = $new.Groups[1].Value.PadLeft(9, "0")
        codigo_viejo   = $old.Groups[1].Value
        codigo_cne_viejo = $old.Groups[1].Value
        nombre_centro  = $name
        rep_2004       = $rep
        votos_validos  = $validos
        votos_gobierno = $no
        votos_oposicion = $si
        votos_otros    = 0
        votos_nulos    = $nulos
        total_votos    = $total
        pct_gobierno   = [Math]::Round(100 * $no / $validos, 2)
        pct_oposicion  = [Math]::Round(100 * $si / $validos, 2)
        participacion  = if ($rep -gt 0) { [Math]::Round(100 * $total / $rep, 2) } else { 0 }
        tipo_centro    = $tipo
        fuente_url     = $SourceUrl
    }
}

function Invoke-WithRetry([string]$Uri, [int]$TimeoutSec) {
    $headers = @{
        "User-Agent" = "exit-poll-historical-import/1.0"
        "Accept-Encoding" = "identity"
    }
    for ($attempt = 1; $attempt -le $Retries; $attempt++) {
        try {
            return Invoke-RestMethod -Uri $Uri -TimeoutSec $TimeoutSec -Headers $headers
        } catch {
            if ($attempt -ge $Retries) { throw }
            Write-Warning "Intento $attempt/$Retries fallo para $Uri`: $($_.Exception.Message)"
            Start-Sleep -Seconds ($RetrySleep * $attempt)
        }
    }
}

function Get-CdxCaptures([string]$Pattern) {
    $escaped = [uri]::EscapeDataString($Pattern)
    $cdxUrl = "https://web.archive.org/cdx/search/cdx?url=$escaped&output=json&fl=timestamp,original,statuscode,mimetype,length&filter=statuscode:200&collapse=urlkey&limit=30000"
    $cdx = Invoke-WithRetry $cdxUrl 90
    if ($null -eq $cdx -or $cdx.Count -le 1) {
        return @()
    }

    $out = @()
    foreach ($row in $cdx[1..($cdx.Count - 1)]) {
        $original = [string]$row[1]
        $m = [regex]::Match($original, '^https?://(?:www\.)?esdata\.info(?::80)?/centro/(\d+)/?$', "IgnoreCase")
        if ($m.Success) {
            $out += [PSCustomObject]@{
                old = [int]$m.Groups[1].Value
                timestamp = [string]$row[0]
                original = $original
            }
        }
    }
    return $out
}

$captures = @()
if ($CenterOld.Count -gt 0) {
    foreach ($oldCode in $CenterOld) {
        $captures += Get-CdxCaptures "esdata.info/centro/$oldCode"
        $captures += Get-CdxCaptures "www.esdata.info/centro/$oldCode"
    }
} elseif ($OldPrefix.Trim() -ne "") {
    $captures = Get-CdxCaptures "esdata.info/centro/$OldPrefix*"
} else {
    $captures = Get-CdxCaptures "esdata.info/centro/*"
}
$captures = @($captures | Sort-Object old -Unique)
$captures = @($captures | Where-Object {
    ($OldMin -le 0 -or $_.old -ge $OldMin) -and
    ($OldMax -le 0 -or $_.old -le $OldMax)
})
if ($captures.Count -eq 0) {
    throw "Wayback no devolvio capturas de /centro/*. No se escribio $Out."
}
if ($Limit -gt 0) {
    $captures = @($captures | Select-Object -First $Limit)
}

$rows = New-Object System.Collections.Generic.List[object]
$existingByCode = @{}
if (($Append -or $SkipExisting) -and (Test-Path $Out)) {
    foreach ($row in (Import-Csv $Out)) {
        $existingByCode[[string]$row.codigo_centro] = $row
        if ($Append) { $rows.Add($row) }
    }
}

$i = 0
$errors = 0
foreach ($capture in $captures) {
    $i += 1
    $url = "https://web.archive.org/web/$($capture.timestamp)id_/$($capture.original)"
    try {
        try {
            $html = Invoke-WithRetry $url 45
        } catch {
            $fallbackUrl = "https://web.archive.org/web/$($capture.timestamp)/$($capture.original)"
            Write-Warning "$($capture.original): recurso crudo fallo; probando captura con wrapper"
            $html = Invoke-WithRetry $fallbackUrl 45
            $url = $fallbackUrl
        }
        $parsed = Parse-CenterPage $html $url
        if ($null -ne $parsed) {
            if ($StateCode.Trim() -ne "" -and -not $parsed.codigo_centro.StartsWith($StateCode.PadLeft(2, "0"))) {
                continue
            }
            if ($MunicipioCode.Trim() -ne "" -and -not $parsed.codigo_centro.StartsWith($MunicipioCode.PadLeft(4, "0"))) {
                continue
            }
            if ($SkipExisting -and $existingByCode.ContainsKey([string]$parsed.codigo_centro)) {
                continue
            }
            $existingByCode[[string]$parsed.codigo_centro] = $parsed
            $rows.Add($parsed)
        }
    } catch {
        $errors += 1
        Write-Warning "$($capture.original): $($_.Exception.Message)"
    }
    if (($i % 250) -eq 0) {
        Write-Host "[$i/$($captures.Count)] centros leidos, $($rows.Count) con RR2004"
    }
    if ($Sleep -gt 0) {
        Start-Sleep -Seconds $Sleep
    }
    if ($PauseEvery -gt 0 -and ($i % $PauseEvery) -eq 0 -and $PauseSeconds -gt 0) {
        Write-Host "Pausa de $PauseSeconds segundos para no forzar Wayback..."
        Start-Sleep -Seconds $PauseSeconds
    }
}

if ($rows.Count -eq 0) {
    throw "No se parseo ningun centro RR2004. No se escribio $Out."
}
$rows | Sort-Object codigo_centro -Unique | Export-Csv -Path $Out -NoTypeInformation -Encoding UTF8
Write-Host "Import 2004 Esdata: capturas=$($captures.Count) filas=$($rows.Count) errores=$errors out=$Out"
