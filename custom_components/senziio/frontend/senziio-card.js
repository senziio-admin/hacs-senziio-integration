/* pick device via registry */
class SenziioCardEditor extends HTMLElement {
  setConfig(cfg) { this._cfg = { device: "", title: "", ...cfg }; this._render(); }
  set hass(h)    { this._hass = h; this._ensureLoaded(); }

  async _ensureLoaded() {
    if (!this._hass || this._devices) { this._render(); return; }
    try {
      // load device registry
      const all = await this._hass.callWS({ type: "config/device_registry/list" });
      this._devices = all.filter(d => (d.manufacturer || "").toLowerCase().includes("senziio"));
      if (this._devices.length === 0) this._devices = all; // fallback: show all devices
    } catch (e) {
      console.error("Senziio editor: device registry error", e);
      this._devices = [];
    }
    this._render();
  }

  _render() {
    if (!this.isConnected) return;
    this.innerHTML = "";
    const wrap = document.createElement("div");
    wrap.style.padding = "8px 0";

    if (!this._hass) {
      wrap.textContent = "Loading…";
      this.appendChild(wrap);
      return;
    }

    const label = document.createElement("label");
    label.textContent = "Pick a Senziio device";
    label.style.display = "block";
    label.style.margin = "0 0 6px";
    wrap.appendChild(label);

    const sel = document.createElement("select");
    sel.style.width = "100%";
    sel.addEventListener("change", (e) => this._picked(e.target.value));

    const opt0 = document.createElement("option");
    opt0.textContent = "— select —";
    opt0.value = "";
    opt0.disabled = true;
    opt0.selected = !this._cfg?.device;
    sel.appendChild(opt0);

    (this._devices || []).forEach((d) => {
      const name = d.name_by_user || d.name || d.id;
      const opt = document.createElement("option");
      opt.value = d.id;
      opt.selected = d.id === this._cfg?.device;
      opt.textContent = `${name} (${d.manufacturer || "?"} ${d.model || ""})`;
      sel.appendChild(opt);
    });

    wrap.appendChild(sel);
    this.appendChild(wrap);
  }

  _picked(deviceId) {
    const cfg = { ...this._cfg, device: deviceId };
    this._cfg = cfg;
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config: cfg } }));
  }
}
customElements.define("senziio-card-editor", SenziioCardEditor);

class SenziioCard extends HTMLElement {
  static getConfigElement() { return document.createElement("senziio-card-editor"); }
  static getStubConfig()    { return { device: "" }; }

  setConfig(cfg) {
    this._cfg = { device: "", title: "", ...cfg };
    this._inner = undefined;
    this._builtFor = undefined;
    this._build();
  }

  set hass(h) {
    this._hass = h;
    if (this._inner) this._inner.hass = h;
    if (!this._inner && (this._cfg?.device || this._cfg?.sensor)) this._build();
  }

  async _build() {
    // Show placeholder until we have config + hass
    if (!this._hass || (!this._cfg?.device && !this._cfg?.sensor)) {
      return this._placeholder("Select a device in the editor");
    }

    try {
      const entReg = await this._hass.callWS({ type: "config/entity_registry/list" });

      let deviceId = this._cfg.device;
      if (!deviceId && this._cfg.sensor) {
        const anchor = entReg.find(e => e.entity_id === this._cfg.sensor);
        deviceId = anchor?.device_id;
      }
      if (!deviceId) return this._placeholder("Cannot resolve device.");

      if (this._builtFor === deviceId && this._inner) return;

      // all entities of that device_id
      let entityIds = entReg.filter(e => e.device_id === deviceId)
                            .map(e => e.entity_id);

      // build config for the official entities card
      const device = (await this._hass.callWS({ type: "config/device_registry/list" }))
                       .find(d => d.id === deviceId);
      const title = this._cfg.title || device?.name_by_user || device?.name || "Senziio device";
      const cfg = { type: "entities", title, entities: entityIds };

      // Create the official card
      const helpers = await (window.loadCardHelpers?.());
      const card = helpers
        ? helpers.createCardElement(cfg)
        : document.createElement("hui-entities-card");
      if (!helpers) card.setConfig(cfg);
      card.hass = this._hass;

      // Replace previous content
      this.innerHTML = "";
      this.appendChild(card);
      this._inner = card;
      this._builtFor = deviceId;
    } catch (err) {
      console.error("SenziioCard build error:", err);
      this._placeholder("Error building card (check console).");
    }
  }

  _placeholder(text) {
    this.innerHTML = "";
    const el = document.createElement("ha-card");
    el.innerHTML = `<div style="padding:16px;color:var(--secondary-text-color);">${text}</div>`;
    this.appendChild(el);
    this._inner = undefined;
  }

  getCardSize() { return 3; }
}
customElements.define("senziio-card", SenziioCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "senziio-card",
  name: "Senziio Data Card",
  preview: true,
  description: "Entities card prefilled with all entities of one device"
});
