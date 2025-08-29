from fastapi import FastAPI, UploadFile, Form
import tempfile, shutil
import speech_service

app = FastAPI()

@app.post("/speech-analiz")
async def speech_analiz(
    audio: UploadFile, 
    text: str = Form(...), 
    locale: str = Form("en-US")
):
    # Ses dosyasını temp klasöre kaydet
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        shutil.copyfileobj(audio.file, tmp)
        tmp_path = tmp.name

    result = speech_service.analyze_pronunciation(tmp_path, text, locale=locale)
    return result
