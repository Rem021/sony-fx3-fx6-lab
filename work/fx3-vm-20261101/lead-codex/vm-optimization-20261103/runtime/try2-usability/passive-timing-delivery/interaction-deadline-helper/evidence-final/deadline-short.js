(async function installInteractionDeadline(config) {
  'use strict';
  const DEADLINE_MS = 1200;
  const KEY = '__fx3InteractionDeadlineV1';
  const SCRIPT_SHA = 'fe56b4846b9cb0c386216b38cc7e5b0707f616cab5ee6a526a217e68ce114478';
  const fail = message => { throw new Error('deadline_refused: ' + message); };
  if (!config || Object.keys(config).sort().join(',') !== 'expectedLaunchId,expectedURL') fail('config');
  const expected = new URL(config.expectedURL);
  if (expected.protocol !== 'http:' || expected.hostname !== '127.0.0.1' || !expected.port ||
      expected.pathname !== '/' || expected.search || expected.hash || expected.username || expected.password ||
      expected.href !== config.expectedURL || location.href !== config.expectedURL || window.top !== window) fail('exact_URL');
  if (!/^[0-9a-f-]{36}$/.test(config.expectedLaunchId)) fail('launch_identity');
  const doc = document, origin = performance.timeOrigin;
  const labels = {3:'↑ 上',21:'← 左',428:'确定',431:'右 →',48:'↓ 下',427:'MENU',504:'删除 / C4'};
  const one = selector => {
    const items = doc.querySelectorAll(selector);
    if (items.length !== 1) fail('DOM ' + selector);
    return items[0];
  };
  const end = one('#end'), start = one('#start'), confirm = one('#confirm');
  if (one('h1').textContent !== 'FX3 固件菜单试用' || doc.title !== 'FX3 固件菜单试用' ||
      end.tagName !== 'BUTTON' || end.textContent !== '结束试用' ||
      start.textContent !== '开始本轮模拟器' || confirm.textContent !== '我已看清当前完整画面，继续' ||
      one('#frame').tagName !== 'IMG' || one('#status').getAttribute('role') !== 'status' ||
      doc.querySelectorAll('.key').length !== 7 || typeof end.onclick !== 'function') fail('DOM schema');
  for (const [key, label] of Object.entries(labels)) {
    if (one('.key[data-key="' + key + '"]').textContent !== label) fail('key schema');
  }
  const scripts = [...doc.scripts];
  if (scripts.length !== 1 || scripts[0].src) fail('PAGE script');
  const script = scripts[0].textContent;
  if ((script.match(/^const token=[^\r\n]*;$/gm) || []).length !== 1) fail('PAGE token line');
  const canonical = script.replace(/^const token=[^\r\n]*;$/m, 'const token=__TOKEN__;');
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(canonical));
  const hash = [...new Uint8Array(digest)].map(x => x.toString(16).padStart(2, '0')).join('');
  if (hash !== SCRIPT_SHA) fail('PAGE fingerprint');
  const handler = end.onclick;
  function identity() {
    if (document !== doc || performance.timeOrigin !== origin || location.href !== config.expectedURL ||
        !end.isConnected || doc.querySelector('#end') !== end || end.onclick !== handler ||
        end.textContent !== '结束试用' || doc.querySelector('#start') !== start ||
        doc.querySelector('#confirm') !== confirm ||
        typeof lastStatus !== 'object' || !lastStatus || lastStatus.launch_request_id !== config.expectedLaunchId) fail('page_identity');
  }
  identity();
  if (window[KEY]) return window[KEY].status(); // Never replace or reset an existing alarm.
  const used = new Set(), events = [];
  let current = null, timer = null, sealed = false;
  const record = (event, extra = {}) => {
    const row = {event, wall_UTC: new Date().toISOString(), performance_ms: performance.now(), ...extra};
    events.push(row);
    return row;
  };
  function terminal() {
    return ending || finished || ['stopping', 'finished'].includes(lastStatus.phase);
  }
  function visible() {
    const r = end.getBoundingClientRect(), s = getComputedStyle(end);
    return !end.hidden && s.display !== 'none' && s.visibility === 'visible' && Number(s.opacity) > 0 &&
      r.width > 0 && r.height > 0 && r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth;
  }
  function status() {
    return {version:1, expectedURL:config.expectedURL, expectedLaunchId:config.expectedLaunchId,
      documentTimeOrigin:origin, deadline_ms:DEADLINE_MS, sealed,
      current:current && {...current}, events:events.map(x => ({...x}))};
  }
  function expire(nonce) {
    if (!current || current.nonce !== nonce || current.state !== 'armed') return;
    timer = null;
    current.state = 'expired';
    current.elapsed_ms = performance.now() - current.armed_ms;
    sealed = true; // No second stop attempt or new timer after expiration.
    try {
      identity();
      if (terminal() || end.disabled) {
        record('already_stopping_or_disabled', {nonce, elapsed_ms:current.elapsed_ms, phase:lastStatus.phase});
        return;
      }
      if (!visible()) fail('End not fully visible');
      record('end_click', {nonce, elapsed_ms:current.elapsed_ms});
      end.click(); // Only mutation: invoke this PAGE's original visible End handler.
    } catch (error) {
      record('expire_refused', {nonce, error:String(error)}); // Never click another document/control.
    }
  }
  const api = Object.freeze({
    arm(nonce) {
      identity();
      if (!/^[0-9a-f-]{36}$/.test(nonce)) fail('nonce');
      if (terminal()) { record('arm_refused_terminal', {nonce, phase:lastStatus.phase}); return status(); }
      if (sealed) fail('sealed');
      if (current && current.state === 'armed') {
        record(current.nonce === nonce ? 'duplicate_arm_no_extension' : 'different_arm_refused', {nonce});
        return status();
      }
      if (used.has(nonce)) fail('nonce_reuse');
      if (end.disabled || !visible() || lastStatus.phase !== 'ready') fail('End/phase not ready');
      used.add(nonce);
      current = {nonce, state:'armed', armed_ms:performance.now(), deadline_ms:DEADLINE_MS};
      current.due_ms = current.armed_ms + DEADLINE_MS;
      timer = setTimeout(() => expire(nonce), DEADLINE_MS);
      record('armed', {nonce, due_ms:current.due_ms});
      return status();
    },
    cancel(nonce) {
      identity();
      if (!current || current.state !== 'armed' || current.nonce !== nonce) {
        record('cancel_ignored_stale_or_inactive', {nonce});
        return status();
      }
      // A late callback cannot beat expiry merely because the event loop was blocked.
      if (performance.now() >= current.due_ms) { expire(nonce); return status(); }
      clearTimeout(timer); timer = null;
      current.state = 'cancelled';
      current.cancelled_ms = performance.now();
      record('cancelled', {nonce, elapsed_ms:current.cancelled_ms-current.armed_ms});
      return status();
    },
    status,
    dispose() {
      identity();
      if (current && current.state === 'armed') fail('cancel exact nonce before dispose');
      if (timer !== null) clearTimeout(timer);
      sealed = true;
      record('disposed');
      return status();
    }
  });
  Object.defineProperty(window, KEY, {value:api, writable:false, configurable:false});
  record('installed', {script_SHA256:hash});
  return status();
})
