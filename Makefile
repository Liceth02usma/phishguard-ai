# Makefile de PhishGuard-AI. Wrapper Unix para el comando de calidad.
# En Windows usar directamente: python scripts/verify.py

.PHONY: verify

verify:
	python scripts/verify.py
