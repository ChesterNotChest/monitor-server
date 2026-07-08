pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(name: "DEPLOY_PROD", defaultValue: false, description: "Deploy with docker compose after a successful build")
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

        stage("Test") {
            steps {
                dir("${APP_DIR}") {
                    sh """
                        set -eu
                        python -m venv .venv
                        . .venv/bin/activate
                        python -m pip install --upgrade pip
                        pip install -r requirements.txt
                        pytest src/tests/ --tb=short
                    """
                }
            }
        }

        stage("Docker Build") {
            steps {
                dir("${APP_DIR}") {
                    sh """
                        set -eu
                        docker build \\
                            -t ${DOCKER_IMAGE}:${BUILD_NUMBER} \\
                            -t ${DOCKER_IMAGE}:latest \\
                            .
                    """
                }
            }
        }

        stage("Deploy Production") {
            when {
                expression { return params.DEPLOY_PROD }
            }
            steps {
                sh """
                    set -eu
                    IMAGE_TAG=${BUILD_NUMBER} docker compose -f ${COMPOSE_FILE} up -d --remove-orphans
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
