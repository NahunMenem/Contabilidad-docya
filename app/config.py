import os

DATABASE_URL = os.environ["DATABASE_URL"]

# Mismo secreto y algoritmo que usa el backend principal de DocYa para firmar
# el "docya_token" (JWT). Se configura como variable de entorno en Railway,
# nunca se hardcodea.
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

# Origenes permitidos para CORS (paneles de DocYa que consumen esta API).
# Los defaults se fuerzan aunque Railway tenga CORS_ORIGINS incompleto.
DEFAULT_CORS_ORIGINS = {
    "https://www.docya.online",
    "https://docya.online",
    "http://localhost:3000",
}

CORS_ORIGINS = sorted(
    DEFAULT_CORS_ORIGINS
    | {
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "").split(",")
        if origin.strip()
    }
)
