# Definição da PoC (revisita do projeto)

> Item 1 da rubrica: *revisitar o projeto apresentado e definir qual será a prova de conceito que precisa ser desenvolvida.*

## 1. Revisita do projeto da 1ª etapa

A 1ª etapa propôs o ReMINDer como um app para iOS, Android, Apple e Mac, com custos de licença estimados (US$ 99/ano para Apple e US$ 260/ano por plataforma) e concluiu que os riscos de desenvolvimento eram baixos.

Ao revisitar, o risco que realmente importa é outro. Distribuição e licenças são questões de **produto final**. A pergunta que decide se o projeto faz sentido é:

> **O alarme que só para quando a pessoa confirma a atividade funciona, de forma simples e confiável, como mecanismo de neuro-feedback?**

Todo o valor do ReMINDer depende disso. Se esse mecanismo não funcionar, apps em quatro plataformas não resolvem nada.

### Melhoria justificada

| Na 1ª etapa | Na PoC | Justificativa |
|---|---|---|
| Apps nativos em várias plataformas, com licenças anuais | **Aplicação web responsiva** (celular e computador pelo navegador) | Valida o mecanismo central sem custo de licença e sem desenvolver cinco versões antes de saber se a ideia funciona |
| Escopo amplo (agenda completa, todas as jornadas) | **Uma jornada-chave**: planejar → alarme persistente → concluir ou reajustar | Reduz risco e tempo; é o que o enunciado pede para uma PoC |
| Regra do alarme implícita | **Regra no servidor** (`/api/alarme/ativo`) | O alarme sobrevive a recarregar a página e pode ser consultado de qualquer aparelho |

## 2. Jornada escolhida

**Jornada do Lucas** (1ª etapa, seção 4), com o reajuste de agenda da **Camila** (hiperfoco e remanejamento):

1. Planejamento noturno e cadastro da atividade (data, horário, duração)
2. Ativação do neuro-feedback
3. Disparo do alarme no horário, tocando em intervalos até a confirmação
4. Confirmação em **Informar Atividade Realizada**, ou **Alterar Duração / Reagendar** (+10, +15, +30 min ou novo horário)
5. Agenda diária reordenada

## 3. Hipótese e critérios de sucesso

| # | Critério | Como é verificado |
|---|---|---|
| C1 | O alarme dispara no horário agendado e continua ativo depois do fim previsto | Testes automatizados e demonstração |
| C2 | O alarme persiste ao recarregar a página | Teste automatizado (estado vem do servidor) e demonstração |
| C3 | O alarme só para ao informar a atividade realizada | Teste automatizado e demonstração |
| C4 | Acrescentar tempo ou reagendar atualiza a agenda e sinaliza sobreposição de horários | Testes automatizados e demonstração |
| C5 | Dados persistem em banco | SQLite, tabelas `tarefas` e `eventos` |

## 4. Decisões de projeto tomadas na PoC

Estes pontos não estavam definidos na 1ª etapa e foram decididos aqui. **O grupo deve confirmar** que concorda com eles:

1. **Acrescentar tempo pausa o alarme.** Ao escolher +10/+15/+30 min, a duração da atividade aumenta e o alarme fica pausado pelo tempo acrescentado, voltando a tocar depois. Assim a pessoa não é "perturbada" enquanto usa o tempo extra, mas continua sendo cobrada.
2. **Reagendar exige horário futuro.** Reagendar para um horário já passado faria o alarme tocar de novo imediatamente.
3. **Sobreposição só é sinalizada, não corrigida.** Quando o tempo extra invade a atividade seguinte, a agenda mostra o aviso; a decisão de remanejar continua com a pessoa.
4. **Intensidade do alarme configurável** por atividade (contínuo, 10 s, 30 s ou 1 min).

## 5. Fora do escopo desta PoC

Login e múltiplos usuários, aplicativos nativos, notificações push, edição completa pela interface, relatórios e integração com agendas existentes.

## 6. Riscos identificados

| Risco | Efeito | Tratamento na PoC |
|---|---|---|
| Navegadores bloqueiam áudio sem interação do usuário | Alarme sem som no primeiro uso | Botão **Ativar som** visível; vibração e título da aba piscando como reforço |
| Abas em segundo plano têm temporizadores limitados | Som pode atrasar com a aba oculta | Consulta imediata ao voltar para a aba; produto final deve usar notificações nativas |
| "Neuro-feedback" pode ser entendido como técnica clínica com EEG | Expectativa errada sobre o produto | No projeto, o termo nomeia o ciclo de alarme persistente + confirmação; não há medição neural nem alegação clínica |
