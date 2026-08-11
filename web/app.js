/* ---- acordeao das hipoteses ---------------------------------------- */
document.querySelectorAll('.hip-cab').forEach(b => {
  b.addEventListener('click', () => {
    const hip = b.closest('.hip');
    const aberta = hip.classList.toggle('aberta');
    b.setAttribute('aria-expanded', String(aberta));   // faltava: leitor de tela
    if (aberta) { b.classList.add('bateu');
      b.addEventListener('animationend', () => b.classList.remove('bateu'), {once:true}); }
  });
});

/* ---- barras so animam quando entram em vista ------------------------ */
/* antes disso elas corriam no load: quando o leitor chegava na oitava
   hipotese a animacao tinha acabado havia meio minuto. */
const io = new IntersectionObserver(es => {
  es.forEach(e => { if (e.isIntersecting) { e.target.dataset.visivel = '1'; io.unobserve(e.target); } });
}, {threshold:.4});
document.querySelectorAll('.sonda').forEach(el => io.observe(el));

/* ---- contadores da capa -------------------------------------------- */
const suave = t => 1 - Math.pow(1 - t, 3);
const ioNum = new IntersectionObserver(es => {
  es.forEach(e => {
    if (!e.isIntersecting) return;
    ioNum.unobserve(e.target);
    const alvo = +e.target.dataset.alvo, t0 = performance.now();
    (function passo(t){
      const k = Math.min((t - t0) / 850, 1);
      e.target.textContent = Math.round(alvo * suave(k));
      if (k < 1) requestAnimationFrame(passo);
    })(t0);
  });
}, {threshold:.6});
document.querySelectorAll('[data-alvo]').forEach(el => ioNum.observe(el));

/* ---- indice de evidencias ------------------------------------------ */
const cx = document.getElementById('busca'), fc = document.getElementById('filtro-conf'),
      ft = document.getElementById('filtro-tema'), lista = document.getElementById('lista-ev'),
      orf = document.getElementById('so-orfaos');
let visiveis = [], cursor = -1;

function esc(s){ return s.replace(/[.*+?^${}()|[\]\]/g, '\$&'); }
function semAcento(s){ return s.normalize('NFD').replace(/[̀-ͯ]/g, ''); }

function filtra(){
  if (!lista) return;
  const bruto = (cx.value || '').trim();
  const termos = semAcento(bruto.toLowerCase()).split(/\s+/).filter(Boolean);
  const c = fc.value, tema = ft.value, soOrf = orf && orf.checked;
  visiveis = []; cursor = -1;
  lista.querySelectorAll('.ev-item').forEach(el => {
    const hay = el.dataset.busca;
    const ok = termos.every(w => hay.includes(w))
            && (!c || el.dataset.conf === c)
            && (!tema || el.dataset.temas.includes('|' + tema + '|'))
            && (!soOrf || el.dataset.orfao === '1');
    el.hidden = !ok;
    el.classList.remove('selecionado');
    if (ok) visiveis.push(el);
    const alvo = el.querySelector('.ev-txt');
    if (!alvo) return;
    const puro = alvo.dataset.puro || (alvo.dataset.puro = alvo.textContent);
    if (ok && bruto.length > 1) {
      const re = new RegExp('(' + esc(bruto) + ')', 'gi');
      alvo.innerHTML = semAcento(puro).match(re)
        ? puro.replace(new RegExp('(' + esc(bruto) + ')', 'gi'), '<mark>$1</mark>') : puro;
    } else if (alvo.innerHTML !== puro) { alvo.textContent = puro; }
  });
  document.getElementById('conta').textContent = visiveis.length;
  document.getElementById('vazio').hidden = visiveis.length > 0;
  const p = new URLSearchParams();
  if (bruto) p.set('q', bruto);
  if (c) p.set('conf', c);
  if (tema) p.set('tema', tema);
  if (soOrf) p.set('orfaos', '1');
  history.replaceState(null, '', p.toString() ? '?' + p : location.pathname);
}

let tempo;
function agenda(){ clearTimeout(tempo); tempo = setTimeout(filtra, 110); }
[cx, fc, ft, orf].forEach(el => el && el.addEventListener('input', agenda));

/* estado vem da URL, e a lista e filtrada no load — bfcache devolvia campo
   preenchido com a lista inteira e o contador mentindo */
if (lista) {
  const u = new URLSearchParams(location.search);
  if (u.get('q')) cx.value = u.get('q');
  if (u.get('conf')) fc.value = u.get('conf');
  if (u.get('tema')) ft.value = u.get('tema');
  if (u.get('orfaos')) orf.checked = true;
  filtra();
  /* deep link com filtro ativo caia num item escondido: limpa e vai */
  if (location.hash && document.querySelector(location.hash)?.hidden) {
    cx.value = ''; fc.value = ''; ft.value = ''; if (orf) orf.checked = false;
    filtra(); document.querySelector(location.hash).scrollIntoView();
  }
}

/* setas percorrem os resultados sem tirar a mao do teclado */
if (cx) cx.addEventListener('keydown', ev => {
  if (!['ArrowDown','ArrowUp','Enter'].includes(ev.key) || !visiveis.length) return;
  ev.preventDefault();
  if (ev.key === 'Enter' && cursor >= 0) { location.hash = visiveis[cursor].id; return; }
  visiveis.forEach(el => el.classList.remove('selecionado'));
  cursor = ev.key === 'ArrowDown'
    ? Math.min(cursor + 1, visiveis.length - 1) : Math.max(cursor - 1, 0);
  const alvo = visiveis[cursor];
  alvo.classList.add('selecionado');
  alvo.scrollIntoView({block:'nearest', behavior:'smooth'});
});

/* ---- voltar ao topo ------------------------------------------------- */
const topo = document.getElementById('ao-topo');
if (topo) {
  addEventListener('scroll', () => { topo.hidden = scrollY < 700; }, {passive:true});
  topo.onclick = () => scrollTo({top:0, behavior:'smooth'});
}
