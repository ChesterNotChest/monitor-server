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
        string(name: "MODEL_DIR", defaultValue: "/home/liusu/video/models", description: "Host directory mounted read-only to /app/src/third-party")
        string(name: "DATABASE_URL", defaultValue: "mysql+pymysql://monitor:monitor_placeholder2026@monitor-mysql:3306/monitor?charset=utf8mb4", description: "SQLAlchemy database URL used by the production app container")
        password(name: "JWT_SECRET", defaultValue: "change-me-in-jenkins-before-prod", description: "JWT signing secret for the production app")
        booleanParam(name: "RUN_SEED_DATA", defaultValue: false, description: "Run python -m src.seed_data after deployment")
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
                    sh '''
                        set -eu
                        docker build -t ${DOCKER_IMAGE}:${BUILD_NUMBER} -t ${DOCKER_IMAGE}:latest .
                    '''
                }
            }
        }

        stage("Test") {
            steps {
                withEnv(["MODEL_DIR=${params.MODEL_DIR}"]) {
                    sh '''
                        set -eu
                        docker run --rm \
                          -v "$MODEL_DIR:/app/src/third-party:ro" \
                          ${DOCKER_IMAGE}:${BUILD_NUMBER} \
                          sh -c 'test -f /app/src/third-party/yolo/yolo11n.pt && python -m pytest src/tests/ --tb=short'
                    '''
                }
            }
        }

        stage("Deploy Production") {
            when {
                expression { return params.DEPLOY_PROD }
            }
            steps {
                withEnv([
                    "HTTP_PORT=${params.HTTP_PORT}",
                    "RTMP_PORT=${params.RTMP_PORT}",
                    "STREAM_HTTP_PORT=${params.STREAM_HTTP_PORT}",
                    "SRS_API_PORT=${params.SRS_API_PORT}",
                    "SRS_RTC_PORT=${params.SRS_RTC_PORT}",
                    "SRS_CANDIDATE=${params.SRS_CANDIDATE}",
                    "SRS_PUBLIC_HOST=${params.SRS_PUBLIC_HOST}",
                    "MODEL_DIR=${params.MODEL_DIR}",
                    "DATABASE_URL=${params.DATABASE_URL}",
                    "JWT_SECRET=${params.JWT_SECRET}",
                    "IMAGE_TAG=${BUILD_NUMBER}",
                ]) {
                    sh '''
                        set -eu
                        HOST_WORKSPACE=${WORKSPACE}
                        case "$HOST_WORKSPACE" in
                            /var/jenkins_home/*) HOST_WORKSPACE="/home/liusu/jenkins/${HOST_WORKSPACE#/var/jenkins_home/}" ;;
                        esac
                        docker run --rm -v "$MODEL_DIR:/models:ro" "$DOCKER_IMAGE:$IMAGE_TAG" test -d /models
                        docker network inspect servercicd_default >/dev/null
                        docker ps --filter name=monitor-mysql --format '{{.Names}} {{.Status}}' | grep -q '^monitor-mysql '
                        docker compose --project-directory "$HOST_WORKSPACE" -f "$HOST_WORKSPACE/$COMPOSE_FILE" up -d --remove-orphans
                        docker image prune -f
                    '''
                }
            }
        }

        stage("Post Deploy Check") {
            when {
                expression { return params.DEPLOY_PROD }
            }
            steps {
                withEnv(["HTTP_PORT=${params.HTTP_PORT}"]) {
                    sh '''
                        set -eu
                        HOST_WORKSPACE=${WORKSPACE}
                        case "$HOST_WORKSPACE" in
                            /var/jenkins_home/*) HOST_WORKSPACE="/home/liusu/jenkins/${HOST_WORKSPACE#/var/jenkins_home/}" ;;
                        esac
                        docker compose --project-directory "$HOST_WORKSPACE" -f "$HOST_WORKSPACE/$COMPOSE_FILE" ps
                        curl --noproxy '*' -fsS "http://127.0.0.1:${HTTP_PORT}/health"
                        docker exec monitor-app python -c "from src.app import app; print([getattr(r, 'path', None) for r in app.routes])"
                    '''
                }
            }
        }

        stage("Seed Production Data") {
            when {
                expression { return params.DEPLOY_PROD && params.RUN_SEED_DATA }
            }
            steps {
                sh '''
                    set -eu
                    HOST_WORKSPACE=${WORKSPACE}
                    case "$HOST_WORKSPACE" in
                        /var/jenkins_home/*) HOST_WORKSPACE="/home/liusu/jenkins/${HOST_WORKSPACE#/var/jenkins_home/}" ;;
                    esac
                    docker compose --project-directory "$HOST_WORKSPACE" -f "$HOST_WORKSPACE/$COMPOSE_FILE" exec -T app python -m src.seed_data
                '''
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
