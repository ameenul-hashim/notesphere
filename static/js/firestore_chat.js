/**
 * NoteSphere Cloud Firestore Chat
 * ─────────────────────────────────────────────────────────────────
 * • Paginates to most-recent 50 messages  (limit/startAfter)
 * • Resolves sender_id → profile via window.USER_REGISTRY (Neon)
 * • Writes mentions + reply notifications to `notifications` collection
 * • Graceful offline banner if Firestore cannot connect
 * ─────────────────────────────────────────────────────────────────
 */
(function () {
  'use strict';

  const PAGE_SIZE = 50;
  let oldestVisible = null;
  let unsubscribeChat = null;

  /* ─── Helpers ───────────────────────────────────────────────── */
  function resolveUser(id) {
    const reg = window.USER_REGISTRY || {};
    return reg[id] || { name: 'Unknown', avatar_url: '', role: 'STUDENT' };
  }

  function me() {
    return window.CURRENT_USER_JSON || {};
  }

  function isMine(senderId) {
    return String(senderId) === String(me().id);
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function formatTime(ts) {
    if (!ts) return '';
    const d = ts.toDate ? ts.toDate() : new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  /* ─── Offline Banner ────────────────────────────────────────── */
  function showOfflineBanner() {
    const container = document.getElementById('chat-messages-container');
    if (!container || document.getElementById('chat-offline-banner')) return;
    const banner = document.createElement('div');
    banner.id = 'chat-offline-banner';
    banner.className = 'flex items-center justify-center gap-2 py-3 px-4 bg-warning/10 border border-warning/30 rounded-xl text-xs text-warning font-semibold mx-2 my-3';
    banner.innerHTML = `
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 1l22 22M16.72 11.06A10.94 10.94 0 0 1 19 12.55M5 12.55a10.94 10.94 0 0 1 5.17-2.39M10.71 5.05A16 16 0 0 1 22.56 9M1.42 9a15.91 15.91 0 0 1 4.7-2.88M8.53 16.11a6 6 0 0 1 6.95 0M12 20h.01"/></svg>
      Chat is offline. Attempting to reconnect…
    `;
    container.insertBefore(banner, container.firstChild);
  }

  function hideOfflineBanner() {
    const banner = document.getElementById('chat-offline-banner');
    if (banner) banner.remove();
  }

  /* ─── Build message bubble DOM ──────────────────────────────── */
  function buildBubble(docId, data) {
    const mine = isMine(data.sender_id);
    const user = resolveUser(data.sender_id);
    const name = mine ? 'YOU' : escHtml(user.name);
    const role = user.role;
    const isAdmin = role === 'ADMIN';
    const time = formatTime(data.created_at);

    const outer = document.createElement('div');
    outer.className = 'flex flex-col space-y-1';
    outer.setAttribute('data-msg-id', docId);

    /* Hidden-if-deleted */
    if (data.deleted) {
      outer.innerHTML = `<div class="text-center text-[10px] text-muted italic py-1">[Message deleted]</div>`;
      return outer;
    }

    /* Avatar (non-mine only) */
    const avatarHtml = !mine && user.avatar_url
      ? `<div class="w-8 h-8 rounded-full overflow-hidden border border-border bg-surface-2 flex-shrink-0 mt-1 shadow-xs">
           <img src="${escHtml(user.avatar_url)}" alt="" class="w-full h-full object-cover">
         </div>`
      : '';

    /* Reply quote */
    const quoteHtml = data.reply_to
      ? `<div class="mb-2 p-2 rounded-xl text-xs border-l-4 ${mine ? 'border-white/80 bg-black/15 text-primary-foreground/95' : 'border-primary/80 bg-primary/10 text-foreground/90'} shadow-2xs">
           <div class="font-black text-[10px] uppercase tracking-wider mb-0.5 flex items-center gap-1">
             <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="9 17 4 12 9 7"/><path d="M20 18v-2a4 4 0 0 0-4-4H4"/></svg>
             <span>@${escHtml(resolveUser(data.reply_to.sender_id).name)}</span>
           </div>
           <p class="text-[11px] line-clamp-2 opacity-90 leading-tight italic">${escHtml(data.reply_to.content || '')}</p>
         </div>`
      : '';

    /* Admin badge */
    const adminBadge = isAdmin && !mine
      ? `<span class="badge badge-warning text-[9px] px-1 py-0">Admin</span>`
      : '';

    /* Edit/delete for own or admin */
    const currentUser = me();
    const canModify = isMine(data.sender_id) || currentUser.is_admin;
    const actionBtns = canModify
      ? `<span>|</span>
         <button type="button" class="hover:underline font-bold text-[10px] uppercase text-danger" onclick="NoteSphereChatDelete('${docId}')">Del</button>`
      : '';

    const bubbleColor = mine
      ? 'bg-primary text-primary-foreground rounded-tr-none border border-primary-hover/50 ml-auto'
      : 'bg-surface-2 text-foreground rounded-tl-none border border-border/90 mr-auto';

    const rowDir = mine ? 'justify-end' : 'justify-start';
    const headerColors = mine
      ? 'border-primary-foreground/20 text-primary-foreground/90'
      : 'border-border/60 text-muted';

    outer.innerHTML = `
      <div class="flex items-start gap-2.5 ${rowDir}">
        ${avatarHtml}
        <div class="group relative max-w-[88%] sm:max-w-[72%] p-3.5 rounded-2xl shadow-xs transition-all ${bubbleColor}">
          <div class="flex items-center justify-between gap-3 mb-1.5 text-[11px] border-b ${headerColors} pb-1">
            <div class="flex items-center gap-1.5 font-bold uppercase tracking-wider">
              <span class="font-black">${name}</span>
              ${adminBadge}
            </div>
            <div class="flex items-center gap-2 font-normal">
              <span>${time}</span>
              <button type="button"
                class="hover:underline font-bold text-[10px] uppercase ${mine ? 'text-primary-foreground' : 'text-primary'}"
                onclick="NoteSphereChatReply('${docId}','${escHtml(user.name)}','${escHtml((data.message || '').substring(0, 60))}')">
                @Reply
              </button>
              ${actionBtns}
            </div>
          </div>
          ${quoteHtml}
          <p class="text-xs sm:text-sm leading-relaxed whitespace-pre-wrap break-words font-medium">${escHtml(data.message || '')}</p>
          ${mine ? `<div class="flex justify-end mt-1 text-primary-foreground/70">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"></polyline><polyline points="22 10 13 19 11 17"></polyline>
            </svg></div>` : ''}
        </div>
      </div>`;

    return outer;
  }

  /* ─── Notification helpers ──────────────────────────────────── */
  function parseMentions(text) {
    const reg = window.USER_REGISTRY || {};
    const mentioned = [];
    Object.keys(reg).forEach(uid => {
      const name = reg[uid].name || '';
      if (name && text.toLowerCase().includes('@' + name.toLowerCase())) {
        mentioned.push(Number(uid));
      }
    });
    return mentioned;
  }

  function createNotification(db, recipientId, type, msg, chatMsgId) {
    const currentUser = me();
    if (String(recipientId) === String(currentUser.id)) return; // no self-notify
    db.collection('notifications').add({
      recipient_id: recipientId,
      sender_id: currentUser.id,
      type: type,
      message: msg,
      chat_message_id: chatMsgId,
      read: false,
      created_at: window.NoteSphereFB.serverTimestamp(),
    }).catch(e => console.warn('Notify err', e));
  }

  /* ─── Firestore Chat Listener ───────────────────────────────── */
  function initChat() {
    if (!window.NoteSphereFB || !window.NoteSphereFB.isReady) return;

    const db = window.NoteSphereFB.db;
    const container = document.getElementById('chat-messages-container');
    if (!container) return;

    /* Clear Django-rendered messages */
    container.innerHTML = `
      <div class="flex justify-center my-2">
        <span class="px-3.5 py-1 rounded-full bg-surface-2 border border-border/80 text-[11px] font-semibold text-muted shadow-xs">Live Discussion Stream</span>
      </div>
      <div id="load-more-wrapper" class="flex justify-center pb-2 hidden">
        <button id="load-more-btn" class="btn btn-xs btn-ghost border border-border rounded-xl text-xs">Load earlier messages</button>
      </div>`;

    const loadMoreWrapper = document.getElementById('load-more-wrapper');
    const loadMoreBtn = document.getElementById('load-more-btn');

    function listenQuery(query) {
      if (unsubscribeChat) unsubscribeChat();

      unsubscribeChat = query.onSnapshot(snapshot => {
        hideOfflineBanner();
        snapshot.docChanges().forEach(change => {
          const existing = container.querySelector(`[data-msg-id="${change.doc.id}"]`);

          if (change.type === 'added') {
            if (existing) return;
            const bubble = buildBubble(change.doc.id, change.doc.data());
            container.appendChild(bubble);
            if (!oldestVisible) oldestVisible = change.doc;
          }
          if (change.type === 'modified') {
            if (existing) existing.replaceWith(buildBubble(change.doc.id, change.doc.data()));
          }
          if (change.type === 'removed') {
            if (existing) existing.remove();
          }
        });
        container.scrollTop = container.scrollHeight;
      }, err => {
        console.warn('Chat snapshot error', err);
        showOfflineBanner();
      });
    }

    const initialQuery = db.collection('community_chat')
      .where('deleted', '==', false)
      .orderBy('created_at', 'asc')
      .limitToLast(PAGE_SIZE);

    listenQuery(initialQuery);

    /* Load earlier messages pagination */
    if (loadMoreBtn) {
      loadMoreBtn.addEventListener('click', () => {
        if (!oldestVisible) return;
        const olderQuery = db.collection('community_chat')
          .where('deleted', '==', false)
          .orderBy('created_at', 'asc')
          .endBefore(oldestVisible)
          .limitToLast(PAGE_SIZE);

        olderQuery.get().then(snap => {
          if (snap.empty) {
            loadMoreWrapper.classList.add('hidden');
            return;
          }
          const frag = document.createDocumentFragment();
          snap.docs.forEach(doc => {
            frag.appendChild(buildBubble(doc.id, doc.data()));
          });
          const firstMsg = container.querySelector('[data-msg-id]');
          if (firstMsg) {
            container.insertBefore(frag, firstMsg);
          } else {
            container.appendChild(frag);
          }
          oldestVisible = snap.docs[0];
          if (snap.size < PAGE_SIZE) loadMoreWrapper.classList.add('hidden');
        }).catch(e => console.warn('Load more err', e));
      });
      loadMoreWrapper.classList.remove('hidden');
    }

    /* ─── Send form ─────────────────────────────────────── */
    const form = document.getElementById('chat-send-form');
    if (form) {
      form.addEventListener('submit', e => {
        e.preventDefault();
        const input = document.getElementById('chat-content-input');
        const parentInput = document.getElementById('reply-parent-id');
        const text = (input?.value || '').trim();
        if (!text) return;

        const currentUser = me();
        const mentions = parseMentions(text);
        let replyData = null;

        const parentId = parentInput?.value;
        if (parentId) {
          const parentEl = container.querySelector(`[data-msg-id="${parentId}"]`);
          const parentQuoteText = parentEl?.querySelector('p')?.textContent || '';
          replyData = { post_id: parentId, sender_id: null, content: parentQuoteText.substring(0, 100) };
        }

        const msgDoc = {
          sender_id: currentUser.id,
          message: text,
          created_at: window.NoteSphereFB.serverTimestamp(),
          edited: false,
          deleted: false,
          reply_to: replyData || null,
          mentions: mentions,
          is_pinned: false,
          is_system: false,
          reactions: {},
        };

        db.collection('community_chat').add(msgDoc).then(docRef => {
          /* Mention notifications */
          mentions.forEach(uid => {
            createNotification(db, uid, 'mention',
              `${currentUser.full_name} mentioned you in Community Chat`, docRef.id);
          });
          /* Reply notification */
          if (replyData?.post_id && replyData?.sender_id) {
            createNotification(db, replyData.sender_id, 'reply',
              `${currentUser.full_name} replied to your message`, docRef.id);
          }
        }).catch(err => console.warn('Send err', err));

        input.value = '';
        if (parentInput) parentInput.value = '';
        cancelReplyQuote();
      });
    }

    /* ─── Notification bell listener ───────────────────── */
    const currentUser = me();
    if (currentUser.id) {
      db.collection('notifications')
        .where('recipient_id', '==', currentUser.id)
        .where('read', '==', false)
        .onSnapshot(snap => {
          const count = snap.size;
          const badge = document.getElementById('topbar-notif-badge');
          if (badge) {
            badge.textContent = count > 99 ? '99+' : count;
            badge.classList.toggle('hidden', count === 0);
          }
        }, err => console.warn('Notif listener err', err));
    }
  }

  /* ─── Global helpers exposed to HTML onclick attrs ─────────── */
  window.NoteSphereChatReply = function(postId, authorName, snippet) {
    const parentInput = document.getElementById('reply-parent-id');
    const quoteBar = document.getElementById('reply-quote-bar');
    const authorEl = document.getElementById('reply-quote-author');
    const textEl = document.getElementById('reply-quote-text');
    const contentInput = document.getElementById('chat-content-input');

    if (parentInput) parentInput.value = postId;
    if (authorEl) authorEl.textContent = '@' + authorName;
    if (textEl) textEl.textContent = `"${snippet}"`;
    if (quoteBar) quoteBar.classList.remove('hidden');
    if (contentInput) {
      if (!contentInput.value.includes('@' + authorName)) {
        contentInput.value = '@' + authorName + ' ' + contentInput.value;
      }
      contentInput.focus();
    }
  };

  window.NoteSphereChatDelete = function(docId) {
    if (!window.NoteSphereFB?.isReady) return;
    if (!confirm('Delete this message?')) return;
    window.NoteSphereFB.db.collection('community_chat').doc(docId)
      .update({ deleted: true })
      .catch(e => console.warn('Delete err', e));
  };

  window.cancelReplyQuote = function() {
    const parentInput = document.getElementById('reply-parent-id');
    const quoteBar = document.getElementById('reply-quote-bar');
    if (parentInput) parentInput.value = '';
    if (quoteBar) quoteBar.classList.add('hidden');
  };

  /* ─── Boot ─────────────────────────────────────────────────── */
  document.addEventListener('NoteSphereFBReady', initChat);
  if (window.NoteSphereFB?.isReady) initChat();
})();
