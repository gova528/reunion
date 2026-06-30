/* =====================================================================
   GRAND REUNION TOUR — APPLICATION LOGIC (vanilla ES6, no frameworks)
   ===================================================================== */

const App = {
  state: { user: null, page: "home", students: [], filterCity: "all" },

  async init() {
    this.injectMeshBackground();
    this.bindCursorGlow();
    this.bindNav();
    this.bindModals();
    await this.refreshUser();
    this.route(location.hash.replace("#", "") || "home");
    this.bindScrollReveal();
    this.startCountdown();
  },

  // ---------------- Background / Cursor ----------------
  injectMeshBackground() {
    const mesh = document.createElement("div");
    mesh.className = "mesh-bg";
    mesh.innerHTML = "<span></span><span></span><span></span><span></span>";
    document.body.prepend(mesh);
  },

  bindCursorGlow() {
    const glow = document.createElement("div");
    glow.id = "cursor-glow";
    document.body.appendChild(glow);
    window.addEventListener("mousemove", (e) => {
      glow.style.left = e.clientX + "px";
      glow.style.top = e.clientY + "px";
    });
  },

  bindScrollReveal() {
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && e.target.classList.add("visible")),
      { threshold: 0.12 }
    );
    document.querySelectorAll(".reveal").forEach((el) => io.observe(el));
  },

  // ---------------- Nav / Routing ----------------
  bindNav() {
    document.querySelectorAll("[data-route]").forEach((link) => {
      link.addEventListener("click", (e) => {
        e.preventDefault();
        this.route(link.dataset.route);
      });
    });
    window.addEventListener("popstate", () => this.route(location.hash.replace("#", "") || "home"));
  },

  async route(page) {
    this.state.page = page;
    location.hash = page;
    document.querySelectorAll(".nav-links a").forEach((a) => a.classList.toggle("active", a.dataset.route === page));
    const root = document.getElementById("view-root");
    root.classList.remove("page-view");
    const renderFn = this.views[page] || this.views.home;
    root.innerHTML = '<div class="grid grid-3"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>';
    const html = await renderFn.call(this);
    root.innerHTML = html;
    root.classList.add("page-view");
    this.bindScrollReveal();
    this.bindDynamicHandlers(page);
    window.scrollTo({ top: 0, behavior: "smooth" });
  },

  // ---------------- API helper ----------------
  async api(path, method = "GET", body) {
    const opts = { method, headers: { "Content-Type": "application/json" }, credentials: "include" };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(path, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
  },

  async refreshUser() {
    try {
      const data = await this.api("/api/me");
      this.state.user = data.user;
    } catch (e) {
      this.state.user = null;
    }
    this.renderAuthArea();
  },

  renderAuthArea() {
    const el = document.getElementById("auth-area");
    if (!el) return;
    if (this.state.user) {
      const roleLabel = this.state.user.role_id === 1 ? "Owner" : this.state.user.role_id === 2 ? "Admin" : "Member";
      el.innerHTML = `
        <span class="chip">${roleLabel}: ${this.state.user.full_name.split(" ")[0]}</span>
        <a href="#myprofile" data-route="myprofile" class="btn btn-ghost btn-sm">My Profile</a>
        ${this.state.user.role_id <= 2 ? '<a href="#admin" data-route="admin" class="btn btn-ghost btn-sm">Admin</a>' : ""}
        <button class="btn btn-ghost btn-sm" id="logout-btn">Logout</button>`;
      document.getElementById("logout-btn").onclick = async () => {
        await this.api("/api/logout", "POST");
        this.state.user = null;
        this.renderAuthArea();
        this.route("home");
        this.toast("Logged out successfully", "info");
      };
      el.querySelectorAll("[data-route]").forEach((link) => {
        link.addEventListener("click", (e) => {
          e.preventDefault();
          this.route(link.dataset.route);
        });
      });
    } else {
      el.innerHTML = `<button class="btn btn-primary btn-sm" id="login-open">Login</button>`;
      document.getElementById("login-open").onclick = () => this.openModal("modal-login");
    }
  },

  // ---------------- Toasts ----------------
  toast(message, type = "info") {
    const stack = document.getElementById("toast-stack");
    const el = document.createElement("div");
    el.className = "toast glass-soft";
    const colors = { success: "🌟", error: "⚠️", info: "✨" };
    el.innerHTML = `<span>${colors[type] || "✨"}</span><span>${message}</span>`;
    stack.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      el.style.transform = "translateX(40px)";
      setTimeout(() => el.remove(), 350);
    }, 3200);
  },

  // ---------------- Modals ----------------
  bindModals() {
    document.querySelectorAll(".modal-overlay").forEach((overlay) => {
      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) overlay.classList.remove("open");
      });
      overlay.querySelectorAll(".modal-close").forEach((btn) => (btn.onclick = () => overlay.classList.remove("open")));
    });

    document.getElementById("login-form").onsubmit = async (e) => {
      e.preventDefault();
      const email = document.getElementById("login-email").value;
      const password = document.getElementById("login-password").value;
      try {
        await this.api("/api/login", "POST", { email, password });
        this.closeModal("modal-login");
        await this.refreshUser();
        this.toast("Welcome back!", "success");
        this.route(this.state.page);
      } catch (err) {
        this.toast(err.message, "error");
      }
    };
  },

  openModal(id) {
    document.getElementById(id).classList.add("open");
  },
  closeModal(id) {
    document.getElementById(id).classList.remove("open");
  },

  // ---------------- Countdown ----------------
  async startCountdown() {
    let target;
    try {
      const s = await this.api("/api/settings");
      target = new Date(s.reunion_date || "2026-12-19T18:00:00");
    } catch (e) {
      target = new Date("2026-12-19T18:00:00");
    }
    const tick = () => {
      const el = document.getElementById("countdown");
      if (!el) return;
      const diff = Math.max(0, target - new Date());
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s2 = Math.floor((diff % 60000) / 1000);
      el.innerHTML = ["DAYS", "HRS", "MIN", "SEC"]
        .map((label, i) => `<div class="unit"><b>${[d, h, m, s2][i]}</b><span>${label}</span></div>`)
        .join("");
    };
    tick();
    setInterval(tick, 1000);
  },

  // ---------------- Dynamic handlers per page ----------------
  bindDynamicHandlers(page) {
    if (page === "directory") this.bindDirectoryHandlers();
    if (page === "gallery") this.bindGalleryHandlers();
    if (page === "events") this.bindEventsHandlers();
    if (page === "board") this.bindBoardHandlers();
    if (page === "lostfound") this.bindLostFoundHandlers();
    if (page === "admin") this.bindAdminHandlers();
    if (page === "myprofile") this.bindProfileHandlers();
  },

  bindDirectoryHandlers() {
    const searchInput = document.getElementById("student-search");
    if (searchInput) {
      searchInput.addEventListener("input", async (e) => {
        const data = await this.api("/api/students?q=" + encodeURIComponent(e.target.value));
        document.getElementById("student-results").innerHTML = this.renderStudentCards(data.students);
      });
    }
  },

  bindGalleryHandlers() {
    document.querySelectorAll(".photo-tile").forEach((tile) => {
      tile.addEventListener("click", () => {
        document.getElementById("lightbox-img").textContent = tile.dataset.caption || "Memory";
        document.getElementById("lightbox").classList.add("open");
      });
    });
    const closeBtn = document.getElementById("lightbox-close-btn");
    if (closeBtn) closeBtn.onclick = () => document.getElementById("lightbox").classList.remove("open");
  },

  bindEventsHandlers() {
    document.querySelectorAll("[data-rsvp]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        if (!this.state.user) return this.openModal("modal-login");
        try {
          await this.api("/api/rsvp", "POST", { event_id: btn.dataset.eventId, status: btn.dataset.rsvp, guests: 1 });
          this.toast("RSVP saved — see you there!", "success");
        } catch (err) {
          this.toast(err.message, "error");
        }
      });
    });
  },

  bindBoardHandlers() {
    const form = document.getElementById("message-form");
    if (form) {
      form.onsubmit = async (e) => {
        e.preventDefault();
        if (!this.state.user) return this.openModal("modal-login");
        const input = document.getElementById("message-input");
        try {
          await this.api("/api/messages/post", "POST", { body: input.value });
          input.value = "";
          this.route("board");
        } catch (err) {
          this.toast(err.message, "error");
        }
      };
    }
  },

  bindLostFoundHandlers() {
    const form = document.getElementById("lostfound-form");
    if (form) {
      form.onsubmit = async (e) => {
        e.preventDefault();
        if (!this.state.user) return this.openModal("modal-login");
        const item = document.getElementById("lf-item").value;
        const desc = document.getElementById("lf-desc").value;
        try {
          await this.api("/api/lostfound/create", "POST", { item_name: item, description: desc, status: "lost" });
          this.toast("Posted to Lost & Found", "success");
          this.route("lostfound");
        } catch (err) {
          this.toast(err.message, "error");
        }
      };
    }
  },

  bindProfileHandlers() {
    const form = document.getElementById("profile-form");
    if (!form) return;
    form.onsubmit = async (e) => {
      e.preventDefault();
      try {
        const payload = {
          full_name: document.getElementById("pf-name").value,
          city: document.getElementById("pf-city").value,
          profession: document.getElementById("pf-profession").value,
          company: document.getElementById("pf-company").value,
          phone: document.getElementById("pf-phone").value,
          bio: document.getElementById("pf-bio").value,
          quote: document.getElementById("pf-quote").value,
          school_memory: document.getElementById("pf-memory").value,
          avatar_then: document.getElementById("pf-then").value,
          avatar_now: document.getElementById("pf-now").value,
        };
        await this.api("/api/profile/update", "POST", payload);
        await this.refreshUser();
        this.toast("Profile updated!", "success");
      } catch (err) {
        this.toast(err.message, "error");
      }
    };
  },

  bindAdminHandlers() {
    const form = document.getElementById("invite-form");
    if (form) {
      form.onsubmit = async (e) => {
        e.preventDefault();
        const email = document.getElementById("invite-email").value;
        try {
          const res = await this.api("/api/invitations/create", "POST", { email, expires_hours: 72 });
          const fullUrl = location.origin + res.invite_url;
          await this.route("admin");
          const box = document.getElementById("latest-invite-url");
          if (box) box.innerHTML = `<a href="${res.invite_url}" target="_blank">${fullUrl}</a>`;
          navigator.clipboard?.writeText(fullUrl).then(
            () => this.toast("Invite link generated and copied to clipboard", "success"),
            () => this.toast("Invite link generated — copy it below", "success")
          );
        } catch (err) {
          this.toast(err.message, "error");
        }
      };
    }
  },

  renderStudentCards(students) {
    if (!students.length) return `<p style="color:var(--text-2)">No classmates found.</p>`;
    return `<div class="grid grid-4">${students
      .map(
        (s) => `
      <div class="glass card student-card reveal">
        <div class="avatar-ring">${s.full_name.split(" ").map((n) => n[0]).join("").slice(0, 2)}</div>
        <h4>${s.full_name}</h4>
        <div class="meta">${s.profession || "Classmate"} ${s.company ? "· " + s.company : ""}</div>
        <div class="meta">📍 ${s.city || "Unknown"}</div>
        ${s.school_memory ? `<p style="font-size:.78rem; color:var(--text-2); margin-top:10px;">"${s.school_memory}"</p>` : ""}
      </div>`
      )
      .join("")}</div>`;
  },

  // ===================================================================
  // VIEWS
  // ===================================================================
  views: {
    async home() {
      let announcements = [];
      try {
        announcements = (await App.api("/api/announcements")).announcements;
      } catch (e) {}
      return `
      <div class="hero glass reveal">
        <h1>Welcome back to <span class="gold-text">Grand Reunion Tour</span><br/>Class of 2006–2007</h1>
        <p>Two decades of stories, friendships and unforgettable memories — together again.</p>
        <div id="countdown" class="countdown"></div>
        <div class="hero-actions">
          <a href="#directory" data-route="directory" class="btn btn-primary">Find Classmates</a>
          <a href="#events" data-route="events" class="btn btn-ghost">View Events &amp; RSVP</a>
        </div>
      </div>

      <div class="marquee-wrap glass-soft">
        <div class="marquee">
          <span>🎓 Welcome to GRT 2026</span><span>📅 Reunion Night — December 19, 2026</span>
          <span>📸 Upload your memories to the Gallery</span><span>💬 Say hello on the Message Board</span>
          <span>🎓 Welcome to GRT 2026</span><span>📅 Reunion Night — December 19, 2026</span>
          <span>📸 Upload your memories to the Gallery</span><span>💬 Say hello on the Message Board</span>
        </div>
      </div>

      <h2 class="section-title reveal">Recent Announcements</h2>
      <p class="section-sub reveal">Stay up to date with the latest reunion news.</p>
      <div class="grid grid-2">
        ${announcements
          .map(
            (a) => `<div class="glass card reveal">
              <h4>${a.pinned ? "📌 " : ""}${a.title}</h4>
              <p style="color:var(--text-2); font-size:.88rem; margin-top:8px;">${a.body}</p>
            </div>`
          )
          .join("") || '<p style="color:var(--text-2)">No announcements yet.</p>'}
      </div>

      <h2 class="section-title reveal" style="margin-top:40px;">Quick Actions</h2>
      <div class="grid grid-4">
        <a href="#directory" data-route="directory" class="glass card quick-action reveal"><div class="icon">🧑‍🤝‍🧑</div>Directory</a>
        <a href="#gallery" data-route="gallery" class="glass card quick-action reveal"><div class="icon">🖼️</div>Gallery</a>
        <a href="#events" data-route="events" class="glass card quick-action reveal"><div class="icon">🎉</div>Events</a>
        <a href="#board" data-route="board" class="glass card quick-action reveal"><div class="icon">💬</div>Message Board</a>
      </div>`;
    },

    async myprofile() {
      if (!App.state.user) {
        return `<div class="glass card reveal" style="max-width:480px; margin:40px auto; text-align:center;">
          <h3>Please log in</h3>
          <p style="color:var(--text-2); margin-top:8px;">Log in to view and edit your profile.</p>
        </div>`;
      }
      const me = App.state.user;
      return `
      <h2 class="section-title reveal">My Profile</h2>
      <p class="section-sub reveal">Add your details so old friends can find and recognize you.</p>
      <form id="profile-form" class="glass card reveal" style="max-width:600px; display:flex; flex-direction:column; gap:14px;">
        <div class="field"><label>Full Name</label><input id="pf-name" value="${me.full_name || ""}" /></div>
        <div class="field"><label>City</label><input id="pf-city" value="${me.city || ""}" /></div>
        <div class="field"><label>Profession</label><input id="pf-profession" value="${me.profession || ""}" /></div>
        <div class="field"><label>Company</label><input id="pf-company" value="${me.company || ""}" /></div>
        <div class="field"><label>Phone</label><input id="pf-phone" value="${me.phone || ""}" /></div>
        <div class="field"><label>Bio</label><textarea id="pf-bio" rows="3">${me.bio || ""}</textarea></div>
        <div class="field"><label>Favorite Quote</label><input id="pf-quote" value="${me.quote || ""}" /></div>
        <div class="field"><label>A School Memory</label><textarea id="pf-memory" rows="2">${me.school_memory || ""}</textarea></div>
        <div class="field"><label>"Then" Photo URL (2006)</label><input id="pf-then" value="${me.avatar_then || ""}" placeholder="https://..." /></div>
        <div class="field"><label>"Now" Photo URL (2026)</label><input id="pf-now" value="${me.avatar_now || ""}" placeholder="https://..." /></div>
        <button class="btn btn-primary" type="submit">Save Profile</button>
      </form>`;
    },
    async directory() {
      const data = await App.api("/api/students");
      App.state.students = data.students;
      return `
      <h2 class="section-title reveal">Student Directory</h2>
      <p class="section-sub reveal">Search the batch of 2006–2007 and reconnect.</p>
      <div class="glass search-bar reveal">
        <span>🔍</span>
        <input id="student-search" placeholder="Search by name or city..." />
      </div>
      <div class="chip-row reveal">
        <div class="chip active">All</div><div class="chip">Bengaluru</div><div class="chip">Mumbai</div>
        <div class="chip">Hyderabad</div><div class="chip">Delhi</div>
      </div>
      <div id="student-results">${App.renderStudentCards(data.students)}</div>`;
    },

    async gallery() {
      let albums = [];
      try { albums = (await App.api("/api/albums")).albums; } catch (e) {}
      const tiles = Array.from({ length: 8 }, (_, i) => i + 1);
      return `
      <h2 class="section-title reveal">Memory Lane — Gallery</h2>
      <p class="section-sub reveal">Then (2006) &amp; Now (2026) — relive the moments. Albums: ${
        albums.map((a) => a.title).join(", ") || "Then & Now"
      }</p>
      <div class="then-now reveal">
        <button class="active">Then · 2006</button><button>Now · 2026</button>
      </div>
      <div class="gallery-grid reveal">
        ${tiles
          .map(
            (i) => `<div class="photo-tile" data-caption="Reunion memory #${i}"><span class="ph-icon">🖼️</span></div>`
          )
          .join("")}
      </div>
      <div class="lightbox" id="lightbox">
        <div class="lightbox-inner glass" style="padding:30px 40px;">
          <button class="lightbox-close" id="lightbox-close-btn">✕</button>
          <div id="lightbox-img" style="font-size:1.2rem; color:var(--gold-soft);"></div>
        </div>
      </div>`;
    },

    async events() {
      let events = [];
      try { events = (await App.api("/api/events")).events; } catch (e) {}
      return `
      <h2 class="section-title reveal">Events Timeline</h2>
      <p class="section-sub reveal">RSVP and view hotel &amp; venue details.</p>
      <div class="timeline">
        ${events
          .map(
            (e) => `<div class="glass timeline-item reveal">
              <h4>${e.title}</h4>
              <p style="color:var(--text-2); font-size:.85rem; margin:8px 0;">${e.description || ""}</p>
              <p style="font-size:.8rem;">📍 ${e.venue || "TBA"} &nbsp; 🕗 ${new Date(e.starts_at).toLocaleString()}</p>
              ${e.hotel_name ? `<p style="font-size:.8rem; color:var(--text-2);">🏨 ${e.hotel_name} — ${e.hotel_details || ""}</p>` : ""}
              <div style="margin-top:14px; display:flex; gap:10px;">
                <button class="btn btn-primary btn-sm" data-rsvp="going" data-event-id="${e.id}">Going</button>
                <button class="btn btn-ghost btn-sm" data-rsvp="maybe" data-event-id="${e.id}">Maybe</button>
                <button class="btn btn-ghost btn-sm" data-rsvp="not_going" data-event-id="${e.id}">Can't make it</button>
              </div>
            </div>`
          )
          .join("") || '<p style="color:var(--text-2)">No events scheduled yet.</p>'}
      </div>`;
    },

    async board() {
      let messages = [];
      try { messages = (await App.api("/api/messages")).messages; } catch (e) {}
      return `
      <h2 class="section-title reveal">Message Board</h2>
      <p class="section-sub reveal">Share a memory, leave a note for the batch.</p>
      <form id="message-form" class="glass card reveal" style="margin-bottom:24px; display:flex; gap:10px;">
        <input id="message-input" placeholder="Write something for the batch..." required
          style="flex:1; background:transparent; border:1px solid var(--glass-border); border-radius:30px; padding:10px 16px; color:var(--text-1);" />
        <button class="btn btn-primary" type="submit">Post</button>
      </form>
      ${messages
        .map(
          (m) => `<div class="glass message-item reveal">
            <div class="author">${m.full_name}</div>
            <div class="time">${new Date(m.created_at).toLocaleString()}</div>
            <p style="margin-top:8px;">${m.body}</p>
          </div>`
        )
        .join("") || '<p style="color:var(--text-2)">No messages yet — be the first!</p>'}`;
    },

    async lostfound() {
      let items = [];
      try { items = (await App.api("/api/lostfound")).items; } catch (e) {}
      return `
      <h2 class="section-title reveal">Lost &amp; Found</h2>
      <p class="section-sub reveal">Misplaced something at the reunion? Post it here.</p>
      <form id="lostfound-form" class="glass card reveal" style="margin-bottom:24px;">
        <div class="field"><label>Item name</label><input id="lf-item" required /></div>
        <div class="field"><label>Description</label><textarea id="lf-desc" rows="2"></textarea></div>
        <button class="btn btn-primary" type="submit">Post Item</button>
      </form>
      <div class="grid grid-3">
        ${items
          .map(
            (i) => `<div class="glass card reveal">
              <h4>${i.item_name}</h4>
              <p style="color:var(--text-2); font-size:.85rem; margin-top:6px;">${i.description || ""}</p>
              <span class="chip" style="margin-top:10px; display:inline-block;">${i.status}</span>
            </div>`
          )
          .join("") || '<p style="color:var(--text-2)">Nothing reported yet.</p>'}
      </div>`;
    },

    async careers() {
      let careers = [];
      try { careers = (await App.api("/api/careers")).careers; } catch (e) {}
      return `
      <h2 class="section-title reveal">Career Opportunities</h2>
      <p class="section-sub reveal">Posted by your batchmates.</p>
      <div class="grid grid-2">
        ${careers
          .map(
            (c) => `<div class="glass card reveal">
              <h4>${c.title}</h4>
              <p style="color:var(--text-2); font-size:.85rem;">${c.company || ""} ${c.location ? "· " + c.location : ""}</p>
              <p style="font-size:.85rem; margin-top:8px;">${c.description || ""}</p>
            </div>`
          )
          .join("") || '<p style="color:var(--text-2)">No openings posted yet.</p>'}
      </div>`;
    },

    async admin() {
      if (!App.state.user || App.state.user.role_id !== 1) {
        return `<div class="glass card reveal" style="text-align:center; padding:50px;">
          <h3>Owner Access Only</h3>
          <p style="color:var(--text-2); margin:14px 0;">Please log in as the Owner to access the Admin Dashboard.</p>
          <button class="btn btn-primary" onclick="App.openModal('modal-login')">Login</button>
        </div>`;
      }
      let invitations = [];
      try { invitations = (await App.api("/api/invitations")).invitations; } catch (e) {}
      return `
      <h2 class="section-title reveal">Owner Admin Dashboard</h2>
      <p class="section-sub reveal">Manage invitations, users and reunion settings.</p>

      <div class="glass card reveal" style="margin-bottom:24px;">
        <h3>Magic Invitation Generator</h3>
        <form id="invite-form" style="display:flex; gap:10px; margin-top:14px; flex-wrap:wrap;">
          <input id="invite-email" placeholder="classmate@example.com (optional)"
            style="flex:1; min-width:200px; background:transparent; border:1px solid var(--glass-border); border-radius:30px; padding:10px 16px; color:var(--text-1);" />
          <button class="btn btn-primary" type="submit">Generate Invite Link</button>
        </form>
        <p id="latest-invite-url" style="margin-top:14px; font-size:.85rem; word-break:break-all; color:var(--gold-soft);"></p>
      </div>

      <h3 class="reveal" style="margin-bottom:14px;">Invitation History</h3>
      <div class="grid grid-2">
        ${invitations
          .map(
            (i) => `<div class="glass card reveal">
              <p style="font-size:.8rem; word-break:break-all;">🔗 <a href="/invite.html?token=${i.token}" target="_blank" style="color:var(--gold-soft); text-decoration:underline;">${location.origin}/invite.html?token=${i.token}</a></p>
              <p style="font-size:.78rem; color:var(--text-2); margin-top:6px;">
                ${i.email || "Open invite"} · ${i.used_by ? "✅ Used" : i.revoked ? "🚫 Revoked" : "🕒 Pending"}
              </p>
            </div>`
          )
          .join("") || '<p style="color:var(--text-2)">No invitations generated yet.</p>'}
      </div>`;
    },
  },
};

document.addEventListener("DOMContentLoaded", () => App.init());

// Magnetic + ripple effects for all buttons
document.addEventListener("mousemove", (e) => {
  document.querySelectorAll(".magnetic").forEach((el) => {
    const rect = el.getBoundingClientRect();
    const dx = e.clientX - (rect.left + rect.width / 2);
    const dy = e.clientY - (rect.top + rect.height / 2);
    const dist = Math.hypot(dx, dy);
    if (dist < 80) {
      el.style.transform = `translate(${dx * 0.15}px, ${dy * 0.15}px)`;
    } else {
      el.style.transform = "translate(0,0)";
    }
  });
});

document.addEventListener("click", (e) => {
  const btn = e.target.closest(".btn");
  if (!btn) return;
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  const rect = btn.getBoundingClientRect();
  ripple.style.left = e.clientX - rect.left + "px";
  ripple.style.top = e.clientY - rect.top + "px";
  ripple.style.width = ripple.style.height = "10px";
  btn.appendChild(ripple);
  setTimeout(() => ripple.remove(), 650);
});
