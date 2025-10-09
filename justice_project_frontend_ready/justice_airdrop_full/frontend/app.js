// Use unified api helper functions from assets/api.js
const logoImg = document.getElementById('logo');
const contentFrame = document.getElementById('content-frame');
const welcomeVideo = document.getElementById('welcomeVideo');

async function init() {
  // fetch and set logo/video via helper
  try {
    const logo = await fetchLogo();
    if (logo && logoImg) logoImg.src = logo;
  } catch (e) { console.error(e); }

  try {
    const video = await fetchVideo();
    if (video) {
      if (welcomeVideo) {
        welcomeVideo.src = video;
        // ensure visible
        welcomeVideo.style.display = 'block'
        if (contentFrame) { contentFrame.style.display = 'none'; contentFrame.src = '' }
        // try to autoplay; if blocked, fallback to iframe
        try {
          const p = welcomeVideo.play()
          if (p && p.then) {
            p.catch(err => {
              console.warn('autoplay blocked, falling back to iframe', err)
              if (welcomeVideo) welcomeVideo.style.display = 'none'
              if (contentFrame) { contentFrame.style.display = 'block'; contentFrame.src = 'video/sonic.html' }
            })
          }
        } catch (err) {
          console.warn('video play call failed, showing iframe fallback', err)
          if (welcomeVideo) welcomeVideo.style.display = 'none'
          if (contentFrame) { contentFrame.style.display = 'block'; contentFrame.src = 'video/sonic.html' }
        }
      } else if (contentFrame) {
        contentFrame.src = video;
      }
    }
  } catch (e) { console.error(e); }

  // update notification badge periodically and show toasts for new notifications
  let lastCount = 0
  async function pollNotifs(){
    try{
      const c = await fetchNotificationCount()
      updateNotifCount(c)
      if(c > lastCount){
        // show toast for new notifications
        const container = document.querySelector('.toast-container') || (()=>{ const d=document.createElement('div'); d.className='toast-container'; document.body.appendChild(d); return d })()
        const t = document.createElement('div'); t.className='toast'; t.innerHTML = `<div class="title">New notification</div><div class="body">You have ${c} unread notification(s)</div>`
        container.prepend(t)
        requestAnimationFrame(()=> t.classList.add('show'))
        setTimeout(()=>{ t.classList.remove('show'); t.remove() }, 6000)
      }
      lastCount = c
    }catch(e){ console.error('pollNotifs', e) }
  }
  await pollNotifs()
  setInterval(pollNotifs, 30000)
}

// Notification popup bubble dashboard
function ensureNotifPopup(){
  let popup = document.getElementById('notifPopup')
  if(popup) return popup
  popup = document.createElement('div'); popup.id='notifPopup'; popup.className='notif-popup'; popup.style.display='none'
  const row = document.createElement('div'); row.className='bubble-row'; popup.appendChild(row)
  document.body.appendChild(popup)
  return popup
}

async function toggleNotifPopup(){
  const popup = ensureNotifPopup()
  if(popup.style.display === 'none'){
    // show and populate
    try{
      const data = await fetchNotifications(20)
      const row = popup.querySelector('.bubble-row')
      row.innerHTML = ''
      const items = (data || [])
      if(items.length === 0){ row.innerHTML = '<div class="empty">No notifications</div>' }
      // compact bubbles at top (auto-mark when clicked)
      const compact = document.createElement('div'); compact.className = 'bubble-row'; compact.style.marginBottom = '8px'
      const list = document.createElement('div'); list.style.maxHeight='260px'; list.style.overflow='auto'; list.style.display='flex'; list.style.flexDirection='column'; list.style.gap='6px'
      items.forEach(n => {
        // compact bubble
        const b = document.createElement('div'); b.className = 'notif-bubble'; b.setAttribute('data-id', n.id); b.title = n.message; b.textContent = '•'
        b.addEventListener('click', async ()=>{
          try{
            await apiFetch(`/notify/read_one/${n.id}`, { method: 'POST' })
            // remove from compact and list
            b.remove()
            const li = list.querySelector(`[data-id="${n.id}"]`)
            if(li) li.remove()
            await pollNotifs()
          }catch(err){ console.error('mark bubble', err) }
        })
        compact.appendChild(b)

        const item = document.createElement('div'); item.className='notif-item'; item.setAttribute('data-id', n.id)
        item.innerHTML = `<div style="display:flex;justify-content:space-between;gap:12px"><div style="flex:1">${n.message}</div><div style="margin-left:8px"><button data-id="${n.id}" class="mark-read-btn" style="background:transparent;border:1px solid rgba(255,255,255,0.04);padding:4px 8px;border-radius:4px;color:var(--muted)">Mark</button></div></div><div class="time">${new Date(n.created_at).toLocaleString()}</div>`
        list.appendChild(item)
      })
      row.appendChild(compact)
      // add mark-all button
      const controls = document.createElement('div'); controls.style.display='flex'; controls.style.justifyContent='flex-end'; controls.style.marginTop='8px'; controls.innerHTML = '<button id="markAllNotif" style="padding:6px 10px;border-radius:6px;background:linear-gradient(90deg,#22c1c3,#60d394);border:none;color:#042028;font-weight:700">Mark all read</button>'
      row.appendChild(list)
      row.appendChild(controls)
      // bind mark buttons
        row.querySelectorAll('.mark-read-btn').forEach(btn=> btn.addEventListener('click', async (e)=>{
        const id = btn.getAttribute('data-id')
        try{ await apiFetch(`/notify/read_one/${id}`, { method:'POST' }); btn.closest('.notif-item').remove(); await pollNotifs(); }catch(err){ console.error(err) }
      }))
      const markAll = document.getElementById('markAllNotif')
      if(markAll) markAll.addEventListener('click', async ()=>{ try{ const tg = window.currentUserId || '' ; await apiFetch(`/notify/read/${tg}`, { method:'POST' }); row.innerHTML = '<div class="empty">No notifications</div>'; await pollNotifs(); }catch(e){console.error(e)} })
    }catch(e){ console.error('toggleNotifPopup', e); popup.querySelector('.bubble-row').innerHTML = '<div class="empty">Error</div>' }
    popup.style.display = 'block'
  }else{
    popup.style.display = 'none'
  }
}

// bind bell if present
const bell = document.querySelector('.notification')
if(bell) bell.addEventListener('click', (e)=>{ e.preventDefault(); toggleNotifPopup() })

init();
