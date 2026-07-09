pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
    }

    parameters {
        booleanParam(name: "DEPLOY_PROD", defaultValue: false, description: "Deploy with docker compose after a successful build")
        string(name: "HTTP_PORT", defaultValue: "8081", description: "Host port exposed by the nginx container")
        string(name: "RTMP_PORT", defaultValue: "1935", description: "Host port for RTMP ingest")
        string(name: "STREAM_HTTP_PORT", defaultValue: "8082", description: "Host port for SRS HTTP/WebRTC access")
        string(name: "SRS_API_PORT", defaultValue: "1985", description: "Host port for SRS HTTP API")
        string(name: "SRS_RTC_PORT", defaultValue: "8000", description: "Host UDP port for SRS WebRTC media")
        string(name: "SRS_CANDIDATE", defaultValue: "10.126.59.25", description: "Public IP or domain returned by SRS for WebRTC")
        string(name: "SRS_PUBLIC_HOST", defaultValue: "10.126.59.25", description: "Public IP or domain returned to Web clients for SRS playback")
        string(name: "MODEL_DIR", defaultValue: "/home/liusu/video/models", description: "Host directory mounted read-only to /app/models")
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
                    HOST_WORKSPACE=\$(printf '%s\n' "\$WORKSPACE" | sed 's#^/var/jenkins_home#/home/liusu/jenkins#')
                    HTTP_PORT=${params.HTTP_PORT} RTMP_PORT=${params.RTMP_PORT} STREAM_HTTP_PORT=${params.STREAM_HTTP_PORT} SRS_API_PORT=${params.SRS_API_PORT} SRS_RTC_PORT=${params.SRS_RTC_PORT} SRS_CANDIDATE=${params.SRS_CANDIDATE} SRS_PUBLIC_HOST=${params.SRS_PUBLIC_HOST} MODEL_DIR=${params.MODEL_DIR} IMAGE_TAG=${BUILD_NUMBER} docker compose --project-directory "\$HOST_WORKSPACE" -f "\$HOST_WORKSPACE/${COMPOSE_FILE}" up -d --remove-orphans
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
