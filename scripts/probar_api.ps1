<#
.SYNOPSIS
    Ejercita la API por HTTP con la coleccion Postman, contra un stack EFIMERO.

.DESCRIPTION
    La suite de pytest usa `force_authenticate`: nunca atraviesa gunicorn, el middleware,
    la autenticacion por token real ni el rate limiting. Esto si.

    Levanta docker-compose.test.yml (base vacia, puertos altos, sin volumen), crea un
    usuario de pruebas, corre postman\all_in_django.postman_collection.json con Newman y
    derriba el stack pase lo que pase. Los datos reales NO se tocan en ningun momento: el
    stack de pruebas ni siquiera monta el volumen `all_in_django_pgdata`.

.PARAMETER Conservar
    No derriba el stack al terminar. Util para inspeccionar la base tras un fallo
    (psql en localhost:5434). Recuerda bajarlo despues:
        docker compose -f docker-compose.test.yml --env-file <el .env que diga la salida> down -v

.PARAMETER Carpeta
    Corre solo una carpeta de la coleccion (nombre exacto), p. ej. '04 - Registro de tareas'.

.PARAMETER Informe
    Ruta donde dejar el informe JSON de Newman (util para revisar fallos con calma).

.EXAMPLE
    .\scripts\probar_api.ps1
    .\scripts\probar_api.ps1 -Carpeta '04 - Registro de tareas'
    .\scripts\probar_api.ps1 -Conservar -Informe .\newman.json
#>
[CmdletBinding()]
param(
    [switch]$Conservar,
    [string]$Carpeta,
    [string]$Informe
)

# OJO: 'Continue', no 'Stop'. En PowerShell 5.1 cualquier linea que un ejecutable nativo
# escriba en stderr (docker compose es locuaz ahi) se convierte en ErrorRecord y con 'Stop'
# abortaria el script aunque el comando haya devuelto 0. El control va por $LASTEXITCODE.
$ErrorActionPreference = 'Continue'

$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz

$puerto = if ($env:TEST_API_PORT) { $env:TEST_API_PORT } else { '8010' }
$puertoDb = if ($env:TEST_DB_PORT) { $env:TEST_DB_PORT } else { '5434' }
$usuario = 'postman'
$clave = 'postman-' + [guid]::NewGuid().ToString('N').Substring(0, 16)

# Credenciales efimeras en un archivo FUERA del repo. Se pasa con --env-file para que compose
# NO lea el `.env` de Django de la raiz: ese es el de la base real y ademas su SECRET_KEY
# lleva '$', que dispara warnings de interpolacion (misma razon por la que docker-compose.yml
# se usa siempre con --env-file).
$envTest = Join-Path ([System.IO.Path]::GetTempPath()) "all_in_django_test_$PID.env"
$secreto = -join ((1..64) | ForEach-Object { [char](Get-Random -Minimum 65 -Maximum 122) })
@(
    "SECRET_KEY=$secreto"
    "POSTGRES_PASSWORD=$([guid]::NewGuid().ToString('N'))"
    "TEST_API_PORT=$puerto"
    "TEST_DB_PORT=$puertoDb"
) | Set-Content -Path $envTest -Encoding utf8

$compose = @('compose', '-f', 'docker-compose.test.yml', '--env-file', $envTest)
$codigoNewman = 1

function Fallar($mensaje) {
    Write-Host "`n  FALLO  $mensaje" -ForegroundColor Red
}

Write-Host "`nPruebas HTTP de la API (stack efimero; tus datos NO se tocan)`n"

try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fallar 'docker no esta en el PATH.'; exit 1 }
    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) { Fallar 'npx no esta en el PATH (Newman necesita Node).'; exit 1 }

    Write-Host '  ... construyendo la imagen y levantando el stack'
    & docker @compose up -d --build
    if ($LASTEXITCODE -ne 0) { Fallar 'no se pudo levantar el stack de pruebas.'; exit 1 }

    # Mismo bucle que verificar.ps1: sale en cuanto los dos estan sanos y aborta en cuanto
    # uno queda unhealthy, sin agotar el timeout.
    Write-Host '  ... esperando a que la API responda'
    $listo = $false
    foreach ($i in 1..60) {
        $estados = @('all_in_django-test-db', 'all_in_django-test') |
                   ForEach-Object { docker inspect -f '{{.State.Health.Status}}' $_ 2>$null }
        if (($estados | Where-Object { $_ -eq 'healthy' }).Count -eq 2) { $listo = $true; break }
        if ($estados -contains 'unhealthy') { break }
        Start-Sleep 5
    }
    if (-not $listo) {
        & docker @compose logs --tail=60
        Fallar 'el stack de pruebas no llego a estar sano.'
        exit 1
    }

    # Usuario de pruebas. La coleccion pide su token por POST /api/token/, asi que no hay que
    # parsear la salida de drf_create_token y de paso se ejercita el endpoint de login.
    Write-Host '  ... creando el usuario de pruebas'
    & docker @compose exec -T `
        -e DJANGO_SUPERUSER_USERNAME=$usuario `
        -e DJANGO_SUPERUSER_EMAIL="$usuario@example.invalid" `
        -e DJANGO_SUPERUSER_PASSWORD=$clave `
        api python manage.py createsuperuser --noinput
    if ($LASTEXITCODE -ne 0) { Fallar 'no se pudo crear el usuario de pruebas.'; exit 1 }

    # --working-dir postman: es donde la peticion de importar busca fixtures/turnos_ejemplo.csv.
    $argumentos = @(
        '--yes', 'newman', 'run', 'postman/all_in_django.postman_collection.json',
        '-e', 'postman/local.postman_environment.json',
        '--working-dir', 'postman',
        '--env-var', "base_url=http://localhost:$puerto",
        '--env-var', "username=$usuario",
        '--env-var', "password=$clave",
        '--color', 'on'
    )
    if ($Carpeta) { $argumentos += @('--folder', $Carpeta) }
    if ($Informe) { $argumentos += @('--reporters', 'cli,json', '--reporter-json-export', $Informe) }

    Write-Host "  ... corriendo la coleccion contra http://localhost:$puerto`n"
    & npx @argumentos
    $codigoNewman = $LASTEXITCODE
}
finally {
    if ($Conservar) {
        Write-Host "`nStack conservado (-Conservar). API en http://localhost:$puerto, base en el $puertoDb."
        Write-Host "Para bajarlo:  docker compose -f docker-compose.test.yml --env-file $envTest down -v"
    } else {
        Write-Host "`n  ... derribando el stack de pruebas"
        & docker @compose down -v | Out-Null
        Remove-Item $envTest -ErrorAction SilentlyContinue
    }
}

if ($codigoNewman -ne 0) {
    Write-Host "`nLa coleccion FALLO. Revisa las aserciones en rojo de arriba." -ForegroundColor Red
    exit 1
}
Write-Host "`nAPI verificada por HTTP: la coleccion paso entera." -ForegroundColor Green
exit 0
