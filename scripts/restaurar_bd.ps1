<#
.SYNOPSIS
    Restaura un dump en la base de All in Django que corre en Docker. DESTRUCTIVO.

.DESCRIPTION
    Reemplaza el contenido de la base del contenedor 'all_in_django-db' con el de un dump
    en formato custom (-Fc) generado por scripts\respaldar_bd.ps1 o por pg_dump.

    Antes de tocar nada saca un respaldo de seguridad de lo que hay AHORA, para que un
    "restaure el dump equivocado" siga teniendo vuelta atras.

    El dump se copia al contenedor con `docker cp` y se restaura ahi dentro, nunca por el
    pipe de PowerShell: la tuberia de PS convierte la salida a texto y corrompe un binario.

.PARAMETER Archivo
    Ruta del dump. Si se omite, usa el mas reciente de fixtures\.

.PARAMETER Force
    Salta la confirmacion interactiva. Para uso en pipelines.

.EXAMPLE
    .\scripts\restaurar_bd.ps1
    .\scripts\restaurar_bd.ps1 -Archivo fixtures\all_in_django_20260830.dump -Force
#>
[CmdletBinding()]
param(
    [string]$Archivo,
    [string]$Contenedor = 'all_in_django-db',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot

if (-not $Archivo) {
    $ultimo = Get-ChildItem (Join-Path $raiz 'fixtures') -Filter '*.dump' -ErrorAction SilentlyContinue |
              Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $ultimo) { throw "No hay ningun .dump en fixtures\. Indica uno con -Archivo." }
    $Archivo = $ultimo.FullName
}
if (-not (Test-Path $Archivo)) { throw "No existe el archivo '$Archivo'." }
$Archivo = (Resolve-Path $Archivo).Path

$estado = docker inspect -f '{{.State.Status}}' $Contenedor 2>$null
if ($LASTEXITCODE -ne 0) { throw "No existe el contenedor '$Contenedor'." }
if ($estado -ne 'running') { throw "El contenedor '$Contenedor' esta '$estado', no 'running'." }

$usuario = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { 'all_in_django' }
$base    = if ($env:POSTGRES_DB)   { $env:POSTGRES_DB }   else { 'all_in_django' }

$sql = @"
select 'clases', count(*) from calendario_clase
union all select 'turnos personales', count(*) from calendario_turnopersonal
union all select 'turnos equipo', count(*) from liveops_turnoequipo
union all select 'tareas', count(*) from tareas_registro
union all select 'notas', count(*) from notas_nota;
"@

# Censo de lo que se va a REEMPLAZAR: que quede en el log a que se le paso por encima.
Write-Host "`nBase actual ('$base' en '$Contenedor'):"
docker exec $Contenedor psql -U $usuario -d $base -tAF' : ' -c $sql

Write-Host "`nSe va a RESTAURAR: $(Split-Path $Archivo -Leaf)"
Write-Host "Esto REEMPLAZA los datos de arriba." -ForegroundColor Yellow

if (-not $Force) {
    $r = Read-Host "Escribe 'restaurar' para continuar"
    if ($r -ne 'restaurar') { Write-Host "Cancelado."; return }
}

# Red de seguridad: respaldar lo actual antes de pisarlo.
Write-Host "`nRespaldo de seguridad previo..."
& (Join-Path $PSScriptRoot 'respaldar_bd.ps1') -Contenedor $Contenedor

Write-Host "`nRestaurando..."
$dentro = '/tmp/restaurar.dump'
docker cp $Archivo "${Contenedor}:${dentro}"
if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar el dump al contenedor." }

# --clean --if-exists: borra los objetos previos sin fallar si no existen (base vacia).
docker exec $Contenedor pg_restore -U $usuario -d $base --no-owner --clean --if-exists --exit-on-error $dentro
$codigo = $LASTEXITCODE
docker exec $Contenedor rm -f $dentro | Out-Null
if ($codigo -ne 0) { throw "pg_restore fallo. La base puede haber quedado a medias: restaura el respaldo de seguridad que se acaba de crear." }

Write-Host "`nBase restaurada:"
docker exec $Contenedor psql -U $usuario -d $base -tAF' : ' -c $sql
Write-Host "`nOK. Un dump -Fc trae los SEQUENCE SET, asi que las secuencias ya quedan al dia." -ForegroundColor Green
