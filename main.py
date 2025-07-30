from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import zeep

app = FastAPI()

# WSDL de The Factory HKA
wsdl = 'https://demoemision.thefactoryhka.com.pa/ws/obj/v1.0/Service.svc?singleWsdl'

@app.post("/enviar-factura")
async def enviar_factura(request: Request):
    datos = await request.json()
    # Agregar tokens obligatorios
    datos['tokenEmpresa'] = "hqavyygdygrn_tfhka"  # Token real
    datos['tokenPassword'] = "@&Si-&7m/,dy"       # Password real
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
    # Asegurar que se incluyan los tokens
    datos['tokenEmpresa'] = "hqavyygdygrn_tfhka"
    datos['tokenPassword'] = "@&Si-&7m/,dy"
    try:
        cliente = zeep.Client(wsdl=wsdl)
        res = cliente.service.DescargaPDF(**datos)
        print("RESPUESTA DESCARGA PDF:", res)
        return JSONResponse({"respuesta": str(res)})
    except Exception as e:
        print("ERROR:", e)
        return JSONResponse({"error": str(e)}, status_code=500)
