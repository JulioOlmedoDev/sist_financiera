import os
import shutil
import subprocess
import tempfile
from pathlib import Path

PLANTILLA_CONTRATO = "plantillas/plantilla_contrato_mutuo.docx"
PLANTILLA_PAGARE   = "plantillas/plantilla_pagare_con_garante.docx"


def _encontrar_soffice() -> str | None:
    candidatos = ["libreoffice", "soffice"]
    if os.name == "nt":
        candidatos += [
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
    for c in candidatos:
        if shutil.which(c):
            return c
    return None


def docx_a_pdf(docx_path: str, outdir: str = None) -> str:
    """Convierte un .docx a PDF usando LibreOffice headless."""
    if outdir is None:
        outdir = tempfile.mkdtemp()
    perfil_tmp = tempfile.mkdtemp(prefix="lo_profile_")
    soffice = _encontrar_soffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice no está instalado o no se encuentra en el PATH.\n"
            "Instalalo desde https://www.libreoffice.org/"
        )
    try:
        resultado = subprocess.run(
            [
                soffice, "--headless",
                f"-env:UserInstallation={Path(perfil_tmp).as_uri()}",
                "--convert-to", "pdf",
                "--outdir", outdir,
                docx_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if resultado.returncode != 0:
            raise RuntimeError(f"LibreOffice falló al convertir:\n{resultado.stderr}")
        nombre = os.path.splitext(os.path.basename(docx_path))[0] + ".pdf"
        return os.path.join(outdir, nombre)
    finally:
        shutil.rmtree(perfil_tmp, ignore_errors=True)


def generar_docs_word(venta) -> tuple[str, str]:
    """Genera contrato y pagaré en Word. Retorna (path_contrato, path_pagare)."""
    from utils.generador_contrato import generar_contrato_word
    from utils.generador_pagare import generar_pagare_word

    faltan = [p for p in (PLANTILLA_CONTRATO, PLANTILLA_PAGARE) if not os.path.exists(p)]
    if faltan:
        raise FileNotFoundError("Plantillas no encontradas:\n- " + "\n- ".join(faltan))
    return (
        generar_contrato_word(venta, PLANTILLA_CONTRATO),
        generar_pagare_word(venta, PLANTILLA_PAGARE),
    )


def generar_docs_pdf(venta) -> tuple[str, str]:
    """Genera contrato y pagaré en PDF (Word → LibreOffice). Retorna (pdf_contrato, pdf_pagare)."""
    path_c, path_p = generar_docs_word(venta)
    outdir = tempfile.mkdtemp()
    return docx_a_pdf(path_c, outdir), docx_a_pdf(path_p, outdir)
