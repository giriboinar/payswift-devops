// PaySwift Jenkins shared library — test step.
def call() {
    sh 'python -m venv .venv && . .venv/bin/activate && pip install -q -r requirements.txt -r requirements-dev.txt && pytest -v'
}
