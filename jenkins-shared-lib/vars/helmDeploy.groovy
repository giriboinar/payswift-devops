// PaySwift Jenkins shared library — Helm deploy step.
// Deploys to the target namespace only; the caller passes the release name.
def call(Map cfg) {
    sh "helm upgrade --install ${cfg.release} ./helm/payswift --namespace ${cfg.namespace} --create-namespace --set image.tag=${cfg.tag}"
}
