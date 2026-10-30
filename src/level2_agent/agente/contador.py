"""Contador diario de llamadas LLM (spec 009, M07, FR-007).

Persiste el conteo en MongoDB `phishguard.llm_contador` con TTL al
final del día. Fallback a in-memory si Mongo no está disponible
(igual que spec 006). Reloj inyectado para determinismo en pruebas.
"""

from __future__ import annotations

import os
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from .modelos import LLM_MAX_DIARIO_DEFAULT


class ContadorLLM:
    """Contador diario de llamadas al modelo LLM.

    Al superar LLM_MAX_DIARIO, la zona gris va a revision_manual
    sin llamar al modelo (FR-007, AC-AGT-05).
    """

    def __init__(
        self,
        *,
        max_diario: int | None = None,
        ahora: date | None = None,
    ) -> None:
        self._max_diario: int = max_diario or int(
            os.environ.get("LLM_MAX_DIARIO", str(LLM_MAX_DIARIO_DEFAULT))
        )
        self._hoy: date = ahora or date.today()
        self._conteo: int = 0
        self._mongo_disponible: bool = False
        self._inicializar_mongo()

    def _inicializar_mongo(self) -> None:
        """Intenta conectar a MongoDB para persistencia del contador."""
        uri = os.environ.get("MONGODB_ATLAS_CLUSTER_URI", "")
        if not uri:
            return
        try:
            from pymongo import MongoClient

            client: Any = MongoClient(uri, serverSelectionTimeoutMS=3000)
            db = client["phishguard"]
            self._coleccion = db["llm_contador"]
            self._mongo_disponible = True
            # Cargar conteo existente de hoy
            doc = self._coleccion.find_one({"fecha": str(self._hoy)})
            if doc:
                self._conteo = doc.get("conteo", 0)
        except Exception:
            # Fallback a in-memory
            self._mongo_disponible = False

    def disponible(self) -> bool:
        """Retorna True si aún no se superó el tope diario."""
        return self._conteo < self._max_diario

    def incrementar(self) -> int:
        """Incrementa el conteo y retorna el valor después de incrementar.

        No verifica el tope — el orquestador llama `disponible()` antes.
        """
        self._conteo += 1
        if self._mongo_disponible:
            try:
                # Calcular expiración: final del día
                manana = datetime.combine(
                    self._hoy + timedelta(days=1), time.min, tzinfo=timezone.utc
                )
                self._coleccion.update_one(
                    {"fecha": str(self._hoy)},
                    {
                        "$set": {
                            "conteo": self._conteo,
                            "expira_en": manana,
                        }
                    },
                    upsert=True,
                )
            except Exception:
                pass  # Fallback silencioso
        return self._conteo

    @property
    def conteo(self) -> int:
        """Conteo actual de llamadas en el día."""
        return self._conteo

    @property
    def max_diario(self) -> int:
        """Tope diario configurado."""
        return self._max_diario
