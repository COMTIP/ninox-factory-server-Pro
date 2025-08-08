from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
import zeep
import base64
import tempfile
import os

app = FastAPI()

# === DATOS DEL WS Y CREDENCIALES ===
wsdl = 'https://demoemision.thefactoryhka.com.pa/ws/obj/v1.0/Service.svc?singleWsdl'
TOKEN_EMPRESA = "hqavyydgygrn_tfhka"
TOKEN_PASSWORD = "@&Si-&7m/,dy"

@app.post("/enviar-factura")
async def enviar_factura(request: Request):
    datos = await request.json()
    datos['tokenEmpresa'] = TOKEN_EMPRESA
    datos['tokenPassword'] = TOKEN_PASSWORD
    try:
        cliente = zeep.Client(wsdl=wsdl)
        res = cliente.service.Enviar(**datos)
        print("RESPUESTA REAL DEL WEBSERVICE:", res)
        return JSONResponse({"ok": True, "respuesta": res, "uuid": getattr(res, "uuid", None)})
    except Exception as e:
        print("ERROR:", e)
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@app.post("/descargar-pdf")
async def descargar_pdf(request: Request):
    body = await request.json()

    # Si viene UUID directo
    if "uuid" in body:
        datos = {
            "tokenEmpresa": TOKEN_EMPRESA,
            "tokenPassword": TOKEN_PASSWORD,
            "uuid": body["uuid"]
        }
        try:
            cliente = zeep.Client(wsdl=wsdl)
            res = cliente.service.DescargaPDF(**datos)
            print("RESPUESTA DescargaPDF (UUID):", res)
            pdf_base64 = res.get('archivoPDF') or res.get('pdf') or None
            if not pdf_base64:
                return JSONResponse({"error": "No se recibió archivo PDF.", "detalle": res}, status_code=404)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(base64.b64decode(pdf_base64))
                tmp_path = tmp.name
            return FileResponse(tmp_path, media_type='application/pdf', filename="factura_dgi.pdf")
        except Exception as e:
            print("ERROR EN PDF (UUID):", e)
            return JSONResponse({"error": str(e)}, status_code=500)

    # Si viene datosDocumento (por número)
    datos_documento = body.get("datosDocumento", body)
    datos = {
        "tokenEmpresa": TOKEN_EMPRESA,
        "tokenPassword": TOKEN_PASSWORD,
        "datosDocumento": {
            "codigoSucursalEmisor": datos_documento.get("codigoSucursalEmisor", "0000"),
            "numeroDocumentoFiscal": datos_documento.get("numeroDocumentoFiscal"),
            "puntoFacturacionFiscal": datos_documento.get("puntoFacturacionFiscal", "001"),
            "tipoDocumento": datos_documento.get("tipoDocumento", "01"),
            "tipoEmision": datos_documento.get("tipoEmision", "01"),
            "serialDispositivo": datos_documento.get("serialDispositivo", "")
        }
    }
    try:
        cliente = zeep.Client(wsdl=wsdl)
        res = cliente.service.DescargaPDF(**datos)
        print("RESPUESTA DescargaPDF (NÚMERO):", res)
        pdf_base64 = res.get('archivoPDF') or res.get('pdf') or None
        if not pdf_base64:
            return JSONResponse({"error": "No se recibió archivo PDF.", "detalle": res}, status_code=404)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(base64.b64decode(pdf_base64))
            tmp_path = tmp.name
        return FileResponse(tmp_path, media_type='application/pdf', filename="factura_dgi.pdf")
    except Exception as e:
        print("ERROR EN PDF (NÚMERO):", e)
        return JSONResponse({"error": str(e)}, status_code=500)









