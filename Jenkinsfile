pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(name: "DEPLOY_PROD", defaultValue: false, description: "Deploy with docker compose after a successful build")
        string(name: "HTTP_PORT", defaultValue: "8081", description: "Host port exposed by the nginx container")
    }

    environment {
        APP_DIR = "monitor-server"
        DOCKER_IMAGE = "monitor-server"
        COMPOSE_FILE = "docker-compose.prod.yml"
        APP_DEBUG = "false"
    }

    stages {
        stage("Checkout") {
            steps {
                checkout scm
            }
        }

        stage("Docker Build") {
            steps {
                dir("${APP_DIR}") {
                    sh """
                        set -eu
                        docker build -t ${DOCKER_IMAGE}:${BUILD_NUMBER} -t ${DOCKER_IMAGE}:latest .
                    """
                }
            }
        }

        stage("Test") {
            steps {
                sh """
                    set -eu
                    docker run --rm ${DOCKER_IMAGE}:${BUILD_NUMBER} python -m pytest src/tests/ --tb=short
                """
            }
        }

        stage("Deploy Production") {
            when {
                expression { return params.DEPLOY_PROD }
            }
            steps {
                sh """
                    set -eu
                    HTTP_PORT=${params.HTTP_PORT} IMAGE_TAG=${BUILD_NUMBER} docker compose -f ${COMPOSE_FILE} up -d --remove-orphans
                    docker image prune -f
                """
            }
        }
    }

    post {
        success {
            echo "Pipeline succeeded. Built ${DOCKER_IMAGE}:${BUILD_NUMBER}"
        }
        failure {
            echo "Pipeline failed. Check the Jenkins console log."
        }
    }
}
