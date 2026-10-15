# Stubs mínimos do firebase_admin (o pacote não publica tipos): só o que o projeto usa.
from firebase_admin.credentials import Certificate

class App: ...

_apps: dict[str, App]

def initialize_app(credential: Certificate) -> App: ...
