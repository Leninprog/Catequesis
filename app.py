from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from config import MONGO_URI, MONGO_DB
import re
from datetime import datetime
from bson.objectid import ObjectId

def parse_mongo_id(value: str):
    value = value.strip()
    # Si es un ObjectId (24 caracteres hex)
    if re.fullmatch(r"[0-9a-fA-F]{24}", value):
        return ObjectId(value)
    # Si es número (ej: "1")
    if value.isdigit():
        return int(value)
    # Caso general
    return value

app = Flask(__name__)

# Conexión a MongoDB (Atlas)
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]

@app.route("/")
def index():
    stats = {
        "estudiantes": db.estudiantes.count_documents({}),
        "grupos": db.grupos.count_documents({}),
        "inscripciones": db.inscripciones.count_documents({}),
        "asistencias": db.asistencias.count_documents({}),
        "eventos": db.eventos.count_documents({}),
    }

    # Próximos 5 eventos (ordenados por fecha)
    eventos = list(db.eventos.find().sort("fecha_evento", 1).limit(5))

    # Formateo simple de fecha para mostrar
    for ev in eventos:
        f = ev.get("fecha_evento") or ev.get("fechaEvento")
        if isinstance(f, datetime):
            ev["fecha_txt"] = f.strftime("%Y-%m-%d")
        else:
            ev["fecha_txt"] = str(f) if f is not None else "N/A"

    return render_template("index.html", stats=stats, eventos=eventos)

from datetime import datetime

@app.route("/estudiantes/nuevo", methods=["GET", "POST"])
def nuevo_estudiante():
    if request.method == "POST":
        doc = {
            "cedula": request.form.get("cedula"),
            "nombres": request.form.get("nombres"),
            "apellidos": request.form.get("apellidos"),
            "fecha_nacimiento": datetime.strptime(request.form.get("fecha_nacimiento"), "%Y-%m-%d"),
            "direccion": request.form.get("direccion"),
            "representante": {
                "nombre": request.form.get("rep_nombre"),
                "telefono": request.form.get("rep_telefono")
            }
        }

        db.estudiantes.insert_one(doc)
        return redirect(url_for("index"))

    return render_template("registrar_estudiante.html")

@app.route("/inscripciones")
def listar_inscripciones():
    inscripciones = list(db.inscripciones.find().sort("fecha_inscripcion", -1))
    return render_template("listar_inscripciones.html", inscripciones=inscripciones)

@app.route("/estudiantes")
def listar_estudiantes():
    estudiantes = list(db.estudiantes.find().sort("apellidos", 1))
    return render_template("listar_estudiantes.html", estudiantes=estudiantes)

@app.route("/estudiantes/<estudiante_id>")
def detalle_estudiante(estudiante_id):
    _id = parse_mongo_id(estudiante_id)
    e = db.estudiantes.find_one({"_id": _id})

    if not e:
        return {"ok": False, "error": "Estudiante no encontrado"}, 404

    return render_template("detalle_estudiante.html", e=e)

@app.route("/estudiantes/<estudiante_id>/inscribir", methods=["GET", "POST"])
def inscribir_estudiante(estudiante_id):
    est_id = parse_mongo_id(estudiante_id)
    e = db.estudiantes.find_one({"_id": est_id})
    if not e:
        return {"ok": False, "error": "Estudiante no encontrado"}, 404

    # Traer grupos disponibles
    grupos = list(db.grupos.find().sort("nombre_grupo", 1))

    if request.method == "POST":
        grupo_raw = request.form.get("grupo_id")
        grupo_id = parse_mongo_id(grupo_raw)

        g = db.grupos.find_one({"_id": grupo_id})
        if not g:
            return {"ok": False, "error": "Grupo no encontrado"}, 404

        insc = {
            "fecha_inscripcion": datetime.now(),
            "estado": request.form.get("estado", "Activo"),
            "estudiante": {
                "_id": e["_id"],
                "cedula": e.get("cedula"),
                "nombre": f"{e.get('nombres','')} {e.get('apellidos','')}".strip(),
            },
            "grupo": {
                "_id": g["_id"],
                "nombre_grupo": g.get("nombre_grupo") or g.get("nombreGrupo"),
                "horario": g.get("horario"),
                "dia_reunion": g.get("dia_reunion") or g.get("diaReunion"),
            },
        }

        db.inscripciones.insert_one(insc)
        return redirect(url_for("listar_estudiantes"))

    return render_template("inscribir_estudiante.html", e=e, grupos=grupos)

