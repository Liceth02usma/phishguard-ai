"""AC-DEC-01: cada regla dura R1–R5 tiene una prueba que la activa y otra que no.

M09 define 5 reglas duras que, al aplicar, fijan veredicto='malicioso'.
Este archivo verifica que cada regla se activa con su condición específica
y NO se activa cuando la condición no se cumple.
"""

from __future__ import annotations

from src.level2_agent.adjuntos.modelos import BanderaAdjunto
from src.level2_agent.banderas.modelos import (
    BanderaActivada,
    EstadosAutenticacion,
)
from src.level2_agent.virustotal.modelos import (
    LastAnalysisStats,
    ResultadoVT,
)

from dobles_decision import entrada_ejemplo


def _vt_maliciosa(tipo: str, identificador: str) -> ResultadoVT:
    """Crea un ResultadoVT con clasificación maliciosa."""
    return ResultadoVT(
        tipo=tipo,  # type: ignore[arg-type]
        identificador=identificador,
        clasificacion="maliciosa",
        fuente="cache",
        stats=LastAnalysisStats(malicious=10, suspicious=0, undetected=0, harmless=0),
        consultas_externas=0,
    )


def _vt_limpia(tipo: str, identificador: str) -> ResultadoVT:
    """Crea un ResultadoVT con clasificación limpia."""
    return ResultadoVT(
        tipo=tipo,  # type: ignore[arg-type]
        identificador=identificador,
        clasificacion="limpia",
        fuente="cache",
        stats=LastAnalysisStats(malicious=0, suspicious=0, undetected=0, harmless=10),
        consultas_externas=0,
    )


# --- R1: Hash de adjunto con clasificación VT maliciosa ---


