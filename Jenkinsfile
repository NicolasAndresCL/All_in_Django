// CD de All in Django — despliega en el MISMO daemon Docker donde corre Jenkins.
// El CI (lint + tests + hardening + build/arranque + publish a GHCR) sigue en GitHub
// Actions; aqui solo se DESPLIEGA una imagen ya publicada.
//
// Prerequisitos en Jenkins (ver README §"CD con Jenkins"):
//   - Contenedor de Jenkins con docker CLI + docker compose y /var/run/docker.sock montado.
//   - Credencial 'all-in-django-env' (Secret file) = contenido de .env.docker
//     (SECRET_KEY, POSTGRES_*, API_TOKEN...). Nunca se versiona.
//   - (Solo si los paquetes GHCR son privados) credencial 'ghcr-credentials'
//     (Username/Password: usuario GitHub + PAT con read:packages).
//   - Un tag v* pusheado para que Actions publique las imagenes.
//
// El nombre de proyecto compose lo fija `name: all_in_django` DENTRO del compose, asi que
// no hace falta -p y dev y deploy no pueden divergir (antes: 'all_in_django' en dev por el
// nombre del directorio vs '-p all-in-django' aqui — dos stacks distintos para la misma
// app, y este pipeline esperaba un contenedor 'all-in-django-api-1' que no existia).

