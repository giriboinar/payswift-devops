// PaySwift Jenkins shared library — build step (SIMULATION project).
// Builds the API image. Image name/tag come from the Jenkinsfile caller.
def call(Map cfg) {
    sh "docker build -t ${cfg.image}:${cfg.tag} ."
}
