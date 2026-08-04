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
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Qatar' });
  }

  /* ─── Offline Banner (disabled — Django messages are the fallback) ── */
  function showOfflineBanner() {}
  function hideOfflineBanner() {}

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

    /* Edit own / Delete admin-only */
    const currentUser = me();
    const isOwn = isMine(data.sender_id);
    const editBtn = isOwn
      ? `<button type="button" class="hover:underline font-bold text-[10px] uppercase ${mine ? 'text-primary-foreground' : 'text-primary'}" onclick="NoteSphereChatEdit('${docId}','${escHtml(data.message || '')}')">Edit</button>`
      : '';
    const deleteBtn = currentUser.is_admin
      ? `<span>|</span><button type="button" class="hover:underline font-bold text-[10px] uppercase text-danger" onclick="NoteSphereChatDelete('${docId}')">Del</button>`
      : '';
    const actionBtns = (editBtn || deleteBtn)
      ? `<span>|</span>${editBtn}${deleteBtn}`
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
        mentioned.push(uid);
      }
    });
    return mentioned;
  }

  function createNotification(db, recipientId, type, msg, chatMsgId) {
    const currentUser = me();
    if (String(recipientId) === String(currentUser.id)) return; // no self-notify
    db.collection('notifications').add({
      recipient_id: String(recipientId),
      sender_id: String(currentUser.id),
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

    /* Don't clear Django-rendered messages — they are the fallback.
       Firestore listener will add new messages on top. */

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
        if (!currentUser.id || !window.NoteSphereFB || !window.NoteSphereFB.isReady) {
          /* Firebase not ready — fall back to Django POST */
          form.submit();
          return;
        }

        const db = window.NoteSphereFB.db;
        const mentions = parseMentions(text);
        let replyData = null;

        const parentId = parentInput?.value;
        if (parentId) {
          const parentEl = container.querySelector(`[data-msg-id="${parentId}"]`);
          const parentQuoteText = parentEl?.querySelector('p')?.textContent || '';
          replyData = { post_id: parentId, sender_id: null, content: parentQuoteText.substring(0, 100) };
        }

        const msgDoc = {
          sender_id: String(currentUser.id),
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

        /* Disable button while sending */
        const btn = form.querySelector('button[type="submit"]');
        if (btn) btn.disabled = true;

        db.collection('community_chat').add(msgDoc).then(docRef => {
          input.value = '';
          if (parentInput) parentInput.value = '';
          cancelReplyQuote();
          if (btn) btn.disabled = false;
          /* Mention notifications */
          mentions.forEach(uid => {
            createNotification(db, uid, 'mention',
              `${currentUser.full_name} mentioned you in Community Chat`, docRef.id);
          });
        }).catch(err => {
          console.warn('Firestore send failed, falling back to Django POST', err);
          if (btn) btn.disabled = false;
          /* Fall back to Django POST */
          form.submit();
        });
      });
    }

    /* ─── Notification bell listener ───────────────────── */
    const currentUser = me();
    if (currentUser.id) {
      db.collection('notifications')
        .where('recipient_id', '==', String(currentUser.id))
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

  window.NoteSphereChatEdit = function(docId, oldText) {
    if (!window.NoteSphereFB?.isReady) return;
    var newText = prompt('Edit message:', oldText);
    if (newText === null || newText.trim() === '' || newText === oldText) return;
    window.NoteSphereFB.db.collection('community_chat').doc(docId)
      .update({ message: newText.trim(), edited: true })
      .catch(e => console.warn('Edit err', e));
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
