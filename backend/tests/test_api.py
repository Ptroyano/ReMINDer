"""Testes automatizados da API do ReMINDer (rodam com um relógio falso)."""
import os
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app  # noqa: E402


class RelogioFalso:
    def __init__(self, inicio):
        self.agora = inicio

    def __call__(self):
        return self.agora

    def avancar(self, **kwargs):
        self.agora += timedelta(**kwargs)


@pytest.fixture
def relogio():
    # Noite anterior: 20/11/2026 às 21:00
    return RelogioFalso(datetime(2026, 11, 20, 21, 0, 0))


@pytest.fixture
def client(tmp_path, relogio):
    app = create_app(db_path=str(tmp_path / "teste.db"), clock=relogio)
    app.config["TESTING"] = True
    return app.test_client()


def criar(client, titulo="Estudar Algoritmos", data="2026-11-21", hora="09:00", duracao=90, **extra):
    resp = client.post(
        "/api/tarefas",
        json={"titulo": titulo, "data": data, "hora_inicio": hora, "duracao_min": duracao, **extra},
    )
    assert resp.status_code == 201, resp.get_json()
    return resp.get_json()


# ---------------------------------------------------------------- CRUD
def test_criar_e_listar_ordenado_por_horario(client):
    criar(client, "Almoço", hora="12:00", duracao=60)
    criar(client, "Estudar Algoritmos", hora="09:00")
    dados = client.get("/api/tarefas?data=2026-11-21").get_json()
    assert [t["titulo"] for t in dados["tarefas"]] == ["Estudar Algoritmos", "Almoço"]
    assert dados["tarefas"][0]["hora_fim"] == "10:30"


def test_validacoes(client):
    assert client.post("/api/tarefas", json={"titulo": "  ", "data": "2026-11-21", "hora_inicio": "09:00"}).status_code == 400
    assert client.post("/api/tarefas", json={"titulo": "X", "data": "21/11/2026", "hora_inicio": "09:00"}).status_code == 400
    assert client.post("/api/tarefas", json={"titulo": "X", "data": "2026-11-21", "hora_inicio": "25:99"}).status_code == 400
    assert client.post("/api/tarefas", json={"titulo": "X", "data": "2026-11-21", "hora_inicio": "09:00", "duracao_min": 1}).status_code == 400
    assert client.post("/api/tarefas", json={"titulo": "X", "data": "2026-11-21", "hora_inicio": "09:00", "duracao_min": "90"}).status_code == 400


def test_editar_e_excluir(client):
    t = criar(client)
    r = client.patch(f"/api/tarefas/{t['id']}", json={"titulo": "Estudar Estruturas de Dados"})
    assert r.get_json()["titulo"] == "Estudar Estruturas de Dados"
    assert client.delete(f"/api/tarefas/{t['id']}").status_code == 200
    assert client.get(f"/api/tarefas/{t['id']}").status_code == 404


def test_rota_inexistente_devolve_json(client):
    r = client.get("/api/nada")
    assert r.status_code == 404 and "erro" in r.get_json()


# ------------------------------------------------- Jornada principal (PoC)
def test_alarme_toca_no_horario_e_so_para_ao_concluir(client, relogio):
    t = criar(client)

    # Noite anterior e manhã antes das 09:00: nada toca
    assert client.get("/api/alarme/ativo").get_json()["alarme"] is None
    relogio.agora = datetime(2026, 11, 21, 8, 59, 59)
    assert client.get("/api/alarme/ativo").get_json()["alarme"] is None

    # 09:00: alarme dispara
    relogio.agora = datetime(2026, 11, 21, 9, 0, 0)
    alarme = client.get("/api/alarme/ativo").get_json()["alarme"]
    assert alarme["id"] == t["id"] and alarme["alarme_ativo"] is True

    # Continua tocando depois do fim previsto, com cronômetro de duração excedida
    relogio.agora = datetime(2026, 11, 21, 10, 45, 0)
    alarme = client.get("/api/alarme/ativo").get_json()["alarme"]
    assert alarme is not None
    assert alarme["excedido_seg"] == 15 * 60

    # Informar atividade realizada interrompe imediatamente
    r = client.post(f"/api/tarefas/{t['id']}/concluir").get_json()
    assert r["status"] == "concluida" and r["alarme_ativo"] is False
    assert client.get("/api/alarme/ativo").get_json()["alarme"] is None


def test_concluir_e_idempotente(client, relogio):
    t = criar(client)
    client.post(f"/api/tarefas/{t['id']}/concluir")
    assert client.post(f"/api/tarefas/{t['id']}/concluir").status_code == 200
    tipos = [e["tipo"] for e in client.get(f"/api/tarefas/{t['id']}/eventos").get_json()["eventos"]]
    assert tipos.count("concluida") == 1


def test_neurofeedback_desligado_nao_toca(client, relogio):
    criar(client, neurofeedback=False)
    relogio.agora = datetime(2026, 11, 21, 9, 30, 0)
    assert client.get("/api/alarme/ativo").get_json()["alarme"] is None


def test_estender_pausa_o_alarme_e_ele_volta(client, relogio):
    t = criar(client)
    relogio.agora = datetime(2026, 11, 21, 9, 0, 0)
    r = client.post(f"/api/tarefas/{t['id']}/estender", json={"minutos": 15}).get_json()
    assert r["duracao_min"] == 105 and r["hora_fim"] == "10:45"

    relogio.agora = datetime(2026, 11, 21, 9, 14, 59)
    assert client.get("/api/alarme/ativo").get_json()["alarme"] is None
    relogio.agora = datetime(2026, 11, 21, 9, 15, 0)
    assert client.get("/api/alarme/ativo").get_json()["alarme"]["id"] == t["id"]


