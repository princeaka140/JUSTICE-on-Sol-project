
function openPage(page) {
  const frame = document.getElementById("content-frame");
  if (!frame) return;
  frame.style.opacity = 0;
  setTimeout(() => {
    frame.src = page;
    frame.onload = () => frame.style.opacity = 1;
  }, 200);
}

// update badge every 10s
async function updateNotifCount() {
  try {
    const el = document.getElementById('notif-count');
    if (!el) return;
    const c = await fetchNotificationCount();
    el.textContent = c || 0;
  } catch (e) { console.error(e); }
}

setInterval(updateNotifCount, 10000);