@app.route("/estudiantes/<estudiante_id>/editar", methods=["GET", "POST"])
def editar_estudiante(estudiante_id):
    _id = parse_mongo_id(estudiante_id)
    e = db.estudiantes.find_one({"_id": _id})
    if not e:
        return {"ok": False, "error": "Estudiante no encontrado"}, 404

    # Formatear fecha para input type=date
    fecha_nac = ""
    if e.get("fecha_nacimiento"):
        if isinstance(e["fecha_nacimiento"], datetime):
            fecha_nac = e["fecha_nacimiento"].strftime("%Y-%m-%d")
        else:
            # si por alguna razón viene como string
            try:
                fecha_nac = str(e["fecha_nacimiento"])[:10]
            except:
                fecha_nac = ""

    if request.method == "POST":
        update_doc = {
            "cedula": request.form.get("cedula"),
            "nombres": request.form.get("nombres"),
            "apellidos": request.form.get("apellidos"),
            "fecha_nacimiento": datetime.strptime(request.form.get("fecha_nacimiento"), "%Y-%m-%d"),
            "direccion": request.form.get("direccion"),
            "representante": {
                "nombre": request.form.get("rep_nombre"),
                "telefono": request.form.get("rep_telefono"),
            },
        }

        db.estudiantes.update_one({"_id": _id}, {"$set": update_doc})
        return redirect(url_for("listar_estudiantes"))

    return render_template("editar_estudiante.html", e=e, fecha_nac=fecha_nac)

@app.route("/estudiantes/<estudiante_id>/eliminar", methods=["POST"])
def eliminar_estudiante(estudiante_id):
    _id = parse_mongo_id(estudiante_id)

    # Opcional: borrar inscripciones relacionadas también
    db.inscripciones.delete_many({"estudiante._id": _id})

    db.estudiantes.delete_one({"_id": _id})
    return redirect(url_for("listar_estudiantes"))

@app.route("/inscripciones/<inscripcion_id>/asistencia/nueva", methods=["GET", "POST"])
def nueva_asistencia(inscripcion_id):
    insc_id = parse_mongo_id(inscripcion_id)
    insc = db.inscripciones.find_one({"_id": insc_id})
    if not insc:
        return {"ok": False, "error": "Inscripción no encontrada"}, 404

    if request.method == "POST":
        asistencia_doc = {
            "fecha_sesion": datetime.now(),
            "estado": request.form.get("estado", "Presente"),
            "inscripcion": {
                "_id": insc["_id"],
                "estudiante": insc.get("estudiante", {}),
                "grupo": insc.get("grupo", {}),
            },
        }
        db.asistencias.insert_one(asistencia_doc)
        return redirect(url_for("listar_inscripciones"))

    return render_template("registrar_asistencia.html", insc=insc)

@app.route("/asistencias")
def listar_asistencias():
    raw = list(db.asistencias.find().sort("fecha_sesion", -1))
    asistencias = []

    for a in raw:
        insc = a.get("inscripcion", {})
        if not isinstance(insc, dict):
            insc = {}

        est = insc.get("estudiante", {})
        if not isinstance(est, dict):
            est = {}

        grp = insc.get("grupo", {})
        if not isinstance(grp, dict):
            grp = {}

        # Campos seguros para la vista
        a["estudiante_nombre"] = est.get("nombre") or "N/A"
        a["grupo_nombre"] = grp.get("nombre_grupo") or grp.get("nombreGrupo") or "N/A"

        # Fecha segura/formateada
        f = a.get("fecha_sesion")
        if isinstance(f, datetime):
            a["fecha_sesion_txt"] = f.strftime("%Y-%m-%d %H:%M")
        else:
            a["fecha_sesion_txt"] = str(f) if f is not None else "N/A"

        asistencias.append(a)

    return render_template("listar_asistencias.html", asistencias=asistencias)

@app.route("/asistencias/<asistencia_id>/editar", methods=["GET", "POST"])
def editar_asistencia(asistencia_id):
    a_id = parse_mongo_id(asistencia_id)
    a = db.asistencias.find_one({"_id": a_id})
    if not a:
        return {"ok": False, "error": "Asistencia no encontrada"}, 404

    # Normalizar para mostrar (mismo patrón que listar_asistencias)
    insc = a.get("inscripcion", {})
    if not isinstance(insc, dict):
        insc = {}

    est = insc.get("estudiante", {})
    if not isinstance(est, dict):
        est = {}

    grp = insc.get("grupo", {})
    if not isinstance(grp, dict):
        grp = {}

    a["estudiante_nombre"] = est.get("nombre") or "N/A"
    a["grupo_nombre"] = grp.get("nombre_grupo") or grp.get("nombreGrupo") or "N/A"

    f = a.get("fecha_sesion")
    if isinstance(f, datetime):
        a["fecha_sesion_txt"] = f.strftime("%Y-%m-%d %H:%M")
    else:
        a["fecha_sesion_txt"] = str(f) if f is not None else "N/A"

    if request.method == "POST":
        nuevo_estado = request.form.get("estado", "Presente")
        db.asistencias.update_one({"_id": a_id}, {"$set": {"estado": nuevo_estado}})
        return redirect(url_for("listar_asistencias"))

    return render_template("editar_asistencia.html", a=a)

