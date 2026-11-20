/* ReMINDer - PoC (frontend)
 * JavaScript puro, sem dependências. Conversa com a API em /api.
 *
 * Jornada: planejar -> alarme persistente -> informar realizada ou reajustar.
 * A regra "o alarme só para quando a atividade é informada" mora no servidor;
 * aqui o navegador apenas consulta /api/alarme/ativo e toca o som.
 */
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);

  // ------------------------------------------------------------------ API
  async function api(caminho, { method = "GET", body } = {}) {
    const res = await fetch("/api" + caminho, {
      method,
      // X-Tz-Offset: o servidor usa a hora local do navegador (ex.: Codespaces roda em UTC)
      headers: { "Content-Type": "application/json", "X-Tz-Offset": String(new Date().getTimezoneOffset()) },
      body: body ? JSON.stringify(body) : undefined,
    });
    let dados = null;
    try { dados = await res.json(); } catch (_) { /* sem corpo */ }
    if (!res.ok) throw new Error((dados && dados.erro) || `Erro inesperado (${res.status})`);
    return dados;
  }

  // ------------------------------------------------------------- Utilidades
  const pad = (n) => String(n).padStart(2, "0");
  const isoData = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const hoje = () => isoData(new Date());
  const amanha = () => { const d = new Date(); d.setDate(d.getDate() + 1); return isoData(d); };

  function esc(texto) {
    const div = document.createElement("div");
    div.textContent = texto;
    return div.innerHTML;
  }

  function fmtDuracao(min) {
    const h = Math.floor(min / 60), m = min % 60;
    if (!h) return `${m} min`;
    return m ? `${h}h${pad(m)}` : `${h}h`;
  }

  function fmtCron(seg) {
    seg = Math.max(0, Math.floor(seg));
    const h = Math.floor(seg / 3600), m = Math.floor((seg % 3600) / 60), s = seg % 60;
    return h ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
  }

  function fmtDataCurta(iso) {
    const [a, m, d] = iso.split("-");
    return `${d}/${m}/${a}`;
  }

  let toastTimer = null;
  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { el.hidden = true; }, 3500);
  }

  function mostrarErro(el, msg) {
    el.textContent = msg;
    el.hidden = !msg;
  }

  // ------------------------------------------------------------------ Estado
  let dataSel = amanha();     // dia exibido na agenda (planejamento é na noite anterior)
  let alarmeAtual = null;     // atividade com alarme tocando
  let alarmeRecebidoEm = 0;   // Date.now() do último polling (para o cronômetro)
  let ultimoSinal = 0;        // quando o último sinal sonoro tocou
  let destaqueId = null;      // atividade recém-reajustada
  let tarefaAjuste = null;    // atividade aberta no modal
  let acrescimo = null;       // minutos escolhidos no modal

  // ------------------------------------------------------------------- Áudio
  let audioCtx = null;

  function audioLigado() {
    return !!audioCtx && audioCtx.state === "running";
  }

  function atualizarBotoesSom() {
    const ligado = audioLigado();
    const topo = $("#btn-som-topo");
    topo.textContent = ligado ? "🔊 Som ativado" : "🔇 Ativar som";
    topo.classList.toggle("ligado", ligado);
    $("#btn-som-alarme").hidden = ligado || !alarmeAtual;
  }

  // Navegadores só liberam áudio depois de um toque/clique do usuário.
  function desbloquearAudio() {
    try {
      if (!audioCtx) {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return;
        audioCtx = new Ctx();
      }
      if (audioCtx.state !== "running") {
        audioCtx.resume().then(atualizarBotoesSom, () => {});
      }
    } catch (_) { /* sem áudio disponível */ }
    atualizarBotoesSom();
  }

  // Sirene: 8 bipes altos alternando dois tons (~2 s). Com intervalo de 3 s o som
  // fica praticamente contínuo; intervalos maiores deixam pausas entre as sirenes.
  function tocarSinal() {
    if (audioLigado()) {
      const t0 = audioCtx.currentTime;
      const mestre = audioCtx.createGain();
      mestre.gain.value = 0.9;
      const compressor = audioCtx.createDynamicsCompressor();
      mestre.connect(compressor).connect(audioCtx.destination);
      for (let i = 0; i < 8; i++) {
        const inicio = t0 + i * 0.25;
        const osc = audioCtx.createOscillator();
        const ganho = audioCtx.createGain();
        osc.type = "square";
        osc.frequency.value = i % 2 === 0 ? 988 : 740;
        ganho.gain.setValueAtTime(0.0001, inicio);
        ganho.gain.exponentialRampToValueAtTime(0.7, inicio + 0.02);
        ganho.gain.setValueAtTime(0.7, inicio + 0.18);
        ganho.gain.exponentialRampToValueAtTime(0.0001, inicio + 0.23);
        osc.connect(ganho).connect(mestre);
        osc.start(inicio);
        osc.stop(inicio + 0.24);
      }
    }
    try { if (navigator.vibrate) navigator.vibrate([300, 100, 300, 100, 300, 100, 300]); } catch (_) { /* ignora */ }
  }

  ["pointerdown", "keydown", "touchstart"].forEach((ev) =>
    document.addEventListener(ev, desbloquearAudio, { passive: true })
  );

  // ------------------------------------------------------------------ Agenda
  function htmlItem(t) {
    const selos = [];
    if (t.status === "concluida") selos.push('<span class="selo selo-ok">Concluída</span>');
    if (t.alarme_ativo) selos.push('<span class="selo selo-toca">Alarme tocando</span>');
    if (t.conflito) selos.push('<span class="selo selo-conflito">Horários se sobrepõem</span>');
    if (t.neurofeedback && t.status === "agendada") {
      selos.push(`<span class="selo selo-neuro">Alarme: ${t.intervalo_seg <= 3 ? "contínuo" : "a cada " + t.intervalo_seg + "s"}</span>`);
    }

    let acoes = "";
    if (t.status === "agendada") {
      acoes = `
        <button class="btn btn-sucesso btn-mini" data-acao="concluir" type="button">✔ Informar realizada</button>
        <button class="btn btn-contorno btn-mini" data-acao="ajustar" type="button">⏱ Ajustar</button>
        <button class="btn btn-contorno btn-mini" data-acao="demo" type="button" title="Demonstração: dispara o alarme agora">▶ Disparar agora (demo)</button>
        <button class="btn btn-perigo btn-mini" data-acao="excluir" type="button">Excluir</button>`;
    } else if (t.concluida_em) {
      const hora = t.concluida_em.slice(11, 16);
      acoes = `<span class="meta">Concluída às ${hora}</span>`;
    }

    const classes = [
      "item",
      `status-${t.status}`,
      t.alarme_ativo ? "tocando" : "",
      t.conflito ? "conflito" : "",
      t.id === destaqueId ? "destaque" : "",
    ].join(" ");

    return `
      <li class="${classes}" data-id="${t.id}">
        <div class="hora"><strong>${esc(t.hora_inicio)}</strong><span>até ${esc(t.hora_fim)}</span></div>
        <div>
          <h3>${esc(t.titulo)}</h3>
          <p class="meta">Duração: ${fmtDuracao(t.duracao_min)}</p>
          <div class="selos">${selos.join("")}</div>
          <div class="acoes">${acoes}</div>
        </div>
      </li>`;
  }

  async function carregarAgenda() {
    try {
      const { tarefas } = await api(`/tarefas?data=${dataSel}`);
      $("#agenda-lista").innerHTML = tarefas.map(htmlItem).join("");
      $("#agenda-vazia").hidden = tarefas.length > 0;
      window.__tarefasDoDia = tarefas;
    } catch (e) {
      toast(e.message);
    }
    $("#btn-hoje").classList.toggle("ativo", dataSel === hoje());
    $("#btn-amanha").classList.toggle("ativo", dataSel === amanha());
    $("#agenda-data").value = dataSel;
    $("#titulo-agenda").textContent = `Agenda de ${fmtDataCurta(dataSel)}`;
  }

  function selecionarDia(data) {
    dataSel = data;
    $("#f-data").value = data;
    return carregarAgenda();
  }

  function destacar(tarefa, mensagem) {
    destaqueId = tarefa.id;
    const aviso = $("#agenda-aviso");
    aviso.textContent = mensagem;
    aviso.hidden = false;
    setTimeout(() => { destaqueId = null; }, 2500);
    setTimeout(() => { aviso.hidden = true; }, 12000);
  }

  // -------------------------------------------------- Alarme (modo interrupção)
  function mostrarAlarme(t) {
    const novo = !alarmeAtual || alarmeAtual.id !== t.id;
    alarmeAtual = t;
    alarmeRecebidoEm = Date.now();

    if (novo) {
      ultimoSinal = 0;
      $("#alarme-titulo").textContent = t.titulo;
      $("#alarme-inicio").textContent = `Começou às ${t.hora_inicio} · previsto até ${t.hora_fim}`;
      $("#alarme").hidden = false;
      document.body.classList.add("sem-scroll");
      $("#btn-concluir").focus({ preventScroll: true });
      carregarAgenda();
    }
    atualizarCronometro();
    atualizarBotoesSom();
  }

  function esconderAlarme() {
    if (!alarmeAtual) return;
    alarmeAtual = null;
    $("#alarme").hidden = true;
    document.body.classList.remove("sem-scroll");
    document.title = "ReMINDer";
    atualizarBotoesSom();
    carregarAgenda();
  }

  function atualizarCronometro() {
    if (!alarmeAtual) return;
    const passou = (Date.now() - alarmeRecebidoEm) / 1000;
    const decorrido = alarmeAtual.decorrido_seg + passou;
    const restante = alarmeAtual.duracao_min * 60 - decorrido;
    const caixa = document.querySelector(".cronometro");
    if (restante >= 0) {
      $("#alarme-cron-rotulo").textContent = "Tempo restante da atividade";
      $("#alarme-cron").textContent = fmtCron(restante);
      caixa.classList.remove("excedido");
    } else {
      $("#alarme-cron-rotulo").textContent = "Duração excedida";
      $("#alarme-cron").textContent = "+" + fmtCron(-restante);
      caixa.classList.add("excedido");
    }
  }

  async function verificarAlarme() {
    try {
      const { alarme, total_ativos: total } = await api("/alarme/ativo");
      if (alarme) {
        mostrarAlarme(alarme);
        const outros = $("#alarme-outros");
        outros.hidden = total < 2;
        outros.textContent = total > 1 ? `Há mais ${total - 1} atividade(s) aguardando confirmação.` : "";
      } else {
        esconderAlarme();
      }
    } catch (_) { /* servidor indisponível: tenta de novo no próximo ciclo */ }
  }

  // Relógio de 1 segundo: cronômetro, repetição do sinal e título da aba.
  let piscar = false;
  setInterval(() => {
    if (!alarmeAtual) return;
    atualizarCronometro();
    const agora = Date.now();
    if (agora - ultimoSinal >= alarmeAtual.intervalo_seg * 1000) {
      ultimoSinal = agora;
      tocarSinal();
    }
    piscar = !piscar;
    document.title = piscar ? `⏰ HORA DE: ${alarmeAtual.titulo}` : "ReMINDer";
  }, 1000);

  setInterval(verificarAlarme, 2000);
  setInterval(carregarAgenda, 10000);
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) { verificarAlarme(); carregarAgenda(); }
  });

  // ------------------------------------------------------------ Ações da jornada
  async function concluir(id) {
    try {
      const t = await api(`/tarefas/${id}/concluir`, { method: "POST" });
      toast(`“${t.titulo}” concluída. Parabéns! 🎉`);
      await verificarAlarme();
      await carregarAgenda();
    } catch (e) {
      toast(e.message);
    }
  }

  function abrirModal(t) {
    tarefaAjuste = t;
    acrescimo = null;
    document.querySelectorAll("#modal-chips .chip").forEach((c) => c.classList.remove("ativo"));
    $("#modal-tarefa").textContent = `${t.titulo} · ${t.hora_inicio}–${t.hora_fim}`;
    $("#m-data").value = t.data;
    $("#m-hora").value = "";
    mostrarErro($("#modal-erro"), "");
    $("#modal").hidden = false;
    document.querySelector("#modal-chips .chip").focus();
  }

  function fecharModal() {
    $("#modal").hidden = true;
    tarefaAjuste = null;
  }

  async function confirmarAjuste() {
    const hora = $("#m-hora").value;
    const data = $("#m-data").value;
    if (!acrescimo && !hora) {
      mostrarErro($("#modal-erro"), "Escolha um acréscimo de tempo ou informe um novo horário.");
      return;
    }
    const id = tarefaAjuste.id;
    try {
      let t = tarefaAjuste;
      if (acrescimo) {
        t = await api(`/tarefas/${id}/estender`, { method: "POST", body: { minutos: acrescimo } });
      }
      if (hora) {
        t = await api(`/tarefas/${id}/reagendar`, { method: "POST", body: { data, hora_inicio: hora } });
      }
      fecharModal();
      const partes = [];
      if (acrescimo) partes.push(`+${acrescimo} min (duração ${fmtDuracao(t.duracao_min)})`);
      if (hora) partes.push(`reprogramada para ${fmtDataCurta(t.data)} às ${t.hora_inicio}`);
      destacar(t, `Agenda reajustada: “${t.titulo}” ${partes.join(" e ")}.`);
      await verificarAlarme();
      await selecionarDia(t.data);
      const item = document.querySelector(`.item[data-id="${t.id}"]`);
      if (item) item.scrollIntoView({ behavior: "smooth", block: "center" });
    } catch (e) {
      mostrarErro($("#modal-erro"), e.message);
    }
  }

  // ------------------------------------------------------------------ Eventos
  $("#form-tarefa").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const f = ev.target;
    const erro = $("#form-erro");
    mostrarErro(erro, "");
    try {
      const t = await api("/tarefas", {
        method: "POST",
        body: {
          titulo: f.titulo.value,
          data: f.data.value,
          hora_inicio: f.hora_inicio.value,
          duracao_min: parseInt(f.duracao_min.value, 10),
          intervalo_seg: parseInt(f.intervalo_seg.value, 10),
          neurofeedback: f.neurofeedback.checked,
        },
      });
      f.titulo.value = "";
      destaqueId = t.id;
      setTimeout(() => { destaqueId = null; }, 2500);
      await selecionarDia(t.data);
      toast(`Agendado: “${t.titulo}” às ${t.hora_inicio}.`);
    } catch (e) {
      mostrarErro(erro, e.message);
    }
  });

  $("#agenda-lista").addEventListener("click", async (ev) => {
    const botao = ev.target.closest("[data-acao]");
    if (!botao) return;
    const id = Number(botao.closest(".item").dataset.id);
    const tarefa = (window.__tarefasDoDia || []).find((t) => t.id === id);
    const acao = botao.dataset.acao;
    try {
      if (acao === "concluir") await concluir(id);
      if (acao === "ajustar" && tarefa) abrirModal(tarefa);
      if (acao === "demo") {
        const t = await api(`/tarefas/${id}/disparar-agora`, { method: "POST" });
        await selecionarDia(t.data);
        await verificarAlarme();
      }
      if (acao === "excluir" && window.confirm("Excluir esta atividade?")) {
        await api(`/tarefas/${id}`, { method: "DELETE" });
        await verificarAlarme();
        await carregarAgenda();
        toast("Atividade excluída.");
      }
    } catch (e) {
      toast(e.message);
    }
  });

  $("#btn-concluir").addEventListener("click", () => alarmeAtual && concluir(alarmeAtual.id));
  $("#btn-ajustar").addEventListener("click", () => alarmeAtual && abrirModal(alarmeAtual));
  $("#btn-som-topo").addEventListener("click", desbloquearAudio);
  $("#btn-som-alarme").addEventListener("click", desbloquearAudio);

  $("#modal-chips").addEventListener("click", (ev) => {
    const chip = ev.target.closest(".chip");
    if (!chip) return;
    const min = Number(chip.dataset.min);
    acrescimo = acrescimo === min ? null : min;
    document.querySelectorAll("#modal-chips .chip").forEach((c) =>
      c.classList.toggle("ativo", Number(c.dataset.min) === acrescimo)
    );
    mostrarErro($("#modal-erro"), "");
  });
  $("#modal-cancelar").addEventListener("click", fecharModal);
  $("#modal-confirmar").addEventListener("click", confirmarAjuste);
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "Escape" && !$("#modal").hidden) fecharModal();
  });

  $("#btn-hoje").addEventListener("click", () => selecionarDia(hoje()));
  $("#btn-amanha").addEventListener("click", () => selecionarDia(amanha()));
  $("#agenda-data").addEventListener("change", (ev) => ev.target.value && selecionarDia(ev.target.value));

  // ------------------------------------------------------------------- Início
  $("#f-data").value = dataSel;
  atualizarBotoesSom();
  carregarAgenda();
  verificarAlarme();
})();
