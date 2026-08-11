/* Explorador do grafo de propriedades — canvas 2D, sem dependencia.
   Modelo: nos com label e propriedades, relacoes tipadas com propriedades.
   Comeca pelas hipoteses vivas; o resto do grafo se abre por expansao. */
(() => {
const cv = document.getElementById('cv');
if (!cv) return;
const ctx = cv.getContext('2d');
const painel = document.getElementById('painel');
const cxBusca = document.getElementById('g-busca');
const infoSel = document.getElementById('g-sel');

const COR = {
  Hipotese:'#ffb703', HipoteseMorta:'#9a9086', Evidencia:'#2f9e6e',
  EvidenciaAmb:'#e8a13a', EvidenciaDisp:'#e03131', Tema:'#1a7fb5', Ator:'#7048a8',
};
const CORREL = {
  APOIA:'#2f9e6e', CONTRADIZ:'#e03131', CONCORRE_COM:'#9a9086',
  TEM_TEMA:'#1a7fb5', MENCIONA:'#7048a8',
};
const TINTA = '#151016';

let NOS = new Map(), RELS = [], META = {};
let vis = new Set();            // ids visiveis
let sel = null, hover = null;
let cam = {x:0, y:0, z:1};
let arrastando = null, panDe = null;
let pausado = false;
const tiposOn = new Set(['APOIA','CONTRADIZ','CONCORRE_COM']);

/* parametros da simulacao e do desenho, todos ajustaveis no painel */
const cfg = {
  repulsao: 2600,      // quanto os nos se empurram
  mola: 0.0055,        // rigidez das arestas
  distancia: 128,      // comprimento de repouso da aresta
  gravidade: 0.0016,   // atracao ao centro
  atrito: 0.86,        // amortecimento (1 = sem atrito)
  tamanho: 1,          // multiplicador do raio dos nos
  rotArestas: 'auto',  // sempre | auto | nunca
  rotNos: 'auto',
  curvar: false,
  seta: true,
};
const LS = 'grafo-cfg';
try { Object.assign(cfg, JSON.parse(localStorage.getItem(LS) || '{}')); } catch(e){}
const salvar = () => { try { localStorage.setItem(LS, JSON.stringify(cfg)); } catch(e){} };

function corDe(n){
  if (n.label === 'Hipotese') return n.props.status === 'refutada' ? COR.HipoteseMorta : COR.Hipotese;
  if (n.label === 'Evidencia'){
    const c = n.props.confiabilidade;
    if (c === 'traducao_disputada') return COR.EvidenciaDisp;
    if (c === 'ambiguo') return COR.EvidenciaAmb;
    return COR.Evidencia;
  }
  return COR[n.label] || '#888';
}
const raio = n => cfg.tamanho * (n.label === 'Hipotese' ? 13 + (n.props.fatia||0)*26
                : n.label === 'Evidencia' ? 7
                : 8 + Math.min(n.grau,26)*0.28);

function relsVis(){
  return RELS.filter(r => tiposOn.has(r.tipo) && vis.has(r.de) && vis.has(r.para));
}
function vizinhos(id){
  const s = new Set();
  RELS.forEach(r => { if(!tiposOn.has(r.tipo)) return;
    if (r.de === id) s.add(r.para); if (r.para === id) s.add(r.de); });
  return s;
}
function mostrar(ids, origem){
  const o = origem && NOS.get(origem);
  ids.forEach(id => {
    const n = NOS.get(id); if(!n || vis.has(id)) return;
    const a = Math.random()*Math.PI*2, d = 90 + Math.random()*70;
    n.x = (o ? o.x : 0) + Math.cos(a)*d;
    n.y = (o ? o.y : 0) + Math.sin(a)*d;
    n.vx = n.vy = 0; n.nasceu = performance.now();
    vis.add(id);
  });
  atualizaContador();
}
function atualizaContador(){
  const c = document.getElementById('g-conta');
  if (c) c.textContent = `${vis.size} nós · ${relsVis().length} relações`;
}

/* ---------------- simulacao ---------------- */
function passo(){
  const ns = [...vis].map(id => NOS.get(id)).filter(Boolean);
  const rs = relsVis();
  for (let i=0;i<ns.length;i++){
    const a = ns[i];
    for (let j=i+1;j<ns.length;j++){
      const b = ns[j];
      let dx = b.x-a.x, dy = b.y-a.y, d2 = dx*dx+dy*dy;
      if (d2 < 1) { dx = Math.random()-.5; dy = Math.random()-.5; d2 = 1; }
      if (d2 > 360000) continue;
      const f = cfg.repulsao/d2, d = Math.sqrt(d2);
      const fx = dx/d*f, fy = dy/d*f;
      a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
    }
  }
  rs.forEach(r => {
    const a = NOS.get(r.de), b = NOS.get(r.para);
    const dx = b.x-a.x, dy = b.y-a.y, d = Math.hypot(dx,dy)||1;
    const alvo = r.tipo === 'CONCORRE_COM' ? cfg.distancia*1.64
               : (r.tipo === 'TEM_TEMA' || r.tipo === 'MENCIONA') ? cfg.distancia*0.94
               : cfg.distancia;
    const f = (d-alvo)*cfg.mola;
    const fx = dx/d*f, fy = dy/d*f;
    a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
  });
  ns.forEach(n => {
    n.vx -= n.x*cfg.gravidade; n.vy -= n.y*cfg.gravidade;
    if (n === arrastando) { n.vx = n.vy = 0; return; }
    n.vx *= cfg.atrito; n.vy *= cfg.atrito;
    n.x += Math.max(-9, Math.min(9, n.vx));
    n.y += Math.max(-9, Math.min(9, n.vy));
  });
}

/* ---------------- desenho ---------------- */
function tela(n){ return { x: cv.clientWidth/2 + (n.x+cam.x)*cam.z,
                           y: cv.clientHeight/2 + (n.y+cam.y)*cam.z }; }

function desenha(){
  const L = cv.clientWidth, A = cv.clientHeight, dpr = window.devicePixelRatio||1;
  if (cv.width !== L*dpr){ cv.width = L*dpr; cv.height = A*dpr; }
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.clearRect(0,0,L,A);

  const rs = relsVis();
  const viz = sel ? vizinhos(sel) : null;

  rs.forEach(r => {
    const a = NOS.get(r.de), b = NOS.get(r.para);
    const pa = tela(a), pb = tela(b);
    const foco = !sel || r.de === sel || r.para === sel;
    ctx.globalAlpha = foco ? 1 : 0.12;
    ctx.strokeStyle = CORREL[r.tipo] || '#999';
    ctx.lineWidth = ((r.props.peso ? 0.9 + r.props.peso*3.4 : 1.6)) * cam.z;
    if (r.tipo === 'CONCORRE_COM'){ ctx.setLineDash([5*cam.z, 5*cam.z]); } else ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(pa.x,pa.y); ctx.lineTo(pb.x,pb.y); ctx.stroke();
    ctx.setLineDash([]);
    // seta
    if (cfg.seta && r.tipo !== 'CONCORRE_COM'){
      const ang = Math.atan2(pb.y-pa.y, pb.x-pa.x), rb = raio(b)*cam.z+3;
      const px = pb.x-Math.cos(ang)*rb, py = pb.y-Math.sin(ang)*rb, s = 7*cam.z;
      ctx.fillStyle = CORREL[r.tipo]; ctx.beginPath();
      ctx.moveTo(px,py);
      ctx.lineTo(px-Math.cos(ang-0.42)*s, py-Math.sin(ang-0.42)*s);
      ctx.lineTo(px-Math.cos(ang+0.42)*s, py-Math.sin(ang+0.42)*s);
      ctx.closePath(); ctx.fill();
    }
    // rotulo da relacao: so com zoom ou foco, senao vira sopa
    const mostraRot = cfg.rotArestas === 'sempre' ? true
                    : cfg.rotArestas === 'nunca' ? false
                    : (cam.z > 0.85 || (sel && foco));
    if (mostraRot && ctx.globalAlpha > .5){
      const mx = (pa.x+pb.x)/2, my = (pa.y+pb.y)/2;
      const txt = r.props.peso ? `${r.tipo} ${r.props.peso}` : r.tipo;
      ctx.font = `700 ${9.5*Math.min(cam.z,1.5)}px "Space Mono",monospace`;
      const w = ctx.measureText(txt).width + 8;
      ctx.fillStyle = '#fff6e2'; ctx.strokeStyle = TINTA; ctx.lineWidth = 1.4;
      ctx.beginPath(); ctx.roundRect(mx-w/2, my-8, w, 15, 7); ctx.fill(); ctx.stroke();
      ctx.fillStyle = CORREL[r.tipo]; ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.fillText(txt, mx, my);
    }
  });

  ctx.globalAlpha = 1;
  [...vis].map(id=>NOS.get(id)).filter(Boolean)
    .sort((a,b)=>raio(a)-raio(b)).forEach(n => {
    const p = tela(n), r = raio(n)*cam.z;
    const nasc = n.nasceu ? Math.min(1,(performance.now()-n.nasceu)/380) : 1;
    const esc = 0.4 + 0.6*(1-Math.pow(1-nasc,3));
    const apagado = sel && n.id !== sel && viz && !viz.has(n.id);
    ctx.globalAlpha = apagado ? 0.2 : 1;
    ctx.beginPath(); ctx.arc(p.x, p.y, r*esc, 0, 6.284);
    ctx.fillStyle = corDe(n); ctx.fill();
    ctx.lineWidth = (n.id===sel?3.4:n.id===hover?2.8:2)*cam.z;
    ctx.strokeStyle = TINTA; ctx.stroke();
    if (n.props.orfao){ ctx.setLineDash([3*cam.z,3*cam.z]); ctx.lineWidth=1.6*cam.z;
      ctx.beginPath(); ctx.arc(p.x,p.y,r*esc+4*cam.z,0,6.284); ctx.stroke(); ctx.setLineDash([]); }
    const mostraNome = cfg.rotNos === 'sempre' ? true
                     : cfg.rotNos === 'nunca' ? false
                     : (cam.z > 0.55 || n.label === 'Hipotese');
    if (mostraNome){
      const t = n.nome;
      ctx.font = `700 ${Math.min(12*cam.z,15)}px "Space Mono",monospace`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'top';
      const w = ctx.measureText(t).width;
      ctx.fillStyle = 'rgba(255,246,226,.9)';
      ctx.fillRect(p.x-w/2-3, p.y+r*esc+3, w+6, 14*Math.min(cam.z,1.2));
      ctx.fillStyle = TINTA; ctx.fillText(t, p.x, p.y+r*esc+4);
    }
  });
  ctx.globalAlpha = 1;
}

function laco(){ if (!pausado) passo(); desenha(); requestAnimationFrame(laco); }

/* ---------------- interacao ---------------- */
function noEm(mx,my){
  let achado = null, melhor = 1e9;
  vis.forEach(id => {
    const n = NOS.get(id); if(!n) return;
    const p = tela(n), d = Math.hypot(p.x-mx, p.y-my);
    if (d < raio(n)*cam.z + 7 && d < melhor){ melhor = d; achado = n; }
  });
  return achado;
}
function seleciona(n){
  sel = n ? n.id : null;
  if (!n){ painel.innerHTML = '<p class="g-dica">Clique num nó para ver as propriedades. Duplo clique expande as ligações.</p>'; return; }
  const props = Object.entries(n.props)
    .filter(([k,v]) => v !== '' && v !== undefined && k !== 'orfao')
    .map(([k,v]) => {
      let val = String(v);
      if (k === 'fonte_url') val = `<a href="${v}" target="_blank" rel="noopener">abrir fonte</a>`;
      return `<div class="g-prop"><b>${k}</b><span>${val}</span></div>`;
    }).join('');
  const ligs = RELS.filter(r => (r.de===n.id||r.para===n.id) && tiposOn.has(r.tipo));
  const porTipo = {};
  ligs.forEach(r => { (porTipo[r.tipo] = porTipo[r.tipo]||[]).push(r); });
  const listaLigs = Object.entries(porTipo).map(([tipo, rr]) => `
    <div class="g-rel-grupo"><h5 style="color:${CORREL[tipo]}">:${tipo} · ${rr.length}</h5>
    ${rr.slice(0,14).map(r => {
      const outro = r.de===n.id ? r.para : r.de, no = NOS.get(outro);
      const dir = r.de===n.id ? '→' : '←';
      return `<div class="g-lig" data-ir="${outro}">${dir} <b>${no?no.nome:outro}</b>
        ${r.props.peso?`<i>peso ${r.props.peso}</i>`:''}
        ${r.props.como?`<span class="g-como">${r.props.como.slice(0,150)}${r.props.como.length>150?'…':''}</span>`:''}</div>`;
    }).join('')}${rr.length>14?`<div class="g-lig-mais">+ ${rr.length-14}</div>`:''}</div>`).join('');
  const link = n.label==='Evidencia' ? `<a class="g-ir" href="evidencias.html#${n.id}">ver no índice de evidências →</a>`
             : n.label==='Hipotese' ? `<a class="g-ir" href="index.html">ver dossiê completo →</a>` : '';
  painel.innerHTML = `<div class="g-lab" style="background:${corDe(n)}">${n.label}</div>
    <h4>${n.nome}</h4>${props}${link}
    <button id="g-expandir">expandir ligações</button>${listaLigs}`;
  const bt = document.getElementById('g-expandir');
  if (bt) bt.onclick = () => { mostrar([...vizinhos(n.id)], n.id); seleciona(n); };
  painel.querySelectorAll('[data-ir]').forEach(el => el.onclick = () => {
    const alvo = el.dataset.ir; mostrar([alvo], n.id); seleciona(NOS.get(alvo));
  });
  if (infoSel) infoSel.textContent = n.nome;
}

cv.addEventListener('mousemove', ev => {
  const r = cv.getBoundingClientRect(), mx = ev.clientX-r.left, my = ev.clientY-r.top;
  if (arrastando){
    arrastando.x = (mx - cv.clientWidth/2)/cam.z - cam.x;
    arrastando.y = (my - cv.clientHeight/2)/cam.z - cam.y;
    return;
  }
  if (panDe){ cam.x += (mx-panDe.x)/cam.z; cam.y += (my-panDe.y)/cam.z; panDe = {x:mx,y:my}; return; }
  const n = noEm(mx,my); hover = n?n.id:null; cv.style.cursor = n?'pointer':'grab';
});
cv.addEventListener('mousedown', ev => {
  const r = cv.getBoundingClientRect(), mx = ev.clientX-r.left, my = ev.clientY-r.top;
  const n = noEm(mx,my);
  if (n){ arrastando = n; seleciona(n); } else { panDe = {x:mx,y:my}; cv.style.cursor='grabbing'; }
});
window.addEventListener('mouseup', () => { arrastando = null; panDe = null; });
cv.addEventListener('dblclick', ev => {
  const r = cv.getBoundingClientRect();
  const n = noEm(ev.clientX-r.left, ev.clientY-r.top);
  if (n){ mostrar([...vizinhos(n.id)], n.id); seleciona(n); }
});
cv.addEventListener('wheel', ev => {
  ev.preventDefault();
  cam.z = Math.max(0.25, Math.min(3, cam.z * (ev.deltaY < 0 ? 1.12 : 0.89)));
}, {passive:false});

document.querySelectorAll('[data-tipo]').forEach(el => {
  el.addEventListener('change', () => {
    el.checked ? tiposOn.add(el.dataset.tipo) : tiposOn.delete(el.dataset.tipo);
    atualizaContador();
  });
});
/* ---------------- painel de parametros ---------------- */
function liga(id, chave, transf = Number){
  const el = document.getElementById(id);
  if (!el) return;
  if (el.type === 'checkbox') el.checked = !!cfg[chave]; else el.value = cfg[chave];
  const eco = document.querySelector(`[data-eco="${id}"]`);
  const pinta = () => { if (eco) eco.textContent = el.type === 'checkbox' ? '' : el.value; };
  pinta();
  el.addEventListener('input', () => {
    cfg[chave] = el.type === 'checkbox' ? el.checked : transf(el.value);
    pinta(); salvar();
  });
}
liga('c-repulsao','repulsao'); liga('c-mola','mola'); liga('c-dist','distancia');
liga('c-grav','gravidade'); liga('c-atrito','atrito'); liga('c-tam','tamanho');
liga('c-seta','seta');
['rotArestas','rotNos'].forEach(chave => {
  const el = document.getElementById(chave === 'rotArestas' ? 'c-rot-a' : 'c-rot-n');
  if (!el) return;
  el.value = cfg[chave];
  el.addEventListener('change', () => { cfg[chave] = el.value; salvar(); });
});
const btPausa = document.getElementById('g-pausa');
if (btPausa) btPausa.onclick = () => {
  pausado = !pausado;
  btPausa.textContent = pausado ? 'retomar' : 'pausar';
  btPausa.setAttribute('aria-pressed', String(pausado));
};
const btPadrao = document.getElementById('g-padrao');
if (btPadrao) btPadrao.onclick = () => {
  Object.assign(cfg, {repulsao:2600, mola:0.0055, distancia:128, gravidade:0.0016,
                      atrito:0.86, tamanho:1, rotArestas:'auto', rotNos:'auto', seta:true});
  salvar(); location.reload();
};

document.getElementById('g-reset').onclick = () => {
  vis = new Set(META.sementes); sel = null; cam = {x:0,y:0,z:1};
  NOS.forEach(n => { n.x = (Math.random()-.5)*300; n.y = (Math.random()-.5)*300; n.vx=n.vy=0; });
  seleciona(null); atualizaContador();
};
document.getElementById('g-tudo').onclick = () => {
  mostrar([...NOS.keys()].filter(id => NOS.get(id).label !== 'Tema' && NOS.get(id).label !== 'Ator'));
};
if (cxBusca) cxBusca.addEventListener('keydown', ev => {
  if (ev.key !== 'Enter') return;
  const q = cxBusca.value.toLowerCase().trim(); if(!q) return;
  const achou = [...NOS.values()].find(n =>
    n.nome.toLowerCase() === q || n.nome.toLowerCase().includes(q) ||
    JSON.stringify(n.props).toLowerCase().includes(q));
  if (achou){ mostrar([achou.id]); mostrar([...vizinhos(achou.id)], achou.id);
    seleciona(achou); cam.x = -achou.x; cam.y = -achou.y; }
});

fetch('grafo.json').then(r => r.json()).then(d => {
  d.nos.forEach(n => { n.x = (Math.random()-.5)*300; n.y = (Math.random()-.5)*300;
                       n.vx = n.vy = 0; NOS.set(n.id, n); });
  RELS = d.rels; META = d.meta;
  vis = new Set(META.sementes);
  seleciona(null); atualizaContador(); laco();
});
})();