def test_estender_valida_minutos(client):
    t = criar(client)
    assert client.post(f"/api/tarefas/{t['id']}/estender", json={"minutos": 0}).status_code == 400
    assert client.post(f"/api/tarefas/{t['id']}/estender", json={}).status_code == 400


def test_reagendar_reordena_a_agenda(client, relogio):
    a = criar(client, "Estudar Algoritmos", hora="09:00")
    criar(client, "Almoço", hora="12:00", duracao=60)
    relogio.agora = datetime(2026, 11, 21, 9, 0, 0)

    r = client.post(f"/api/tarefas/{a['id']}/reagendar", json={"hora_inicio": "14:00"})
    assert r.status_code == 200 and r.get_json()["hora_inicio"] == "14:00"
    assert client.get("/api/alarme/ativo").get_json()["alarme"] is None

    ordem = [t["titulo"] for t in client.get("/api/tarefas?data=2026-11-21").get_json()["tarefas"]]
    assert ordem == ["Almoço", "Estudar Algoritmos"]


def test_reagendar_para_o_passado_e_recusado(client, relogio):
    t = criar(client)
    relogio.agora = datetime(2026, 11, 21, 9, 0, 0)
    r = client.post(f"/api/tarefas/{t['id']}/reagendar", json={"hora_inicio": "08:00"})
    assert r.status_code == 400


def test_reagendar_para_outro_dia(client):
    t = criar(client)
    r = client.post(f"/api/tarefas/{t['id']}/reagendar", json={"data": "2026-11-22", "hora_inicio": "10:00"})
    assert r.get_json()["data"] == "2026-11-22"
    assert client.get("/api/tarefas?data=2026-11-21").get_json()["tarefas"] == []


def test_conflito_de_horarios_apos_estender(client, relogio):
    a = criar(client, "Estudar Algoritmos", hora="09:00", duracao=60)
    b = criar(client, "Reunião", hora="10:00", duracao=30)
    lista = client.get("/api/tarefas?data=2026-11-21").get_json()["tarefas"]
    assert not any(t["conflito"] for t in lista)

    relogio.agora = datetime(2026, 11, 21, 9, 0, 0)
    client.post(f"/api/tarefas/{a['id']}/estender", json={"minutos": 30})
    lista = client.get("/api/tarefas?data=2026-11-21").get_json()["tarefas"]
    assert all(t["conflito"] for t in lista)
    assert {t["id"] for t in lista} == {a["id"], b["id"]}


def test_disparar_agora_demo(client, relogio):
    t = criar(client, data="2026-11-22", hora="07:00")
    r = client.post(f"/api/tarefas/{t['id']}/disparar-agora").get_json()
    assert r["data"] == "2026-11-20" and r["hora_inicio"] == "21:00"
    assert client.get("/api/alarme/ativo").get_json()["alarme"]["id"] == t["id"]


def test_alarme_persiste_entre_requisicoes(client, relogio):
    """Equivale a recarregar a página: o estado vem do servidor, não do navegador."""
    t = criar(client)
    relogio.agora = datetime(2026, 11, 21, 9, 5, 0)
    for _ in range(3):
        assert client.get("/api/alarme/ativo").get_json()["alarme"]["id"] == t["id"]


def test_historico_de_eventos(client, relogio):
    t = criar(client)
    relogio.agora = datetime(2026, 11, 21, 9, 0, 0)
    client.post(f"/api/tarefas/{t['id']}/estender", json={"minutos": 10})
    client.post(f"/api/tarefas/{t['id']}/concluir")
    tipos = [e["tipo"] for e in client.get(f"/api/tarefas/{t['id']}/eventos").get_json()["eventos"]]
    assert tipos == ["criada", "estendida", "concluida"]


# ------------------------------------------------- Fuso horário e horário passado
def test_servidor_usa_o_fuso_do_navegador(tmp_path):
    """Sem relógio falso, o servidor usa o cabeçalho X-Tz-Offset (180 = Brasília)."""
    from datetime import timezone

    app = create_app(db_path=str(tmp_path / "tz.db"))
    c = app.test_client()
    esperado = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=3)
    r = c.get("/api/saude", headers={"X-Tz-Offset": "180"}).get_json()
    obtido = datetime.strptime(r["agora"], "%Y-%m-%dT%H:%M:%S")
    assert abs((obtido - esperado).total_seconds()) < 5


def test_cabecalho_de_fuso_invalido_e_ignorado(tmp_path):
    app = create_app(db_path=str(tmp_path / "tz2.db"))
    r = app.test_client().get("/api/saude", headers={"X-Tz-Offset": "abc"})
    assert r.status_code == 200


def test_nao_permite_agendar_no_passado(client):
    resp = client.post(
        "/api/tarefas",
        json={"titulo": "Ontem", "data": "2026-11-10", "hora_inicio": "01:36", "duracao_min": 90},
    )
    assert resp.status_code == 400
    assert "já passou" in resp.get_json()["erro"]


def test_permite_agendar_para_o_minuto_atual(client, relogio):
    relogio.agora = datetime(2026, 11, 20, 21, 0, 40)
    resp = client.post(
        "/api/tarefas",
        json={"titulo": "Agora", "data": "2026-11-20", "hora_inicio": "21:00", "duracao_min": 30},
    )
    assert resp.status_code == 201


def test_intensidade_padrao_e_continua(client):
    assert criar(client)["intervalo_seg"] == 3
    assert client.post(
        "/api/tarefas",
        json={"titulo": "X", "data": "2026-11-21", "hora_inicio": "09:00", "intervalo_seg": 1},
    ).status_code == 400
