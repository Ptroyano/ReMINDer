# Roteiro do vídeo (máximo 1 minuto)

Objetivo da rubrica: **apresentar o projeto concluído em funcionamento**. O vídeo não pode divergir do que foi desenvolvido.

## Antes de gravar

1. Suba o servidor e abra `http://localhost:8000` em tela cheia.
2. Apague `backend/reminder.db` para começar com a agenda vazia.
3. Clique em **🔇 Ativar som** (precisa estar "🔊 Som ativado" para o alarme gravar áudio).
4. Para gravar o som do computador junto com a tela:
   - **Windows:** Xbox Game Bar (`Win + G`) ou OBS Studio.
   - **macOS:** `Cmd + Shift + 5` não grava o áudio do sistema; use OBS Studio com um driver de áudio, ou grave a tela com o celular apontado para o computador.
5. Ensaie uma vez com cronômetro. Alvo: **50 a 55 segundos**.

## Roteiro com tempos

| Tempo | Na tela | Fala sugerida |
|---|---|---|
| 0:00–0:07 | Tela inicial do ReMINDer | "Este é o ReMINDer, uma agenda com alarme que só para quando a atividade é feita. Esta prova de conceito valida a jornada do Lucas." |
| 0:07–0:17 | Preenche "Estudar Algoritmos", 09:00, 90 min → **Agendar** | "Na noite anterior ele agenda a atividade, com data, horário e duração, e liga o neuro-feedback." |
| 0:17–0:25 | Clica em **Disparar agora (demo)** | "Para não esperar o relógio, uso um atalho de demonstração que antecipa o horário." |
| 0:25–0:35 | Tela de interrupção com cronômetro; recarrega a página (F5) e o alarme continua | "O alarme toca em intervalos e não para sozinho. Mesmo recarregando a página, ele continua, porque a regra está no servidor." |
| 0:35–0:47 | **Alterar Duração / Reagendar** → **+15 min** → **Confirmar** → agenda reajustada | "Se precisar de mais tempo, ele acrescenta minutos e a agenda é reajustada, avisando se houver sobreposição." |
| 0:47–0:55 | **Informar Atividade Realizada**; alarme para; atividade concluída | "Ao informar que concluiu, o alarme para e a atividade fica registrada." |
| 0:55–1:00 | Mostra o repositório no GitHub (opcional) | "Feito com Flask, SQLite e JavaScript. O código está no GitHub." |

## Texto corrido (cerca de 120 palavras)

> Este é o ReMINDer, uma agenda com alarme que só para quando a atividade é feita. Esta prova de conceito valida a jornada do Lucas. Na noite anterior ele agenda a atividade, com data, horário e duração, e liga o neuro-feedback. Para não esperar o relógio, uso um atalho de demonstração que antecipa o horário. O alarme toca em intervalos e não para sozinho. Mesmo recarregando a página, ele continua, porque a regra está no servidor. Se precisar de mais tempo, ele acrescenta minutos e a agenda é reajustada, avisando se houver sobreposição. Ao informar que concluiu, o alarme para e a atividade fica registrada. Feito com Flask, SQLite e JavaScript.

## Hospedagem do vídeo

- **YouTube:** publique como **Não listado** e envie o link. Com "Privado", só quem você convidar consegue assistir, e o professor pode não conseguir abrir. Se o enunciado do Blackboard exigir "Privado", convide o e-mail do professor.
- **GitHub:** um MP4 pequeno pode ir na pasta `docs/`. O GitHub limita arquivos a 100 MB.

## Cuidados

- Não mostre nada que não esteja no projeto entregue.
- Se o áudio do alarme não gravar, deixe a tela de interrupção visível por alguns segundos e diga que o sinal está tocando; a avaliação é o funcionamento da jornada.