pipeline {
    agent any

    parameters {
        string(name: 'IMAGE_TAG', defaultValue: '',
               description: 'Tag a desplegar. Semver publicado (p. ej. 1.0.0 o 1.0). Actions NO publica "latest": dejarlo vacio o poner "latest" aborta el job.')
        string(name: 'REGISTRY', defaultValue: 'ghcr.io',
               description: 'Registry de donde tirar las imagenes. ghcr.io en uso normal; un registry local (p. ej. localhost:5000) permite ensayar el pipeline completo sin publicar nada fuera.')
        booleanParam(name: 'RUN_LOADDATA', defaultValue: false,
                     description: 'Sembrar datos con loaddata (una sola vez; requiere fixtures/datos_sqlite.json en el workspace).')
        booleanParam(name: 'GHCR_PRIVATE', defaultValue: false,
                     description: 'Marca si los paquetes GHCR son privados (hace docker login con la credencial ghcr-credentials).')
    }

    environment {
        // REGISTRY es un parametro (arriba), no una constante: asi el mismo pipeline
        // sirve para desplegar de GHCR y para ensayarse contra un registry local.
        REGISTRY    = "${params.REGISTRY}"
        IMAGE_OWNER = 'nicolasandrescl'
        API_CTR     = 'all_in_django'
        UI_CTR      = 'all_in_django-ui'
        DB_CTR      = 'all_in_django-db'
        PG_USER     = 'all_in_django'
        PG_DB       = 'all_in_django'
        COMPOSE_F   = 'docker-compose.deploy.yml'
        // Deja constancia del ultimo tag desplegado con exito, para poder revertir solo.
        ESTADO      = '.jenkins-ultimo-tag-ok'
    }

    options {
        timestamps()
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
    }

    stages {
        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Validar parametros') {
            steps {
                script {
                    // Fail-fast: 'latest' no existe en GHCR (docker-publish.yml publica solo
                    // semver y sha). Descubrirlo aqui cuesta segundos; descubrirlo en el pull
                    // deja el stack a medias.
                    def tag = params.IMAGE_TAG?.trim()
                    if (!tag || tag == 'latest') {
                        error("IMAGE_TAG invalido ('${tag}'). Actions no publica 'latest': usa el semver publicado, p. ej. 1.0.0.")
                    }
                    echo "Desplegando ${REGISTRY}/${IMAGE_OWNER}/all-in-django-{api,ui}:${tag}"
                }
            }
        }

        stage('Preparar .env.docker') {
            steps {
                // Los secretos llegan de una credencial Secret file, nunca del repo.
                withCredentials([file(credentialsId: 'all-in-django-env', variable: 'ENV_FILE')]) {
                    sh 'cp "$ENV_FILE" .env.docker'
                }
            }
        }

        stage('Respaldo previo') {
            steps {
                // Un CD que reemplaza la imagen de la API tiene que poder devolver los datos
                // a como estaban. Si aun no hay base (primer despliegue), no es un error.
                sh '''
                    set -e
                    if [ "$(docker inspect -f '{{.State.Status}}' "$DB_CTR" 2>/dev/null)" = "running" ]; then
                        mkdir -p respaldos
                        nombre="pre-deploy-$(date +%Y%m%d_%H%M%S).dump"
                        # El dump se genera y se VERIFICA dentro del contenedor, y solo
                        # despues se saca con `docker cp`. pg_restore --list no lee de
                        # stdin ("-" no es un origen valido), asi que tiene que operar
                        # sobre un archivo real.
                        docker exec "$DB_CTR" pg_dump -U "$PG_USER" -d "$PG_DB" -Fc -f "/tmp/$nombre"
                        # Un dump que no se puede leer no es un respaldo: comprobarlo aqui,
                        # no el dia que haga falta restaurarlo.
                        docker exec "$DB_CTR" pg_restore --list "/tmp/$nombre" > /dev/null
                        docker cp "$DB_CTR:/tmp/$nombre" "respaldos/$nombre"
                        docker exec "$DB_CTR" rm -f "/tmp/$nombre"
                        echo "Respaldo verificado: respaldos/$nombre ($(wc -c < "respaldos/$nombre") bytes)"
                    else
                        echo "No hay base corriendo todavia (primer despliegue): sin respaldo previo."
                    fi
                '''
            }
        }

        stage('Login GHCR') {
            when { expression { params.GHCR_PRIVATE } }
            steps {
                withCredentials([usernamePassword(credentialsId: 'ghcr-credentials',
                                                  usernameVariable: 'GHCR_USER',
                                                  passwordVariable: 'GHCR_PAT')]) {
                    sh 'echo "$GHCR_PAT" | docker login ghcr.io -u "$GHCR_USER" --password-stdin'
                }
            }
        }

        stage('Pull') {
            steps {
                withEnv(["IMAGE_TAG=${params.IMAGE_TAG}"]) {
                    sh 'docker compose --env-file .env.docker -f "$COMPOSE_F" pull'
                }
            }
        }

        stage('Deploy') {
            steps {
                withEnv(["IMAGE_TAG=${params.IMAGE_TAG}"]) {
                    sh 'docker compose --env-file .env.docker -f "$COMPOSE_F" up -d'
                }
            }
        }

        stage('Semilla (loaddata)') {
            when { expression { params.RUN_LOADDATA } }
            steps {
                withEnv(["IMAGE_TAG=${params.IMAGE_TAG}"]) {
                    sh '''
                        docker compose --env-file .env.docker -f "$COMPOSE_F" \
                            run --rm -v "$(pwd)/fixtures:/app/fixtures" api \
                            python manage.py loaddata fixtures/datos_sqlite.json
                    '''
                }
            }
        }

        stage('Healthcheck') {
            steps {
                // Espera a que compose reporte sanos la API *y* la UI. Antes solo se miraba la
                // API: una UI rota por falta de token pasaba por despliegue correcto.
                // Se consulta el healthcheck del contenedor (definido en la imagen), no el
                // puerto publicado, para no depender de la red Jenkins -> host.
                sh '''
                    set -e
                    for i in $(seq 1 36); do
                        a=$(docker inspect -f '{{.State.Health.Status}}' "$API_CTR" 2>/dev/null || echo ausente)
                        u=$(docker inspect -f '{{.State.Health.Status}}' "$UI_CTR"  2>/dev/null || echo ausente)
                        echo "[$i] api=$a ui=$u"
                        if [ "$a" = "healthy" ] && [ "$u" = "healthy" ]; then
                            echo "Stack sano."
                            exit 0
                        fi
                        if [ "$a" = "unhealthy" ] || [ "$u" = "unhealthy" ]; then
                            echo "Un servicio quedo unhealthy."
                            exit 1
                        fi
                        sleep 5
                    done
                    echo "El stack no quedo sano a tiempo."
                    exit 1
                '''
                // Solo tras un despliegue SANO se anota el tag como "bueno conocido".
                withEnv(["IMAGE_TAG=${params.IMAGE_TAG}"]) {
                    sh 'printf "%s\\n" "$IMAGE_TAG" > "$ESTADO"'
                }
            }
        }
    }

    post {
        success {
            echo "Deploy OK: ${IMAGE_OWNER}/all-in-django:${params.IMAGE_TAG} · API :8000/healthz · UI :8501"
            archiveArtifacts artifacts: 'respaldos/*.dump', allowEmptyArchive: true, fingerprint: true
        }
        failure {
            sh 'docker compose --env-file .env.docker -f "$COMPOSE_F" ps || true'
            sh 'docker compose --env-file .env.docker -f "$COMPOSE_F" logs --tail=100 || true'
            // Rollback automatico al ultimo tag que SI quedo sano. Antes esto era una nota
            // pidiendo al operador que relanzara el job a mano, justo cuando el servicio esta
            // caido y la prisa hace equivocarse.
            withEnv(["TAG_FALLIDO=${params.IMAGE_TAG}"]) {
                sh '''
                    if [ ! -f "$ESTADO" ]; then
                        echo "Primer despliegue (sin tag previo conocido): sin rollback automatico."
                        exit 0
                    fi
                    anterior=$(cat "$ESTADO")
                    if [ -z "$anterior" ] || [ "$anterior" = "$TAG_FALLIDO" ]; then
                        echo "No hay un tag anterior distinto al fallido: sin rollback automatico."
                        exit 0
                    fi
                    echo "ROLLBACK automatico a $anterior"
                    IMAGE_TAG="$anterior" docker compose --env-file .env.docker -f "$COMPOSE_F" up -d \
                        || echo "El rollback tambien fallo: hace falta intervencion manual."
                '''
            }
            echo "Deploy FALLO. Si hubo rollback, el servicio volvio al tag anterior; el respaldo previo queda archivado en la build."
        }
        always {
            // Nunca dejar el .env.docker (secretos) en el workspace.
            sh 'rm -f .env.docker || true'
        }
        cleanup {
            // Los dumps se borran en `cleanup`, NO en `always`: el orden de los bloques
            // post es always -> failure/success -> cleanup, asi que un `rm -rf respaldos`
            // en `always` se ejecuta ANTES que el archiveArtifacts de `success` y se
            // llevaba por delante el respaldo que se pretendia guardar. Detectado
            // ejecutando el pipeline de verdad: "respaldos/*.dump doesn't match anything".
            sh 'rm -rf respaldos || true'
        }
    }
}
