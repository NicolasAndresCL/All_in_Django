<#
.SYNOPSIS
    Apagado / reinicio programado del PC. Equivalente por consola de la vista
    "Apagado" de la UI (nicegui_ui/apagado.py); ambos usan shutdown.exe, asi que
    se cancelan entre si.

.PARAMETER Minutos
    Retardo en minutos. Excluyente con -Hora.

.PARAMETER Hora
    Hora objetivo "HH:MM". Si ya paso hoy, se entiende que es la de manana.

.PARAMETER Accion
    apagar (por defecto) o reiniciar.

.PARAMETER Forzar
    Cierra las aplicaciones sin esperar a que guarden (/f).

.PARAMETER Cancelar
    Aborta el apagado programado (shutdown /a).

.EXAMPLE
    .\scripts\apagar.ps1 -Minutos 45
.EXAMPLE
    .\scripts\apagar.ps1 -Hora 23:30 -Accion reiniciar
.EXAMPLE
    .\scripts\apagar.ps1 -Cancelar
#>
[CmdletBinding(DefaultParameterSetName = 'Minutos')]
param(
    [Parameter(ParameterSetName = 'Minutos')]
    [ValidateRange(0, 10080)]
    [int]$Minutos = 45,

    [Parameter(ParameterSetName = 'Hora', Mandatory = $true)]
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')]
    [string]$Hora,

    [Parameter(ParameterSetName = 'Minutos')]
    [Parameter(ParameterSetName = 'Hora')]
    [ValidateSet('apagar', 'reiniciar')]
    [string]$Accion = 'apagar',

    [Parameter(ParameterSetName = 'Minutos')]
    [Parameter(ParameterSetName = 'Hora')]
    [switch]$Forzar,

    [Parameter(ParameterSetName = 'Cancelar', Mandatory = $true)]
    [switch]$Cancelar
)

$ErrorActionPreference = 'Stop'

if ($Cancelar) {
    shutdown /a
    if ($LASTEXITCODE -eq 0) { "Apagado cancelado." } else { "No habia nada programado." }
    return
}

# Un unico camino de calculo: todo se reduce a segundos de retardo.
if ($PSCmdlet.ParameterSetName -eq 'Hora') {
    $ahora = Get-Date
    $objetivo = [datetime]::ParseExact($Hora, 'HH:mm', $null)
    $objetivo = $ahora.Date.AddHours($objetivo.Hour).AddMinutes($objetivo.Minute)
    if ($objetivo -le $ahora) { $objetivo = $objetivo.AddDays(1) }
    $segundos = [int]($objetivo - $ahora).TotalSeconds
} else {
    $segundos = $Minutos * 60
    $objetivo = (Get-Date).AddSeconds($segundos)
}

$flag = if ($Accion -eq 'reiniciar') { '/r' } else { '/s' }
$args = @($flag, '/t', "$segundos")
if ($Forzar) { $args += '/f' }

shutdown @args
if ($LASTEXITCODE -ne 0) { throw "shutdown.exe devolvio $LASTEXITCODE" }

"{0} programado para las {1} (en {2} min). Cancelar con: .\scripts\apagar.ps1 -Cancelar" -f `
    $Accion, $objetivo.ToString('HH:mm:ss'), [math]::Round($segundos / 60, 1)
