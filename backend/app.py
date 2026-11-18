"""ReMINDer - Prova de Conceito (backend).

API REST em Flask + SQLite que sustenta a jornada principal do projeto:
planejar a atividade -> alarme persistente -> informar realizada ou reajustar.

O servidor também entrega o frontend (pasta ../frontend), então um único
comando sobe tudo: `python backend/app.py`.
"""
import os
import sqlite3
from datetime import datetime, timedelta

from flask import Flask, current_app, g, jsonify, request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONT_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")
DEFAULT_DB = os.path.join(BASE_DIR, "reminder.db")

FMT_DATA = "%Y-%m-%d"
FMT_HORA = "%H:%M"
FMT_TS = "%Y-%m-%dT%H:%M:%S"


class ApiError(Exception):
    def __init__(self, mensagem, status=400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


# --------------------------------------------------------------------------
# Utilidades
# --------------------------------------------------------------------------
def agora():
    """Horário atual (injetável para testes via app.config['CLOCK'])."""
    return current_app.config["CLOCK"]().replace(microsecond=0)


def ts(dt):
    return dt.strftime(FMT_TS)


def parse_data(valor):
    try:
        return datetime.strptime(valor, FMT_DATA).strftime(FMT_DATA)
    except (TypeError, ValueError):
        raise ApiError("Data inválida. Use o formato AAAA-MM-DD.")


def parse_hora(valor):
    try:
        return datetime.strptime(valor, FMT_HORA).strftime(FMT_HORA)
    except (TypeError, ValueError):
        raise ApiError("Horário inválido. Use o formato HH:MM.")


def parse_int(valor, nome, minimo, maximo):
    if isinstance(valor, bool) or not isinstance(valor, int):
        raise ApiError(f"'{nome}' deve ser um número inteiro.")
    if not minimo <= valor <= maximo:
        raise ApiError(f"'{nome}' deve estar entre {minimo} e {maximo}.")
    return valor


def parse_titulo(valor):
    if not isinstance(valor, str) or not valor.strip():
        raise ApiError("Informe o nome da atividade.")
    valor = valor.strip()
    if len(valor) > 100:
        raise ApiError("O nome da atividade deve ter no máximo 100 caracteres.")
    return valor


def corpo_json():
    dados = request.get_json(silent=True)
    if dados is None:
        return {}
    if not isinstance(dados, dict):
        raise ApiError("Corpo da requisição inválido.")
    return dados


def inicio_dt(row):
    return datetime.strptime(f"{row['data']} {row['hora_inicio']}", f"{FMT_DATA} {FMT_HORA}")


def fim_dt(row):
    return inicio_dt(row) + timedelta(minutes=row["duracao_min"])


def alarme_ativo(row, now):
    """Regra central do produto: o alarme toca a partir do início e só para
    quando a atividade é informada como realizada (ou enquanto está pausado
    por um acréscimo de tempo)."""
    if row["status"] != "agendada" or not row["neurofeedback"]:
        return False
    if now < inicio_dt(row):
        return False
    if row["silenciado_ate"] and now < datetime.strptime(row["silenciado_ate"], FMT_TS):
        return False
    return True


def ids_em_conflito(rows):
    """Atividades agendadas do mesmo dia cujos horários se sobrepõem."""
    abertas = sorted((r for r in rows if r["status"] == "agendada"), key=inicio_dt)
    conflitos = set()
    for anterior, atual in zip(abertas, abertas[1:]):
        if inicio_dt(atual) < fim_dt(anterior):
            conflitos.update({anterior["id"], atual["id"]})
    return conflitos


def serializar(row, now, conflitos=frozenset()):
    ini, fim = inicio_dt(row), fim_dt(row)
    aberta = row["status"] == "agendada"
    return {
        "id": row["id"],
        "titulo": row["titulo"],
        "data": row["data"],
        "hora_inicio": row["hora_inicio"],
        "hora_fim": fim.strftime(FMT_HORA),
        "duracao_min": row["duracao_min"],
        "neurofeedback": bool(row["neurofeedback"]),
        "intervalo_seg": row["intervalo_seg"],
        "status": row["status"],
        "concluida_em": row["concluida_em"],
        "alarme_ativo": alarme_ativo(row, now),
        "decorrido_seg": max(0, int((now - ini).total_seconds())) if aberta else 0,
        "excedido_seg": max(0, int((now - fim).total_seconds())) if aberta else 0,
        "conflito": row["id"] in conflitos,
    }


# --------------------------------------------------------------------------
# Banco de dados
# --------------------------------------------------------------------------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DB_PATH"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def init_db(db_path):
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        conn = sqlite3.connect(db_path)
        conn.executescript(f.read())
        conn.commit()
        conn.close()


def buscar_tarefa(tarefa_id):
    row = get_db().execute("SELECT * FROM tarefas WHERE id = ?", (tarefa_id,)).fetchone()
    if row is None:
        raise ApiError("Atividade não encontrada.", 404)
    return row


def registrar_evento(tarefa_id, tipo, detalhe=None):
    get_db().execute(
        "INSERT INTO eventos (tarefa_id, tipo, detalhe, criado_em) VALUES (?, ?, ?, ?)",
        (tarefa_id, tipo, detalhe, ts(agora())),
    )


def resposta_tarefa(tarefa_id, status=200):
    """Devolve a tarefa já com o flag de conflito calculado para o dia dela."""
    row = buscar_tarefa(tarefa_id)
    do_dia = get_db().execute("SELECT * FROM tarefas WHERE data = ?", (row["data"],)).fetchall()
    return jsonify(serializar(row, agora(), ids_em_conflito(do_dia))), status


# --------------------------------------------------------------------------
# Aplicação
# --------------------------------------------------------------------------
def create_app(db_path=None, clock=None):
    app = Flask(__name__, static_folder=FRONT_DIR, static_url_path="")
    app.config["DB_PATH"] = db_path or os.environ.get("REMINDER_DB", DEFAULT_DB)
    app.config["CLOCK"] = clock or datetime.now
    init_db(app.config["DB_PATH"])

    @app.teardown_appcontext
    def fechar_db(_erro):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.errorhandler(ApiError)
    def erro_api(e):
        return jsonify({"erro": e.mensagem}), e.status

    @app.errorhandler(404)
    def nao_encontrado(_e):
        if request.path.startswith("/api/"):
            return jsonify({"erro": "Rota não encontrada."}), 404
        return "Não encontrado", 404

    @app.get("/")
    def index():
        return app.send_static_file("index.html")

    # ---- Saúde ----------------------------------------------------------
    @app.get("/api/saude")
    def saude():
        return jsonify({"status": "ok", "agora": ts(agora())})

    # ---- CRUD de atividades --------------------------------------------
    @app.get("/api/tarefas")
    def listar():
        data = parse_data(request.args.get("data") or agora().strftime(FMT_DATA))
        rows = get_db().execute(
            "SELECT * FROM tarefas WHERE data = ? ORDER BY hora_inicio, id", (data,)
        ).fetchall()
        conflitos = ids_em_conflito(rows)
        now = agora()
        return jsonify({"data": data, "tarefas": [serializar(r, now, conflitos) for r in rows]})

    @app.post("/api/tarefas")
    def criar():
        d = corpo_json()
        titulo = parse_titulo(d.get("titulo"))
        data = parse_data(d.get("data"))
        hora = parse_hora(d.get("hora_inicio"))
        duracao = parse_int(d.get("duracao_min", 30), "duracao_min", 5, 720)
        intervalo = parse_int(d.get("intervalo_seg", 30), "intervalo_seg", 5, 600)
        neuro = 1 if d.get("neurofeedback", True) else 0

        db = get_db()
        cur = db.execute(
            "INSERT INTO tarefas (titulo, data, hora_inicio, duracao_min, neurofeedback,"
            " intervalo_seg, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (titulo, data, hora, duracao, neuro, intervalo, ts(agora())),
        )
        registrar_evento(cur.lastrowid, "criada", f"{data} {hora}, {duracao} min")
        db.commit()
        return resposta_tarefa(cur.lastrowid, 201)

    @app.get("/api/tarefas/<int:tarefa_id>")
    def detalhar(tarefa_id):
        return resposta_tarefa(tarefa_id)

    @app.patch("/api/tarefas/<int:tarefa_id>")
    def editar(tarefa_id):
        row = buscar_tarefa(tarefa_id)
        d = corpo_json()
        campos = {}
        if "titulo" in d:
            campos["titulo"] = parse_titulo(d["titulo"])
        if "duracao_min" in d:
            campos["duracao_min"] = parse_int(d["duracao_min"], "duracao_min", 5, 720)
        if "intervalo_seg" in d:
            campos["intervalo_seg"] = parse_int(d["intervalo_seg"], "intervalo_seg", 5, 600)
        if "neurofeedback" in d:
            campos["neurofeedback"] = 1 if d["neurofeedback"] else 0
        if not campos:
            raise ApiError("Nenhum campo para atualizar.")
        sets = ", ".join(f"{c} = ?" for c in campos)
        db = get_db()
        db.execute(f"UPDATE tarefas SET {sets} WHERE id = ?", (*campos.values(), row["id"]))
        registrar_evento(row["id"], "editada", ", ".join(campos))
        db.commit()
        return resposta_tarefa(row["id"])

    @app.delete("/api/tarefas/<int:tarefa_id>")
    def excluir(tarefa_id):
        buscar_tarefa(tarefa_id)
        db = get_db()
        db.execute("DELETE FROM tarefas WHERE id = ?", (tarefa_id,))
        db.commit()
        return jsonify({"ok": True})

    # ---- Jornada: alarme, conclusão e reajuste -------------------------
    @app.get("/api/alarme/ativo")
    def alarme_em_curso():
        """O frontend consulta este endpoint em intervalos curtos. Como a regra
        mora no servidor, o alarme continua ativo mesmo se a página for
        recarregada ou aberta em outro aparelho."""
        now = agora()
        rows = get_db().execute(
            "SELECT * FROM tarefas WHERE status = 'agendada' AND neurofeedback = 1"
        ).fetchall()
        ativos = sorted((r for r in rows if alarme_ativo(r, now)), key=inicio_dt)
        if not ativos:
            return jsonify({"alarme": None, "total_ativos": 0, "agora": ts(now)})
        return jsonify(
            {"alarme": serializar(ativos[0], now), "total_ativos": len(ativos), "agora": ts(now)}
        )

    @app.post("/api/tarefas/<int:tarefa_id>/concluir")
    def concluir(tarefa_id):
        row = buscar_tarefa(tarefa_id)
        if row["status"] == "agendada":
            db = get_db()
            db.execute(
                "UPDATE tarefas SET status = 'concluida', concluida_em = ?, silenciado_ate = NULL"
                " WHERE id = ?",
                (ts(agora()), tarefa_id),
            )
            registrar_evento(tarefa_id, "concluida")
            db.commit()
        return resposta_tarefa(tarefa_id)

    @app.post("/api/tarefas/<int:tarefa_id>/estender")
    def estender(tarefa_id):
        """Acrescenta tempo à atividade (+10, +15, +30 min...). O alarme fica
        pausado pelo tempo acrescentado e volta a tocar depois dele."""
        row = buscar_tarefa(tarefa_id)
        if row["status"] != "agendada":
            raise ApiError("Esta atividade já foi concluída.", 409)
        minutos = parse_int(corpo_json().get("minutos"), "minutos", 5, 240)
        nova_duracao = row["duracao_min"] + minutos
        if nova_duracao > 1440:
            raise ApiError("A duração total não pode passar de 24 horas.")
        db = get_db()
        db.execute(
            "UPDATE tarefas SET duracao_min = ?, silenciado_ate = ? WHERE id = ?",
            (nova_duracao, ts(agora() + timedelta(minutes=minutos)), tarefa_id),
        )
        registrar_evento(tarefa_id, "estendida", f"+{minutos} min (total {nova_duracao} min)")
        db.commit()
        return resposta_tarefa(tarefa_id)

    @app.post("/api/tarefas/<int:tarefa_id>/reagendar")
    def reagendar(tarefa_id):
        row = buscar_tarefa(tarefa_id)
        if row["status"] != "agendada":
            raise ApiError("Esta atividade já foi concluída.", 409)
        d = corpo_json()
        data = parse_data(d.get("data") or row["data"])
        hora = parse_hora(d.get("hora_inicio"))
        novo_inicio = datetime.strptime(f"{data} {hora}", f"{FMT_DATA} {FMT_HORA}")
        if novo_inicio <= agora():
            raise ApiError("O novo horário precisa ser no futuro.")
        db = get_db()
        db.execute(
            "UPDATE tarefas SET data = ?, hora_inicio = ?, silenciado_ate = NULL WHERE id = ?",
            (data, hora, tarefa_id),
        )
        registrar_evento(tarefa_id, "reagendada", f"{row['data']} {row['hora_inicio']} -> {data} {hora}")
        db.commit()
        return resposta_tarefa(tarefa_id)

    @app.post("/api/tarefas/<int:tarefa_id>/disparar-agora")
    def disparar_agora(tarefa_id):
        """Atalho de DEMONSTRAÇÃO: move o início da atividade para agora, para
        mostrar o alarme sem esperar o horário real."""
        row = buscar_tarefa(tarefa_id)
        if row["status"] != "agendada":
            raise ApiError("Esta atividade já foi concluída.", 409)
        now = agora()
        db = get_db()
        db.execute(
            "UPDATE tarefas SET data = ?, hora_inicio = ?, silenciado_ate = NULL WHERE id = ?",
            (now.strftime(FMT_DATA), now.strftime(FMT_HORA), tarefa_id),
        )
        registrar_evento(tarefa_id, "disparo_demo")
        db.commit()
        return resposta_tarefa(tarefa_id)

    @app.get("/api/tarefas/<int:tarefa_id>/eventos")
    def eventos(tarefa_id):
        buscar_tarefa(tarefa_id)
        rows = get_db().execute(
            "SELECT tipo, detalhe, criado_em FROM eventos WHERE tarefa_id = ? ORDER BY id",
            (tarefa_id,),
        ).fetchall()
        return jsonify({"eventos": [dict(r) for r in rows]})

    return app


if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 8000))
    print(f"ReMINDer rodando em http://localhost:{porta}")
    create_app().run(host="127.0.0.1", port=porta, debug=False)
