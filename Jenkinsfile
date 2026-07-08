pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "monitor-server"
    }

    stages {
        stage("Checkout") {
            steps {
                checkout scm
            }
        }

        stage("Test") {
            steps {
                dir("monitor-server") {
                    sh """
                        python -m venv .venv
                        . .venv/bin/activate
                        pip install -r requirements.txt
                        pytest src/tests/ --tb=short
                    """
                }
            }
        }

        stage("Build") {
            steps {
                dir("monitor-server") {
                    sh "docker build -t ${DOCKER_IMAGE}:${BUILD_NUMBER} ."
                }
            }
        }

        stage("Deploy") {
            steps {
                sh "docker-compose -f docker-compose.prod.yml up -d"
            }
        }
    }

    post {
        failure {
            echo "Pipeline failed — check logs."
        }
    }
}
