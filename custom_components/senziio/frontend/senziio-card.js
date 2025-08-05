class SenziioCardEditor extends HTMLElement {
  setConfig(cfg) { this._cfg = { device: "", title: "", ...cfg }; this._render(); }
  set hass(h)    { this._hass = h; this._ensureLoaded(); }

  async _ensureLoaded() {
    if (!this._hass || this._loaded) { this._render(); return; }
    this._loaded = true;

    try {
      // load registries
      const [devices, entities] = await Promise.all([
        this._hass.callWS({ type: "config/device_registry/list" }),
        this._hass.callWS({ type: "config/entity_registry/list" }),
      ]);

      const isActiveReg = (e) => !e.disabled_by && !e.hidden_by;
      // Domains that define a real device for the dropdown
      const allowedDomains = new Set(["sensor", "binary_sensor"]);

      // device_id: has at least one active sensor/binary_sensor
      const realDevIds = new Set(
        entities
          .filter(
            (e) =>
              e.device_id &&
              isActiveReg(e) &&
              allowedDomains.has(e.entity_id.split(".")[0])
          )
          .map((e) => e.device_id)
      );

      // only show real devices
      const filtered = devices.filter((d) => {
        const manuOk = (d.manufacturer || "")
          .toLowerCase()
          .includes("senziio");
        const notService = d.entry_type !== "service";
        const hasReal = realDevIds.has(d.id);
        const tag = `${d.model || ""} ${d.name || ""}`.toLowerCase();
        const notAdmin = !/(admin|integration)/i.test(tag);
        return manuOk && notService && hasReal && notAdmin;
      });

      this._devices = filtered.length
        ? filtered
        : devices.filter((d) => realDevIds.has(d.id));
    } catch (e) {
      console.error("Senziio editor: registry error", e);
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

    if ((this._devices?.length || 0) === 0) {
      const note = document.createElement("div");
      note.style.cssText = "margin-top:8px;color:var(--secondary-text-color);";
      note.textContent = "No Senziio devices with active sensors found.";
      wrap.appendChild(note);
    }

    this.appendChild(wrap);
  }

  _picked(deviceId) {
    const cfg = { ...this._cfg, device: deviceId };
    this._cfg = cfg;
    this.dispatchEvent(
      new CustomEvent("config-changed", { detail: { config: cfg } })
    );
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
    if (!this._hass || (!this._cfg?.device && !this._cfg?.sensor)) {
      return this._placeholder("Select a Senziio device");
    }

    try {
      const entReg = await this._hass.callWS({ type: "config/entity_registry/list" });

      let deviceId = this._cfg.device;
      if (!deviceId && this._cfg.sensor) {
        const anchor = entReg.find((e) => e.entity_id === this._cfg.sensor);
        deviceId = anchor?.device_id;
      }
      if (!deviceId) return this._placeholder("Cannot resolve device.");

      if (this._builtFor === deviceId && this._inner) return;

      // active registry entries for this device
      const isActiveReg = (e) => !e.disabled_by && !e.hidden_by;

      let entityIds = entReg
        .filter((e) => e.device_id === deviceId && isActiveReg(e))
        .map((e) => e.entity_id);

      // keep only those currently in the state machine
      entityIds = entityIds.filter((id) => id in this._hass.states);

      // keep only data entities
      const allowedDomainsShow = new Set(["sensor", "binary_sensor"]);
      entityIds = entityIds.filter((id) => allowedDomainsShow.has(id.split(".")[0]));

      entityIds.sort((a, b) => {
        const [ra, na] = rank(a, this._hass);
        const [rb, nb] = rank(b, this._hass);
        return ra !== rb ? ra - rb : na.localeCompare(nb, undefined, {sensitivity: "base"});
      });

      if (entityIds.length === 0) {
        return this._placeholder("This device has no active entities.");
      }

      const devices = await this._hass.callWS({ type: "config/device_registry/list" });
      const device = devices.find((d) => d.id === deviceId);
      const title =
        this._cfg.title ||
        device?.name_by_user ||
        device?.name ||
        (this._hass.states[entityIds[0]]?.attributes?.friendly_name ??
          "Senziio device");

      const cfg = { type: "entities", title, entities: entityIds };

      const helpers = await (window.loadCardHelpers?.());
      const card = helpers
        ? helpers.createCardElement(cfg)
        : document.createElement("hui-entities-card");
      if (!helpers) card.setConfig(cfg);
      card.hass = this._hass;

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

const ENTITIES_ORDER = [
  "presence",
  "motion",
  "radar",
  "camera",
  "thermal",  // keep for compatibility
  "pir",
  "beacon",
  "temperature",
  "humidity",
  "co2",
  "illuminance",
  "pressure",
];

const rank = (id, hass) => {
  // rank for custom entities order
  const s = id.toLowerCase();
  let i = ENTITIES_ORDER.findIndex(k => s.includes(k));
  if (i === -1) i = ENTITIES_ORDER.length;
  const name = hass.states[id]?.attributes?.friendly_name ?? id;
  return [i, name];
};

window.customCards = window.customCards || [];
window.customCards.push({
  type: "senziio-card",
  name: "Senziio Card",
  preview: true,
  description: "Entities card prefilled with all entities of one device"
});
