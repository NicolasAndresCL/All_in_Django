// CD de All in Django — despliega en el MISMO daemon Docker donde corre Jenkins.
// El CI (tests + build + publish a GHCR) sigue en GitHub Actions; aquí solo se DESPLIEGA
// (docker compose pull + up -d) una imagen ya publicada.
//
// Prerequisitos en Jenkins (ver README §"CD con Jenkins"):
//   - Contenedor de Jenkins con docker CLI + docker compose y /var/run/docker.sock montado.
//   - Credencial 'all-in-django-env' (Secret file) = contenido de .env.docker
//     (SECRET_KEY, POSTGRES_*, API_TOKEN...). Nunca se versiona.
//   - (Solo si los paquetes GHCR son privados) credencial 'ghcr-credentials'
//     (Username/Password: usuario GitHub + PAT con read:packages).
//   - Un tag v* pusheado para que Actions publique las imágenes.

pipeline {
    agent any

    parameters {
        string(name: 'IMAGE_TAG', defaultValue: 'latest',
               description: 'Tag de imagen GHCR a desplegar. Usa el semver publicado (p. ej. 1.0.0 o 1.0); Actions NO publica "latest".')
        booleanParam(name: 'RUN_LOADDATA', defaultValue: false,
                     description: 'Sembrar datos con loaddata (una sola vez; requiere fixtures/datos_sqlite.json en el workspace).')
        booleanParam(name: 'GHCR_PRIVATE', defaultValue: false,
                     description: 'Marca si los paquetes GHCR son privados (hace docker login con la credencial ghcr-credentials).')
    }

    environment {
        REGISTRY    = 'ghcr.io'
        IMAGE_OWNER = 'nicolasandrescl'
        COMPOSE     = 'docker-compose.deploy.yml'
        PROJECT     = 'all-in-django'
        // Prefijo reutilizable del comando compose (proyecto estable → up -d idempotente).
        DC          = "docker compose -p all-in-django --env-file .env.docker -f docker-compose.deploy.yml"
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

        stage('Preparar .env.docker') {
            steps {
                // El .env.docker (secretos) llega de una credencial Secret file, nunca del repo.
                withCredentials([file(credentialsId: 'all-in-django-env', variable: 'ENV_FILE')]) {
                    sh 'cp "$ENV_FILE" .env.docker'
                }
                echo "Desplegando ${REGISTRY}/${IMAGE_OWNER}/all-in-django-{api,ui}:${params.IMAGE_TAG}"
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
                sh "IMAGE_TAG='${params.IMAGE_TAG}' IMAGE_OWNER='${IMAGE_OWNER}' REGISTRY='${REGISTRY}' ${DC} pull"
            }
        }

        stage('Deploy') {
            steps {
                sh "IMAGE_TAG='${params.IMAGE_TAG}' IMAGE_OWNER='${IMAGE_OWNER}' REGISTRY='${REGISTRY}' ${DC} up -d"
            }
        }

        stage('Semilla (loaddata)') {
            when { expression { params.RUN_LOADDATA } }
            steps {
                sh """
                    IMAGE_TAG='${params.IMAGE_TAG}' IMAGE_OWNER='${IMAGE_OWNER}' REGISTRY='${REGISTRY}' \
                    ${DC} run --rm -v "\$(pwd)/fixtures:/app/fixtures" api \
                        python manage.py loaddata fixtures/datos_sqlite.json
                """
            }
        }

        stage('Healthcheck') {
            steps {
                // Espera a que el healthcheck de compose reporte la API 'healthy'
                // (evita depender de la red Jenkins→puerto publicado).
                sh '''
                    for i in $(seq 1 30); do
                        status=$(docker inspect -f '{{ .State.Health.Status }}' all-in-django-api-1 2>/dev/null || echo starting)
                        echo "api health: $status"
                        [ "$status" = "healthy" ] && exit 0
                        sleep 5
                    done
                    echo "La API no quedó healthy a tiempo."; exit 1
                '''
            }
        }
    }

    post {
        success {
            echo "Deploy OK: ${IMAGE_OWNER}/all-in-django:${params.IMAGE_TAG} · API :8000/healthz · UI :8501"
        }
        failure {
            sh "${DC} ps || true"
            sh "${DC} logs --tail=100 || true"
            echo "Deploy FALLÓ. Revisa los logs de arriba; puedes relanzar el Job con el IMAGE_TAG anterior para revertir."
        }
        always {
            // Nunca dejar el .env.docker (secretos) en el workspace.
            sh 'rm -f .env.docker || true'
        }
    }
}
