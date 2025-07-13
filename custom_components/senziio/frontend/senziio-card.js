// senziio-data.js

// 1) Register your card in the Lovelace picker
window.customCards = window.customCards || [];
window.customCards.push({
  type: "custom:senziio-data",
  name: "Senziio Data Card",
  preview: true,
  description: "Display Senziio sensors in the order you choose"
});

class SenziioDataCard extends HTMLElement {
  // 2) Provide a config editor (reuse the built-in entities card editor)
  static getConfigElement() {
    return document.createElement("hui-entities-card-editor");
  }

  // 3) Provide a stub config so the picker can show a preview
  static getStubConfig() {
    return {
      entities: []
    };
  }

  // 4) Validate & save the user’s YAML config
  setConfig(config) {
    if (!config.entities || !Array.isArray(config.entities)) {
      throw new Error("Senziio Data Card: you must define an `entities` array");
    }
    this._config = config;
  }

  // 5) Render whenever Home Assistant state updates
  set hass(hass) {
    // Grab exactly the entities the user listed, in that order
    const items = this._config.entities
      .map(eid => hass.states[eid])
      .filter(st => !!st);

    // Build a simple HTML list of “friendly_name: state”
    const list = items
      .map(
        st => `<li>
                 <strong>${st.attributes.friendly_name || st.entity_id}</strong>:
                 ${st.state}
               </li>`
      )
      .join("");

    // Render inside an <ha-card>
    this.innerHTML = `
      <ha-card header="${this._config.title || "Senziio Sensors"}">
        <ul style="list-style:none; padding:8px; margin:0;">
          ${list}
        </ul>
      </ha-card>
    `;
  }

  // 6) Tell the UI how much space this card needs
  getCardSize() {
    return this._config.entities.length || 1;
  }
}

// 7) Define your custom element (must include a hyphen)
customElements.define("senziio-data", SenziioDataCard);
