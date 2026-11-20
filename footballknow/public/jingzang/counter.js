/* Count one homepage opening. Retrying the same request cannot count twice. */
window.jingzangCountVisit = async function (target) {
  if (!target) return;
  const event = crypto.randomUUID();
  try {
    const response = await fetch('/api/visits', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event }), keepalive: true, cache: 'no-store'
    });
    if (!response.ok) throw new Error('counter unavailable');
    const data = await response.json();
    if (!Number.isSafeInteger(data.total) || data.total < 0) throw new Error('invalid count');
    target.textContent = data.total.toLocaleString('zh-CN');
  } catch {
    target.textContent = '暂未更新';
  }
};
