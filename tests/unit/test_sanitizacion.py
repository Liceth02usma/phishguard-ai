"""Unidad y propiedades de `sanitizar_parametros` (FR-007, research D10.4/D12).

Los 7 nombres literales de la FR-007 se eliminan, cualquier valor con forma
de correo se elimina aunque el nombre no sea sensible, los parámetros
inofensivos se conservan en orden y la URL original nunca se muta.
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from src.level2_agent.analisis_urls.configuracion import ConfigURLs
from src.level2_agent.analisis_urls.sanitizacion import sanitizar_parametros

_CONFIG = ConfigURLs()
FR007 = ["token", "key", "session", "email", "user", "code", "password"]


def test_los_siete_sensibles_de_fr007_desaparecen() -> None:
    """Los 7 nombres literales de la spec se eliminan todos juntos."""
    url = "http://e.com/p?token=a&key=b&session=c&email=d&user=e&code=f&password=g&page=1"

    saneada = sanitizar_parametros(url, _CONFIG)

    assert saneada == "http://e.com/p?page=1"
    for nombre in FR007:
        assert nombre not in saneada


def test_valor_con_forma_de_correo_se_elimina_en_cualquier_parametro() -> None:
    """Un valor con forma de correo cae aunque el parámetro no esté en la lista."""
    url = "http://e.com/p?contacto=juan.perez@banco.com&other=x"

    saneada = sanitizar_parametros(url, _CONFIG)

    assert saneada == "http://e.com/p?other=x"


def test_parametros_inofensivos_conservan_orden() -> None:
    """Los no sensibles sobreviven y conservan su orden original."""
    url = "http://e.com/p?z=1&a=2&m=3"

    saneada = sanitizar_parametros(url, _CONFIG)

    assert saneada == "http://e.com/p?z=1&a=2&m=3"


def test_sin_query_no_agrega_signo_de_pregunta() -> None:
    """Una URL sin query regresa idéntica (sin `?` colgante)."""
    url = "http://e.com/p"

    assert sanitizar_parametros(url, _CONFIG) == url


def test_url_original_nunca_se_muta() -> None:
    """Pureza: la entrada sigue intacta tras sanitizar (FR-001 conserva lo original)."""
    url = "http://e.com/p?token=secreto"

    saneada = sanitizar_parametros(url, _CONFIG)

    assert url == "http://e.com/p?token=secreto"
    assert "secreto" not in saneada


def test_valores_en_blanco_de_sensibles_se_eliminan() -> None:
    """`token=` (valor vacío) también se elimina: el nombre ya es sensible."""
    url = "http://e.com/p?token=&ok=1"

    assert sanitizar_parametros(url, _CONFIG) == "http://e.com/p?ok=1"


@given(valor=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=30))
@settings(max_examples=30, deadline=None)
def test_propiedad_ningun_valor_sensible_en_la_salida(valor: str) -> None:
    """Propiedad: para cualquier valor, `token=<valor>` nunca sobrevive al saneador."""
    url = f"http://e.com/p?token={valor}&id=99"

    saneada = sanitizar_parametros(url, _CONFIG)

    assert f"token={valor}" not in saneada
    assert "id=99" in saneada


@given(url=st.text(alphabet="abc0123?&=%@.:-/", min_size=0, max_size=60))
@settings(max_examples=40, deadline=None)
def test_propiedad_nunca_lanza_excepcion(url: str) -> None:
    """Propiedad: cualquier cadena arbitraria se sanea sin excepción (AC-URL-07)."""
    resultado = sanitizar_parametros(url, _CONFIG)
    assert isinstance(resultado, str)
