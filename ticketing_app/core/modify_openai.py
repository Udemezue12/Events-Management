from ticketing_app.app import app


def modify_openapi():
    openapi_schema = app.openapi()
    user_schema = openapi_schema["components"]["schemas"]["UserCreate"]

  
    user_schema["properties"].pop("name", None)
    user_schema["required"] = [
        field for field in user_schema.get("required", []) if field != "name"
    ]

    app.openapi_schema = openapi_schema