class TestR1:
    """R1: algún hash de adjunto con clasificación VT maliciosa."""

    def test_activada(self) -> None:
        """Con un VT malicioso de tipo archivo → R1 aplica → malicioso."""
        entrada = entrada_ejemplo(
            resultados_vt=[_vt_maliciosa("archivo", "abc123sha256hash00000000000000000000")],
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert resultado.veredicto == "malicioso"
        assert resultado.ruta == "reglas"
        assert any(r.id == "R1" for r in resultado.reglas_aplicadas)

    def test_no_activada(self) -> None:
        """Sin VT malicioso de tipo archivo → R1 no aplica."""
        entrada = entrada_ejemplo(
            resultados_vt=[_vt_limpia("archivo", "abc123sha256hash00000000000000000000")],
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert not any(r.id == "R1" for r in resultado.reglas_aplicadas)


# --- R2: URL con clasificación VT maliciosa ---


class TestR2:
    """R2: alguna URL con clasificación VT maliciosa."""

    def test_activada(self) -> None:
        """Con un VT malicioso de tipo url → R2 aplica → malicioso."""
        entrada = entrada_ejemplo(
            resultados_vt=[_vt_maliciosa("url", "http://malware.example.com")],
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert resultado.veredicto == "malicioso"
        assert resultado.ruta == "reglas"
        assert any(r.id == "R2" for r in resultado.reglas_aplicadas)

    def test_no_activada(self) -> None:
        """Sin VT malicioso de tipo url → R2 no aplica."""
        entrada = entrada_ejemplo(
            resultados_vt=[_vt_limpia("url", "http://safe.example.com")],
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert not any(r.id == "R2" for r in resultado.reglas_aplicadas)


# --- R3: Dominio del remitente con clasificación VT maliciosa ---


class TestR3:
    """R3: dominio del remitente con clasificación VT maliciosa."""

    def test_activada(self) -> None:
        """Con un VT malicioso de tipo dominio → R3 aplica → malicioso."""
        entrada = entrada_ejemplo(
            resultados_vt=[_vt_maliciosa("dominio", "malware.example.com")],
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert resultado.veredicto == "malicioso"
        assert resultado.ruta == "reglas"
        assert any(r.id == "R3" for r in resultado.reglas_aplicadas)

    def test_no_activada(self) -> None:
        """Sin VT malicioso de tipo dominio → R3 no aplica."""
        entrada = entrada_ejemplo(
            resultados_vt=[_vt_limpia("dominio", "safe.example.com")],
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert not any(r.id == "R3" for r in resultado.reglas_aplicadas)


# --- R4: SPF+DKIM+DMARC fallan y (dominio parecido o nombre que suplanta) ---


class TestR4:
    """R4: SPF=fail Y DKIM=fail Y DMARC=fail Y (dominio parecido O nombre suplanta)."""

    def test_activada(self) -> None:
        """Con SPF/DKIM/DMARC fail + bandera DOMINIO_PARECIDO → R4 aplica."""
        entrada = entrada_ejemplo(
            estados_autenticacion=EstadosAutenticacion(
                spf="fail", dkim="fail", dmarc="fail",
            ),
            banderas_cabeceras=[
                BanderaActivada(
                    codigo="DOMINIO_PARECIDO",
                    severidad="alta",
                    puntos=20,
                    detalle="dominio parecido a propio",
                ),
            ],
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert resultado.veredicto == "malicioso"
        assert resultado.ruta == "reglas"
        assert any(r.id == "R4" for r in resultado.reglas_aplicadas)

    def test_no_activada_spf_pass(self) -> None:
        """Con SPF=pass → R4 no aplica (aunque dominio parecido)."""
        entrada = entrada_ejemplo(
            estados_autenticacion=EstadosAutenticacion(
                spf="pass", dkim="fail", dmarc="fail",
            ),
            banderas_cabeceras=[
                BanderaActivada(
                    codigo="DOMINIO_PARECIDO",
                    severidad="alta",
                    puntos=20,
                    detalle="dominio parecido a propio",
                ),
            ],
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert not any(r.id == "R4" for r in resultado.reglas_aplicadas)

    def test_no_activada_sin_banderas(self) -> None:
        """Con SPF/DKIM/DMARC fail pero sin bandera de suplantación → R4 no aplica."""
        entrada = entrada_ejemplo(
            estados_autenticacion=EstadosAutenticacion(
                spf="fail", dkim="fail", dmarc="fail",
            ),
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert not any(r.id == "R4" for r in resultado.reglas_aplicadas)


# --- R5: Adjunto de macro/ejecutable en archivo cifrado, remitente no autenticado ---


class TestR5:
    """R5: adjunto de macro/ejecutable en archivo cifrado, remitente no autenticado."""

    def test_activada(self) -> None:
        """Con ADJ_MACRO + adjunto cifrado + SPF fail → R5 aplica."""
        from src.level2_agent.adjuntos.modelos import AnalisisAdjunto

        adjunto = AnalisisAdjunto(
            nombre="doc.docm",
            tipo_declarado="application/vnd.ms-word.document.macroEnabled.12",
            tipo_real="docm",
            tamano_bytes=1024,
            sha256="a" * 64,
            md5="b" * 32,
            sha1="c" * 40,
            banderas=[
                BanderaAdjunto(
                    codigo="ADJ_MACRO", severidad="alta", puntos=20,
                    detalle="macro detectado",
                )
            ],
            detalles=["cifrado_con_contrasena"],
        )
        entrada = entrada_ejemplo(
            resultado_adjuntos=[adjunto],
            estados_autenticacion=EstadosAutenticacion(spf="fail"),
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert resultado.veredicto == "malicioso"
        assert resultado.ruta == "reglas"
        assert any(r.id == "R5" for r in resultado.reglas_aplicadas)

    def test_no_activada_spf_pass(self) -> None:
        """Con ADJ_MACRO + cifrado pero SPF pass → R5 no aplica (remitente autenticado)."""
        from src.level2_agent.adjuntos.modelos import AnalisisAdjunto

        adjunto = AnalisisAdjunto(
            nombre="doc.docm",
            tipo_declarado="application/vnd.ms-word.document.macroEnabled.12",
            tipo_real="docm",
            tamano_bytes=1024,
            sha256="a" * 64,
            md5="b" * 32,
            sha1="c" * 40,
            banderas=[
                BanderaAdjunto(
                    codigo="ADJ_MACRO", severidad="alta", puntos=20,
                    detalle="macro detectado",
                )
            ],
            detalles=["cifrado_con_contrasena"],
        )
        entrada = entrada_ejemplo(
            resultado_adjuntos=[adjunto],
            estados_autenticacion=EstadosAutenticacion(spf="pass"),
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert not any(r.id == "R5" for r in resultado.reglas_aplicadas)

    def test_no_activada_sin_cifrado(self) -> None:
        """Con ADJ_MACRO pero sin cifrado → R5 no aplica."""
        from src.level2_agent.adjuntos.modelos import AnalisisAdjunto

        adjunto = AnalisisAdjunto(
            nombre="doc.docm",
            tipo_declarado="application/vnd.ms-word.document.macroEnabled.12",
            tipo_real="docm",
            tamano_bytes=1024,
            sha256="a" * 64,
            md5="b" * 32,
            sha1="c" * 40,
            banderas=[
                BanderaAdjunto(
                    codigo="ADJ_MACRO", severidad="alta", puntos=20,
                    detalle="macro detectado",
                )
            ],
            detalles=[],
        )
        entrada = entrada_ejemplo(
            resultado_adjuntos=[adjunto],
            estados_autenticacion=EstadosAutenticacion(spf="fail"),
        )
        from src.level2_agent.decision.motor import evaluar_veredicto

        resultado = evaluar_veredicto(entrada)
        assert not any(r.id == "R5" for r in resultado.reglas_aplicadas)
