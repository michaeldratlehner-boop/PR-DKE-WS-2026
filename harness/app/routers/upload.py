from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from app.services.pdf_verarbeitung import speichere_pdf_und_datenbank, verarbeite_pdf_im_hintergrund

router = APIRouter(tags=["Upload"])


@router.post("/upload")
async def upload_anleitung(
        background_tasks: BackgroundTasks,
        datei: UploadFile = File(...)
):
    # 1. Validierung
    if not datei.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Nur PDF-Dateien sind erlaubt.")

    # 2. Datei in den RAM laden
    datei_bytes = await datei.read()

    try:
        # 3. Speichern in Supabase Storage und in der Tabelle "dokument" (synchron & schnell)
        produkt_id, dokument_id, datei_pfad = speichere_pdf_und_datenbank(
            datei.filename, datei_bytes
        )

        # 4. Hintergrundaufgabe an FastAPI übergeben (blockiert den Nutzer nicht)
        background_tasks.add_task(
            verarbeite_pdf_im_hintergrund, produkt_id, dokument_id, datei_pfad
        )
        # 5. Sofortige Rückmeldung an das Frontend
        return {
            "status": "Erfolgreich hochgeladen",
            "produkt_id": produkt_id,
            "dokument_id": dokument_id,
            "hinweis": "Die Datei wird im Hintergrund verarbeitet (Chunking & Embedding).",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fehler beim Upload: {str(e)}")