# Checklist de entrega — 2ª etapa (prazo: 23/11/2026, 23h59, horário de Brasília)

## Rubrica × evidências no repositório

| Item da rubrica | Pontos | Onde está |
|---|---|---|
| Revisitar o projeto e definir a PoC | 1,0 | `docs/DEFINICAO_POC.md` |
| Preparação do ambiente de desenvolvimento | 2,0 | Stack definida (README), `requirements.txt`, `.gitignore`, instruções de execução, servidor de desenvolvimento rodando com um comando |
| Desenvolvimento do frontend | 2,0 | `frontend/` (4 telas da jornada, responsivo) |
| Desenvolvimento do backend | 2,0 | `backend/app.py` (API REST), `backend/schema.sql` (dados), `backend/tests/` (16 testes) |
| Vídeo de até 1 minuto | 1,0 | Roteiro em `docs/ROTEIRO_VIDEO.md` — **precisa ser gravado por vocês** |
| Todo o projeto no GitHub | 2,0 | Ver passos abaixo — **precisa ser publicado por vocês** |

## O que ainda depende do grupo

- [ ] **Template do Blackboard:** os slides pedem para seguir o template da plataforma. Ele não veio nos arquivos; baixe no Blackboard e transfira o conteúdo de `docs/DEFINICAO_POC.md` e do README para ele.
- [ ] **Confirmar as decisões de projeto** da seção 4 de `docs/DEFINICAO_POC.md`.
- [ ] **Gravar o vídeo** (máx. 1 min) e publicar.
- [ ] **Publicar no GitHub** com os três integrantes como membros.
- [ ] Preencher `<URL-DO-REPOSITORIO>` no README.

## Passos no GitHub

A rubrica pede **todos os integrantes como membros** e **histórico de contribuições de cada um**. Isso significa que cada pessoa precisa fazer commits com a própria conta.

1. **Um integrante cria o repositório** em github.com → *New repository* (sem README, para não conflitar).
2. **Adicione os outros dois:** *Settings → Collaborators → Add people*. Cada um aceita o convite por e-mail.
3. **Suba o projeto** (a partir da pasta `reminder-poc`):

   ```bash
   git init
   git add .
   git commit -m "feat: PoC inicial do ReMINDer (backend, frontend e docs)"
   git branch -M main
   git remote add origin https://github.com/<usuario>/<repositorio>.git
   git push -u origin main
   ```

4. **Cada integrante clona e contribui de verdade** com a própria conta (commits pequenos, com mensagens claras). Uma divisão simples, só como sugestão:
   - Integrante A: backend e testes (`backend/`)
   - Integrante B: frontend (`frontend/`)
   - Integrante C: documentação, roteiro e vídeo (`docs/`, `README.md`)
5. Confira em *Insights → Contributors* se os três aparecem.
6. Confirme que o repositório está **público** ou que o professor tem acesso.

> Se o grupo já tem commits anteriores, prefira usar o repositório existente e adicionar estes arquivos a ele.

## Antes de enviar

- [ ] Em uma pasta limpa: clonar, instalar e subir seguindo só o README. Se funcionar, a avaliação também funciona.
- [ ] `python -m pytest backend/tests -q` passa.
- [ ] O vídeo mostra exatamente o que está no repositório.
- [ ] Link do vídeo e do GitHub enviados na plataforma **antes de 23/11/2026 às 23h59**.
