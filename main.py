# app.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os, base64, tempfile
import zeep
from zeep.helpers import serialize_object

# ========= CONFIG =========
# Usa env vars si existen; si no, usa los valores por defecto que pasaste
WSDL = os.getenv(
    "THEFACTORY_WSDL",
    "https://demoemision.thefactoryhka.com.pa/ws/obj/v1.0/Service.svc?singleWsdl"
)
TOKEN_EMPRESA  = os.getenv("THEFACTORY_TOKEN_EMPRESA") or "hqavyydgygrn_tfhka"
TOKEN_PASSWORD = os.getenv("THEFACTORY_TOKEN_PASSWORD") or "@&Si-&7m/,dy"

# Reusar el cliente SOAP
soap_client = zeep.Client(wsdl=WSDL)

app = FastAPI(title="Ninox-TheFactory Bridge")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en prod: pon tu dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========= HELPERS =========
def to_dict(res):
    try:
        return serialize_object(res)
    except Exception:
        try:
            return dict(res)
        except Exception:
            return {"raw": str(res)}

def extract_uuid(d):
    """Intenta encontrar uuid/claveAcceso/idTransaccion en cualquier parte de la respuesta."""
    if not isinstance(d, dict):
        return None
    keys = ["uuid","UUID","claveAcceso","cufe","CUFE","idTransaccion","id","claveAutorizacion","clave"]
    for k in keys:
        if k in d and d[k]:
            return d[k]
    for v in d.values():
        if isinstance(v, dict):
            got = extract_uuid(v)
            if got: return got
        elif isinstance(v, list):
            for it in v:
                if isinstance(it, dict):
                    got = extract_uuid(it)
                    if got: return got
    return None

def decode_pdf_from_response(res_dict):
    """Busca el PDF en base64 en llaves comunes."""
    keys = ["archivoPDF","archivo","pdf","documento","contenido","ArchivoPDF","Archivo","PDF"]
    for k in keys:
        if k in res_dict and res_dict[k]:
            return res_dict[k]
    for v in res_dict.values():
        if isinstance(v, dict):
            got = decode_pdf_from_response(v)
            if got: return got
    return None

# ========= ENDPOINTS =========
@app.post("/enviar-factura")
async def enviar_factura(request: Request):
    """
    Espera: {"documento": {...}} (estructura de TheFactory)
    Devuelve: {"ok": True, "respuesta": <dict>, "uuid": "<id o clave>"}
    """
    body = await request.json()
    doc = body.get("documento")
    if not doc:
        return JSONResponse({"ok": False, "error": "Falta 'documento' en payload"}, status_code=400)
    try:
        res = soap_client.service.Enviar(
            tokenEmpresa=TOKEN_EMPRESA,
            tokenPassword=TOKEN_PASSWORD,
            documento=doc
        )
        res_dict = to_dict(res)
        uid = extract_uuid(res_dict)
        return JSONResponse({"ok": True, "respuesta": res_dict, "uuid": uid})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/descargar-pdf")
async def descargar_pdf(request: Request):
    """
    Modo 1 (preferido): por UUID
      Payload: {"uuid":"...", "documento":{"tipoDocumento":"01"}}

    Modo 2 (fallback): por número de documento
      Payload: {"datosDocumento":{
                  "codigoSucursalEmisor":"0000",
                  "numeroDocumentoFiscal":"00000001",
                  "puntoFacturacionFiscal":"001",
                  "tipoDocumento":"01",
                  "tipoEmision":"01",
                  "serialDispositivo":""
               }}
    """
    body = await request.json()

    # 1) Por UUID
    uuid = body.get("uuid") or body.get("claveAcceso") or body.get("idTransaccion")
    if uuid:
        tipo_doc = body.get("documento", {}).get("tipoDocumento", "01")
        try:
            # Algunos WSDL usan Descargar; otros, ObtenerCAFE
            try:
                res = soap_client.service.Descargar(
                    tokenEmpresa=TOKEN_EMPRESA,
                    tokenPassword=TOKEN_PASSWORD,
                    uuid=uuid,
                    tipoDocumento=tipo_doc,
                    formato="PDF"
                )
            except Exception:
                res = soap_client.service.ObtenerCAFE(
                    tokenEmpresa=TOKEN_EMPRESA,
                    tokenPassword=TOKEN_PASSWORD,
                    uuid=uuid,
                    tipoDocumento=tipo_doc,
                    formato="PDF"
                )
            res_dict = to_dict(res)
            pdf_b64 = decode_pdf_from_response(res_dict)
            if not pdf_b64:
                return JSONResponse({"error": "El servicio no devolvió PDF", "respuesta": res_dict}, status_code=502)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(base64.b64decode(pdf_b64))
                path = tmp.name
            return FileResponse(path, media_type="application/pdf", filename=f"factura_{uuid}.pdf")
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    # 2) Por número de documento (DescargaPDF / DescargarPDF)
    d = body.get("datosDocumento", body)
    numero = d.get("numeroDocumentoFiscal")
    if not numero:
        return JSONResponse({"error": "Falta 'uuid' o 'datosDocumento.numeroDocumentoFiscal'"}, status_code=400)

    datos = {
        "tokenEmpresa": TOKEN_EMPRESA,
        "tokenPassword": TOKEN_PASSWORD,
        "datosDocumento": {
            "codigoSucursalEmisor": d.get("codigoSucursalEmisor", "0000"),
            "numeroDocumentoFiscal": numero,
            "puntoFacturacionFiscal": d.get("puntoFacturacionFiscal", "001"),
            "tipoDocumento": d.get("tipoDocumento", "01"),
            "tipoEmision": d.get("tipoEmision", "01"),
            "serialDispositivo": d.get("serialDispositivo", "")
        }
    }
    try:
        # Algunos WSDL lo tienen como DescargaPDF (sin 'r'), otros DescargarPDF
        try:
            res = soap_client.service.DescargaPDF(**datos)
        except Exception:
            res = soap_client.service.DescargarPDF(**datos)

        res_dict = to_dict(res)
        pdf_b64 = decode_pdf_from_response(res_dict)
        if not pdf_b64:
            return JSONResponse({"error": "No se recibió archivo PDF", "detalle_respuesta": res_dict}, status_code=404)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(base64.b64decode(pdf_b64))
            path = tmp.name
        return FileResponse(path, media_type="application/pdf", filename=f"factura_{numero}.pdf")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/")
def health():
    return {"status": "ok"}

# Ejecutar local: uvicorn app:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))








