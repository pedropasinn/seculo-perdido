document.querySelectorAll('.hip-cab').forEach(b=>{
  b.addEventListener('click',()=>b.closest('.hip').classList.toggle('aberta'));
});
const cx=document.getElementById('busca'), fc=document.getElementById('filtro-conf'),
      ft=document.getElementById('filtro-tema'), lista=document.getElementById('lista-ev');
function filtra(){
  if(!lista) return;
  const q=(cx.value||'').toLowerCase().trim(), c=fc.value, t=ft.value;
  let n=0;
  lista.querySelectorAll('.ev-item').forEach(el=>{
    const ok = (!q || el.dataset.busca.includes(q))
            && (!c || el.dataset.conf===c)
            && (!t || el.dataset.temas.includes(t));
    el.style.display = ok?'':'none'; if(ok) n++;
  });
  document.getElementById('conta').textContent = n;
  document.getElementById('vazio').style.display = n?'none':'block';
}
[cx,fc,ft].forEach(el=>el&&el.addEventListener('input',filtra));
