-- ReMINDer PoC - modelo de dados (SQLite)

CREATE TABLE IF NOT EXISTS tarefas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo          TEXT    NOT NULL CHECK (length(titulo) BETWEEN 1 AND 100),
    data            TEXT    NOT NULL,                       -- AAAA-MM-DD
    hora_inicio     TEXT    NOT NULL,                       -- HH:MM
    duracao_min     INTEGER NOT NULL CHECK (duracao_min BETWEEN 5 AND 1440),
    neurofeedback   INTEGER NOT NULL DEFAULT 1,             -- 1 = alarme persistente ligado
    intervalo_seg   INTEGER NOT NULL DEFAULT 30,            -- intervalo entre os sinais sonoros
    status          TEXT    NOT NULL DEFAULT 'agendada'
                    CHECK (status IN ('agendada', 'concluida')),
    silenciado_ate  TEXT,                                   -- alarme pausado por "+ tempo" (AAAA-MM-DDTHH:MM:SS)
    concluida_em    TEXT,                                   -- AAAA-MM-DDTHH:MM:SS
    criado_em       TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tarefas_data ON tarefas (data, hora_inicio);

-- Histórico de tudo que acontece com uma tarefa (base para o "neuro-feedback")
CREATE TABLE IF NOT EXISTS eventos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tarefa_id   INTEGER NOT NULL REFERENCES tarefas (id) ON DELETE CASCADE,
    tipo        TEXT    NOT NULL,   -- criada | editada | estendida | reagendada | concluida | disparo_demo
    detalhe     TEXT,
    criado_em   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eventos_tarefa ON eventos (tarefa_id, id);
