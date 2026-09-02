<#
.SYNOPSIS
    Reproduce en local lo que verifica el CI, en el mismo orden. Correr ANTES de commitear.

.DESCRIPTION
    Un CI que se descubre en remoto ya llega tarde. Este script recorre los mismos jobs que
    .github\workflows\ci.yml (rapido -> lento) y resume que fallo, para no pushear en rojo.

    El job que MAS se olvida es 'hardening': corre con la configuracion de produccion
    (DEBUG=False + SECURE_HTTPS=True), asi que no aparece jamas en un pytest normal.

.PARAMETER Rapido
    Salta los pasos lentos: los dos con Docker (arranque del stack y pruebas HTTP de la
    API) y la verificacion visual en navegador. Util mientras se itera.

.EXAMPLE
    .\scripts\verificar.ps1
    .\scripts\verificar.ps1 -Rapido
#>
[CmdletBinding()]
param([switch]$Rapido)

$raiz = Split-Path -Parent $PSScriptRoot
Set-Location $raiz
$py = Join-Path $raiz 'env\Scripts\python.exe'
if (-not (Test-Path $py)) { $py = 'python' }

$fallos = @()
$log = Join-Path $env:TEMP 'verificar_all_in_django.log'

function Ejecutar {
    param([string]$Desc, [scriptblock]$Bloque)
    Write-Host "  ... $Desc" -NoNewline
    try {
        & $Bloque *> $log
        $ok = ($LASTEXITCODE -eq 0 -or $null -eq $LASTEXITCODE)
    } catch { $ok = $false }
    if ($ok) {
        Write-Host "`r  OK  $Desc                    " -ForegroundColor Green
    } else {
        Write-Host "`r  FALLO  $Desc                 " -ForegroundColor Red
        Get-Content $log -Tail 25 | ForEach-Object { Write-Host "      $_" -ForegroundColor DarkGray }
        $script:fallos += $Desc
    }
}

Write-Host "`nVerificando lo mismo que el CI (rapido -> lento)`n"

# 1) lint
Ejecutar 'ruff check' { & $py -m ruff check . }

# 2) tests + cobertura, con el MISMO umbral que el CI (no basta con que pasen).
Ejecutar 'pytest + cobertura (>=80%)' {
    $env:SECRET_KEY = 'test-secret-key-not-for-prod'; $env:DEBUG = 'True'
    & $py -m pytest -q -rs --cov=apps --cov=core --cov=nicegui_ui --cov-fail-under=80
}

# 2b) el esquema OpenAPI es el contrato publicado: si un endpoint queda sin anotar, sale
#     documentado como algo que no es. --fail-on-warn convierte eso en un fallo.
Ejecutar 'esquema OpenAPI (--fail-on-warn)' {
    $env:SECRET_KEY = 'test-secret-key-not-for-prod'; $env:DEBUG = 'True'
    & $py manage.py spectacular --validate --fail-on-warn --file $env:TEMP\schema_verificar.yml
}

# 3) hardening de produccion: el olvidado. Clave efimera porque el gate de core/conf.py
#    exige >=50 chars y >=5 distintos (con una debil fallaria por la clave, no por el
#    hardening, que es lo que se quiere medir).
Ejecutar 'check --deploy (hardening)' {
    $env:SECRET_KEY = & $py -c "import secrets; print(secrets.token_urlsafe(64))"
    $env:DEBUG = 'False'; $env:SECURE_HTTPS = 'True'
    $env:ALLOWED_HOSTS = 'all-in-django.local'; $env:DATABASE_URL = ''
    & $py manage.py check --deploy --fail-level WARNING
}
$env:DEBUG = 'True'; $env:SECURE_HTTPS = 'False'

# 4) smoke: que el stack ARRANQUE, no solo que las imagenes compilen.
if (-not $Rapido) {
    Ejecutar 'build + arranque del stack' {
        # Los MISMOS dos pasos que el job `build` del CI (build y luego up --no-build), no
        # un `up --build` que los funde en uno: esa diferencia fue justo la que dejo pasar
        # un fallo de nombre de imagen hasta el CI ("No such image: all_in_django-api").
        # Un script que no reproduce el job fielmente da la misma falsa seguridad que no
        # tenerlo.
        docker compose --env-file .env.docker build
        if ($LASTEXITCODE -ne 0) { return }
        docker compose --env-file .env.docker up -d --no-build
        if ($LASTEXITCODE -ne 0) { return }
        foreach ($i in 1..60) {
            $e = @('all_in_django-db', 'all_in_django', 'all_in_django-ui') |
                 ForEach-Object { docker inspect -f '{{.State.Health.Status}}' $_ 2>$null }
            if (($e | Where-Object { $_ -eq 'healthy' }).Count -eq 3) { $global:LASTEXITCODE = 0; return }
            if ($e -contains 'unhealthy') { $global:LASTEXITCODE = 1; return }
            Start-Sleep 5
        }
        $global:LASTEXITCODE = 1
    }
} else {
    Write-Host "  --  build + arranque del stack (saltado por -Rapido)" -ForegroundColor DarkGray
}

# 5) pruebas HTTP de la API con la coleccion Postman, igual que el job `build` del CI.
#    Va contra su PROPIO stack efimero (docker-compose.test.yml), no contra el de arriba:
#    la coleccion escribe y borra datos, y el stack normal corre sobre el volumen con los
#    datos reales. Si el CI ejercita la API viva y este script no, deja de reproducirlo.
if (-not $Rapido) {
    Ejecutar 'API por HTTP (coleccion Postman)' {
        & "$PSScriptRoot\probar_api.ps1"
    }
} else {
    Write-Host "  --  API por HTTP (saltado por -Rapido)" -ForegroundColor DarkGray
}

# 6) verificacion VISUAL en navegador real (marca `visual`, excluida del pytest normal y
#    del CI). Mide computed style y contraste: es lo unico que comprueba que el CSS GANA la
#    cascada, no solo que esta escrito. Vigila las tres regresiones documentadas (cubierta
#    borrada por el shorthand de bg-black, rebote que se pausa en vez de apagarse y el
#    bloque prefers-reduced-motion). Necesita `playwright install chromium` una vez.
if (-not $Rapido) {
    Ejecutar 'visual (contraste y estilos en Chromium)' {
        & $py -m pytest -m visual -q -rs
    }
} else {
    Write-Host "  --  visual (saltado por -Rapido)" -ForegroundColor DarkGray
}

Write-Host ""
if ($fallos.Count -eq 0) {
    Write-Host "Todo en verde. Puedes commitear." -ForegroundColor Green
    exit 0
}
Write-Host "NO commitees todavia. Fallaron: $($fallos -join ', ')" -ForegroundColor Red
exit 1
