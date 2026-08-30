<#
.SYNOPSIS
    Respalda la base de All in Django que corre en Docker, a un dump fechado.

.DESCRIPTION
    Vuelca la base del contenedor 'all_in_django-db' con pg_dump en formato custom (-Fc),
    el mismo que entiende scripts\restaurar_bd.ps1. Los dumps van a fixtures\ (gitignored:
    contienen horarios, tareas y notas personales) y se rotan conservando los N ultimos.

    El formato custom NO es texto plano: trae los SEQUENCE SET, asi que al restaurar no hay
    que resetear secuencias a mano (a diferencia del camino dumpdata/loaddata de Django).

    El dump se genera DENTRO del contenedor y se trae con `docker cp`, nunca por el pipe de
    PowerShell: la tuberia de PS convierte la salida a texto y corrompe un binario -Fc.

.PARAMETER Conservar
    Cuantos dumps mantener en fixtures\. Los mas antiguos se borran. Por defecto 10.

.PARAMETER Contenedor
    Nombre del contenedor de Postgres. Por defecto 'all_in_django-db'.

.EXAMPLE
    .\scripts\respaldar_bd.ps1
    .\scripts\respaldar_bd.ps1 -Conservar 30
#>
[CmdletBinding()]
param(
    [int]$Conservar = 10,
    [string]$Contenedor = 'all_in_django-db'
)

$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$destino = Join-Path $raiz 'fixtures'

# El contenedor tiene que estar arriba: un respaldo que falla en silencio es peor que no
# tenerlo, porque genera confianza injustificada.
$estado = docker inspect -f '{{.State.Status}}' $Contenedor 2>$null
if ($LASTEXITCODE -ne 0) { throw "No existe el contenedor '$Contenedor'. Levanta el stack: docker compose --env-file .env.docker up -d" }
if ($estado -ne 'running') { throw "El contenedor '$Contenedor' esta '$estado', no 'running'." }

if (-not (Test-Path $destino)) { New-Item -ItemType Directory -Path $destino | Out-Null }

$usuario = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { 'all_in_django' }
$base    = if ($env:POSTGRES_DB)   { $env:POSTGRES_DB }   else { 'all_in_django' }
$nombre  = "all_in_django_{0}.dump" -f (Get-Date -Format 'yyyyMMdd_HHmmss')
$archivo = Join-Path $destino $nombre
$dentro  = "/tmp/$nombre"

Write-Host "Respaldando '$base' desde '$Contenedor'..."
docker exec $Contenedor pg_dump -U $usuario -d $base -Fc -f $dentro
if ($LASTEXITCODE -ne 0) { throw "pg_dump fallo dentro del contenedor." }

# Verificar que es legible ANTES de sacarlo y antes de rotar los anteriores: un dump que
# no se puede leer no es un respaldo, y eso hay que descubrirlo hoy, no el dia que urja.
docker exec $Contenedor pg_restore --list $dentro | Out-Null
if ($LASTEXITCODE -ne 0) {
    docker exec $Contenedor rm -f $dentro | Out-Null
    throw "El dump no pasa 'pg_restore --list': se descarta."
}

docker cp "${Contenedor}:${dentro}" $archivo
if ($LASTEXITCODE -ne 0) { throw "No se pudo copiar el dump al host." }
docker exec $Contenedor rm -f $dentro | Out-Null

$tam = (Get-Item $archivo).Length
if ($tam -lt 1024) { Remove-Item $archivo; throw "El dump salio de $tam bytes: sospechoso, se descarta." }
Write-Host ("OK  {0}  ({1:N0} KB)" -f $nombre, ($tam / 1KB)) -ForegroundColor Green

$viejos = Get-ChildItem $destino -Filter 'all_in_django_*.dump' |
          Sort-Object LastWriteTime -Descending | Select-Object -Skip $Conservar
foreach ($v in $viejos) {
    Remove-Item $v.FullName
    Write-Host "    rotado (borrado): $($v.Name)"
}
