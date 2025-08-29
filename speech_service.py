import os, json, time, threading
import azure.cognitiveservices.speech as speechsdk

def map_to_cefr(scores: dict) -> dict:
    overall = (
        0.35 * scores.get("PronScore", 0) +
        0.25 * scores.get("Accuracy", 0) +
        0.20 * scores.get("Fluency", 0) +
        0.10 * scores.get("Completeness", 0) +
        0.10 * scores.get("Prosody", 0)
    )
    if overall < 45:
        level = "A2"
    elif overall < 60:
        level = "B1"
    elif overall < 75:
        level = "B2"
    elif overall < 88:
        level = "C1"
    else:
        level = "C2"
    return {"overall_score": round(overall, 2), "level": level}

def parse_pa_from_json(raw_json: str):
    data = json.loads(raw_json) if raw_json else {}
    nbest = (data.get("NBest") or [{}])
    top = nbest[0] if nbest else {}
    pa = top.get("PronunciationAssessment") or {}
    words = top.get("Words") or []
    return {
        "PronScore": pa.get("PronScore"),
        "Accuracy": pa.get("AccuracyScore"),
        "Fluency": pa.get("FluencyScore"),
        "Completeness": pa.get("CompletenessScore"),
        "Prosody": pa.get("ProsodyScore"),
        "Words": words,
        "Text": top.get("Display") or top.get("Lexical") or "",
        "Raw": data,
    }

def analyze_pronunciation(audio_path: str, reference_text: str, locale="en-US", miscue=True):
    key = os.getenv("SPEECH_KEY")
    region = os.getenv("SPEECH_REGION")
    if not key or not region:
        raise RuntimeError("SPEECH_KEY and SPEECH_REGION env vars must be set")

    speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
    speech_config.request_word_level_timestamps()
    speech_config.set_property(
        speechsdk.PropertyId.SpeechServiceResponse_RequestDetailedResultTrueFalse, "true"
    )

    audio_config = speechsdk.AudioConfig(filename=audio_path)
    recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, language=locale, audio_config=audio_config
    )

    pa_cfg = speechsdk.PronunciationAssessmentConfig(
        reference_text=reference_text,
        grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
        granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
        enable_miscue=miscue
    )
    pa_cfg.enable_prosody_assessment()
    pa_cfg.apply_to(recognizer)

    done = threading.Event()
    sums = {"PronScore":0,"Accuracy":0,"Fluency":0,"Completeness":0,"Prosody":0}
    total_weight = 0
    segments = []

    def on_recognized(evt):
        nonlocal total_weight
        res = evt.result
        if res.reason != speechsdk.ResultReason.RecognizedSpeech:
            return
        raw = res.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult) or "{}"
        pa = parse_pa_from_json(raw)
        # duration ticks to seconds
        dur = getattr(res, "duration", None)
        seg_dur = float(dur)/10_000_000 if dur else max(1.0, len(pa["Words"]))
        weight = seg_dur
        for k in sums:
            if isinstance(pa.get(k), (int,float)):
                sums[k] += pa[k]*weight
        total_weight += weight
        segments.append(pa)

    recognizer.recognized.connect(on_recognized)
    recognizer.session_stopped.connect(lambda evt: done.set())
    recognizer.canceled.connect(lambda evt: done.set())

    recognizer.start_continuous_recognition()
    while not done.is_set():
        time.sleep(0.1)
    recognizer.stop_continuous_recognition()

    if total_weight == 0:
        return {"error":"No speech recognized."}

    agg = {k: round(sums[k]/total_weight,2) for k in sums}
    cefr = map_to_cefr(agg)
    return {"aggregate_scores": agg, "cefr_result": cefr} # if you want detail analize add , "segments": segments
