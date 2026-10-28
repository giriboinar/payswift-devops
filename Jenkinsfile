// PaySwift Jenkinsfile (SIMULATION project).
// Uses the shared library in jenkins-shared-lib/ (vars/: buildApp,
// testApp, scanImage, helmDeploy). In a real Jenkins, the library is
// loaded from SCM; here the steps are kept identical to the local/CI flow.
@Library('payswift-shared-lib') _

pipeline {
    agent any
    environment {
        IMAGE = 'payswift-api'
        TAG = "${env.BUILD_NUMBER}"
    }
    stages {
        stage('Build') { steps { buildApp(image: env.IMAGE, tag: env.TAG) } }
        stage('Test') { steps { testApp() } }
        stage('Scan') { steps { scanImage(image: env.IMAGE, tag: env.TAG) } }
        stage('Deploy') {
            steps { helmDeploy(release: 'payswift', namespace: 'payswift', tag: env.TAG) }
        }
    }
}