@app.route("/asistencias/<asistencia_id>/eliminar", methods=["POST"])
def eliminar_asistencia(asistencia_id):
    a_id = parse_mongo_id(asistencia_id)
    db.asistencias.delete_one({"_id": a_id})
    return redirect(url_for("listar_asistencias"))

@app.route("/grupos")
def listar_grupos():
    grupos = list(db.grupos.find())
    # Orden seguro
    grupos.sort(key=lambda g: (g.get("nombre_grupo") or g.get("nombreGrupo") or ""))
    return render_template("listar_grupos.html", grupos=grupos)


@app.route("/grupos/nuevo", methods=["GET", "POST"])
def nuevo_grupo():
    if request.method == "POST":
        doc = {
            "nombre_grupo": request.form.get("nombre_grupo"),
            "horario": request.form.get("horario"),
            "dia_reunion": request.form.get("dia_reunion"),
            "estado": request.form.get("estado", "Activo"),
            # opcional: parroquia/catequista/nivel si quieres después
        }
        db.grupos.insert_one(doc)
        return redirect(url_for("listar_grupos"))

    return render_template("nuevo_grupo.html")


@app.route("/grupos/<grupo_id>/editar", methods=["GET", "POST"])
def editar_grupo(grupo_id):
    g_id = parse_mongo_id(grupo_id)
    g = db.grupos.find_one({"_id": g_id})
    if not g:
        return {"ok": False, "error": "Grupo no encontrado"}, 404

    if request.method == "POST":
        update_doc = {
            "nombre_grupo": request.form.get("nombre_grupo"),
            "horario": request.form.get("horario"),
            "dia_reunion": request.form.get("dia_reunion"),
            "estado": request.form.get("estado", "Activo"),
        }
        db.grupos.update_one({"_id": g_id}, {"$set": update_doc})
        return redirect(url_for("listar_grupos"))

    return render_template("editar_grupo.html", g=g)

@app.route("/grupos/<grupo_id>/eliminar", methods=["POST"])
def eliminar_grupo(grupo_id):
    g_id = parse_mongo_id(grupo_id)

    # Opcional: borrar inscripciones de ese grupo para que no queden huérfanas
    db.inscripciones.delete_many({"grupo._id": g_id})

    db.grupos.delete_one({"_id": g_id})
    return redirect(url_for("listar_grupos"))

@app.route("/eventos")
def listar_eventos():
    eventos = list(db.eventos.find())
    eventos.sort(key=lambda e: e.get("fecha_evento") or e.get("fechaEvento") or datetime.min)
    return render_template("listar_eventos.html", eventos=eventos)


@app.route("/eventos/nuevo", methods=["GET", "POST"])
def nuevo_evento():
    if request.method == "POST":
        doc = {
            "nombre_evento": request.form.get("nombre_evento"),
            "descripcion": request.form.get("descripcion"),
            "fecha_evento": datetime.strptime(request.form.get("fecha_evento"), "%Y-%m-%d"),
            "parroquia": {
                "idParroquia": int(request.form.get("parroquia_id") or 1),
                "nombreParroquia": request.form.get("parroquia_nombre") or "San José"
            }
        }
        db.eventos.insert_one(doc)
        return redirect(url_for("listar_eventos"))

    return render_template("nuevo_evento.html")


@app.route("/eventos/<evento_id>/editar", methods=["GET", "POST"])
def editar_evento(evento_id):
    ev_id = parse_mongo_id(evento_id)
    e = db.eventos.find_one({"_id": ev_id})
    if not e:
        return {"ok": False, "error": "Evento no encontrado"}, 404

    # fecha para input date
    fecha_txt = ""
    f = e.get("fecha_evento") or e.get("fechaEvento")
    if isinstance(f, datetime):
        fecha_txt = f.strftime("%Y-%m-%d")
    elif isinstance(f, str):
        fecha_txt = f[:10]

    if request.method == "POST":
        update_doc = {
            "nombre_evento": request.form.get("nombre_evento"),
            "descripcion": request.form.get("descripcion"),
            "fecha_evento": datetime.strptime(request.form.get("fecha_evento"), "%Y-%m-%d"),
            "parroquia": {
                "idParroquia": int(request.form.get("parroquia_id") or 1),
                "nombreParroquia": request.form.get("parroquia_nombre") or "San José"
            }
        }
        db.eventos.update_one({"_id": ev_id}, {"$set": update_doc})
        return redirect(url_for("listar_eventos"))

    return render_template("editar_evento.html", e=e, fecha_txt=fecha_txt)

@app.route("/eventos/<evento_id>/eliminar", methods=["POST"])
def eliminar_evento(evento_id):
    ev_id = parse_mongo_id(evento_id)
    db.eventos.delete_one({"_id": ev_id})
    return redirect(url_for("listar_eventos"))

@app.route("/ping")
def ping():
    # Prueba rápida de conexión: lista colecciones
    colecciones = db.list_collection_names()
    return {"ok": True, "db": MONGO_DB, "colecciones": colecciones}

if __name__ == "__main__":
    app.run(debug=True)
