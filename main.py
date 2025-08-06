from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
import zeep
import base64
import os

app = FastAPI()

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
        return JSONResponse({"respuesta": str(res)})
    except Exception as e:
        print("ERROR:", e)
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/descargar-pdf")
async def descargar_pdf(request: Request):
    datos = await request.json()
    datos['tokenEmpresa'] = TOKEN_EMPRESA
    datos['tokenPassword'] = TOKEN_PASSWORD
    try:
        cliente = zeep.Client(wsdl=wsdl)
        res = cliente.service.DescargaPDF(**datos)
        print("RESPUESTA DescargaPDF:", res)
        pdf_base64 = res.get('archivoPDF') or res.get('pdf') or None
        if not pdf_base64:
            return JSONResponse(
                {
                    "error": "No se recibió archivo PDF.",
                    "detalle_respuesta": res
                },
                status_code=404
            )
        filename = "factura_dgi.pdf"
        with open(filename, "wb") as f:
            f.write(base64.b64decode(pdf_base64))
        return FileResponse(filename, media_type='application/pdf', filename=filename)
    except Exception as e:
        print("ERROR EN PDF:", e)
        return JSONResponse({"error": str(e)}, status_code=500)






