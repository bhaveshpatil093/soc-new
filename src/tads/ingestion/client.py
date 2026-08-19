from elasticsearch import AsyncElasticsearch
from tads.schema.settings import Settings

def get_es_client(settings: Settings) -> AsyncElasticsearch:
    """
    Creates an AsyncElasticsearch client from settings.
    """
    client_kwargs = {
        "hosts": [str(settings.elastic_host)],
        "basic_auth": (settings.elastic_username, settings.elastic_password.get_secret_value()),
        "request_timeout": settings.elastic_timeout,
        "verify_certs": settings.elastic_verify_tls,
    }
    
    if settings.elastic_ca_cert:
        client_kwargs["ca_certs"] = str(settings.elastic_ca_cert)
        
    return AsyncElasticsearch(**client_kwargs)
