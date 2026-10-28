// PaySwift Jenkins shared library — image scan step (Trivy).
// A HIGH/CRITICAL finding fails the build; that is the point of the gate.
def call(Map cfg) {
    sh "trivy image --severity HIGH,CRITICAL --exit-code 1 ${cfg.image}:${cfg.tag}"
}
